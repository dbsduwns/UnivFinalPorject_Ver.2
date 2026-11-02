"""Start a configured Cloud Run Job with the API service's own identity."""

from __future__ import annotations

import os
import re

import httpx


METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/token"
)
RESOURCE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")


class JobConfigurationError(RuntimeError):
    pass


class JobLaunchError(RuntimeError):
    pass


def start_notice_crawler_job() -> str:
    project = os.getenv("GCP_PROJECT_ID", "").strip()
    region = os.getenv("GCP_REGION", "asia-northeast3").strip()
    job = os.getenv("NOTICE_CRAWLER_JOB", "").strip()
    if not project or not region or not job:
        raise JobConfigurationError(
            "공지 크롤러 Job 설정이 없습니다. GCP_PROJECT_ID, GCP_REGION, NOTICE_CRAWLER_JOB을 확인하세요."
        )
    if not all(RESOURCE_NAME_PATTERN.fullmatch(value) for value in (project, region, job)):
        raise JobConfigurationError("Cloud Run 프로젝트, 리전 또는 Job 이름이 올바르지 않습니다.")

    url = f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs/{job}:run"
    try:
        with httpx.Client(timeout=15.0) as client:
            token_response = client.get(METADATA_URL, headers={"Metadata-Flavor": "Google"})
            token_response.raise_for_status()
            token = token_response.json().get("access_token")
            if not token:
                raise JobLaunchError("Cloud Run 서비스 계정의 액세스 토큰을 받지 못했습니다.")
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            if response.status_code in (401, 403):
                raise JobLaunchError("API 서비스 계정에 크롤러 Job 실행 권한이 없습니다.")
            if response.status_code == 404:
                raise JobLaunchError("설정된 Cloud Run 크롤러 Job을 찾지 못했습니다.")
            response.raise_for_status()
            operation = response.json().get("name")
            if not operation:
                raise JobLaunchError("Cloud Run에서 작업 실행 정보를 반환하지 않았습니다.")
            return operation
    except httpx.HTTPError as exc:
        raise JobLaunchError("Cloud Run 크롤러 Job 실행 요청에 실패했습니다.") from exc
