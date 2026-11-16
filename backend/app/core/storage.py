import io
import os
import uuid

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


MAX_COMMUNITY_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def upload_community_image(file: UploadFile, user_id: int) -> tuple[str, str]:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="JPG, PNG, WEBP 이미지만 첨부할 수 있습니다.")

    payload = file.file.read(MAX_COMMUNITY_IMAGE_BYTES + 1)
    if len(payload) > MAX_COMMUNITY_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="이미지 파일은 10MB 이하만 첨부할 수 있습니다.")

    try:
        image = Image.open(io.BytesIO(payload))
        image.verify()
        image = Image.open(io.BytesIO(payload))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="유효한 이미지 파일이 아닙니다.") from exc

    if image.format not in {"JPEG", "PNG", "WEBP"}:
        raise HTTPException(status_code=400, detail="JPG, PNG, WEBP 이미지만 첨부할 수 있습니다.")

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "community-images")
    if not supabase_url or not service_key:
        raise HTTPException(status_code=503, detail="이미지 저장소가 설정되지 않았습니다.")

    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image.format]
    path = f"posts/{user_id}/{uuid.uuid4().hex}.{extension}"
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{path}"
    response = httpx.post(
        upload_url,
        content=payload,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": file.content_type or "application/octet-stream",
            "x-upsert": "false",
        },
        timeout=60,
    )
    response.raise_for_status()
    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
    return public_url, path


def delete_community_image(path: str | None) -> None:
    if not path:
        return
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "community-images")
    if not supabase_url or not service_key:
        return
    response = httpx.delete(
        f"{supabase_url}/storage/v1/object/{bucket}/{path}",
        headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        timeout=30,
    )
    response.raise_for_status()
