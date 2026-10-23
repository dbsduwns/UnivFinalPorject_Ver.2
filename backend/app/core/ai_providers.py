from __future__ import annotations

import os
from typing import Any


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def cloudflare_base_url() -> str:
    account_id = require_env("CLOUDFLARE_ACCOUNT_ID")
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


def build_embeddings(provider: str | None = None) -> Any:
    selected_provider = (provider or os.getenv("EMBEDDING_PROVIDER", "cloudflare")).lower()

    if selected_provider == "cloudflare":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=os.getenv("CLOUDFLARE_EMBEDDING_MODEL", "@cf/baai/bge-m3"),
            api_key=require_env("CLOUDFLARE_API_TOKEN"),
            base_url=cloudflare_base_url(),
            check_embedding_ctx_length=False,
            max_retries=5,
        )

    if selected_provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            google_api_key=require_env("GOOGLE_API_KEY"),
        )

    if selected_provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name="jhgan/ko-sroberta-multitask",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    raise ValueError(f"지원하지 않는 EMBEDDING_PROVIDER: {selected_provider}")


def build_chat_model(provider: str | None = None) -> Any:
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "cloudflare")).lower()

    if selected_provider == "cloudflare":
        from langchain_openai import ChatOpenAI

        class CloudflareChatOpenAI(ChatOpenAI):
            """Tolerate malformed non-text content in Workers AI SSE chunks."""

            def _convert_chunk_to_generation_chunk(
                self,
                chunk,
                default_chunk_class,
                base_generation_info,
            ):
                choices = chunk.get("choices") or (
                    (chunk.get("chunk") or {}).get("choices")
                )
                if choices:
                    delta = choices[0].get("delta")
                    if isinstance(delta, dict) and "content" in delta:
                        content = delta.get("content")
                        if isinstance(content, list):
                            normalized_content = []
                            for item in content:
                                if isinstance(item, (str, dict)):
                                    normalized_content.append(item)
                                elif isinstance(item, (int, float)) and not isinstance(
                                    item, bool
                                ):
                                    normalized_content.append(str(item))
                            delta["content"] = normalized_content
                        elif isinstance(content, (int, float)) and not isinstance(
                            content, bool
                        ):
                            # Workers AI occasionally emits a generated number
                            # as a JSON number instead of an OpenAI-style string.
                            delta["content"] = str(content)
                        elif content is not None and not isinstance(content, str):
                            delta["content"] = ""

                return super()._convert_chunk_to_generation_chunk(
                    chunk,
                    default_chunk_class,
                    base_generation_info,
                )

        return CloudflareChatOpenAI(
            model=os.getenv(
                "CLOUDFLARE_CHAT_MODEL",
                "@cf/qwen/qwen3-30b-a3b-fp8",
            ),
            api_key=require_env("CLOUDFLARE_API_TOKEN"),
            base_url=cloudflare_base_url(),
            temperature=0.7,
            max_retries=3,
        )

    if selected_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
            google_api_key=require_env("GOOGLE_API_KEY"),
            temperature=0.7,
            max_retries=2,
        )

    raise ValueError(f"지원하지 않는 LLM_PROVIDER: {selected_provider}")
