from urllib.parse import urljoin, urlsplit

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from app.core.university_http import university_get
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notice import NoticeResponse, NoticeUpdate, NoticeCreate
from app.services import notice as notice_service
from app.models.user import User
from app.core.dependencies import get_current_admin_user

router = APIRouter(prefix="/api/notices", tags=["notices"])

_NOTICE_ASSET_HOST = "web.kangnam.ac.kr"
_NOTICE_ASSET_PATH_PREFIX = "/comm/cmnFile/"
_MAX_NOTICE_IMAGE_BYTES = 15 * 1024 * 1024


def _validate_notice_image_url(url: str) -> str:
	parsed = urlsplit(url)
	try:
		port = parsed.port
	except ValueError as exc:
		raise HTTPException(status_code=400, detail="잘못된 이미지 URL입니다.") from exc

	if (
		parsed.scheme != "https"
		or parsed.hostname != _NOTICE_ASSET_HOST
		or port not in (None, 443)
		or parsed.username is not None
		or parsed.password is not None
		or not parsed.path.startswith(_NOTICE_ASSET_PATH_PREFIX)
	):
		raise HTTPException(status_code=400, detail="허용되지 않은 이미지 URL입니다.")
	return url


def _detect_image_media_type(payload: bytes, content_type: str) -> str | None:
	media_type = content_type.split(";", 1)[0].strip().lower()
	if media_type.startswith("image/"):
		return media_type
	if payload.startswith(b"\xff\xd8\xff"):
		return "image/jpeg"
	if payload.startswith(b"\x89PNG\r\n\x1a\n"):
		return "image/png"
	if payload.startswith((b"GIF87a", b"GIF89a")):
		return "image/gif"
	if payload.startswith(b"BM"):
		return "image/bmp"
	if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
		return "image/webp"
	return None


@router.get("/image-proxy", response_class=Response)
def proxy_notice_image(
	url: str = Query(..., min_length=1, max_length=2048),
):
	"""Serve an allowlisted university notice image through the trusted API host."""
	return _proxy_university_file(url, "image")


@router.get("/pdf-proxy", response_class=Response)
def proxy_university_pdf(url: str = Query(..., min_length=1, max_length=2048)):
	return _proxy_university_file(url, "pdf")


def _proxy_university_file(url: str, kind: str):
	current_url = _validate_notice_image_url(url)
	response = None

	try:
		for _ in range(4):
			response = university_get(
				current_url,
				headers={"User-Agent": "KNU-Campus/1.0", "Referer": "https://web.kangnam.ac.kr/"},
				timeout=(5, 30),
				allow_redirects=False,
				stream=True,
			)

			if response.is_redirect or response.is_permanent_redirect:
				location = response.headers.get("location")
				response.close()
				if not location:
					raise HTTPException(status_code=502, detail="이미지 이동 주소가 없습니다.")
				current_url = _validate_notice_image_url(urljoin(current_url, location))
				continue
			break
		else:
			raise HTTPException(status_code=502, detail="이미지 이동 횟수가 너무 많습니다.")

		if response is None or not response.ok:
			status = response.status_code if response is not None else "unknown"
			raise HTTPException(status_code=502, detail=f"공지 이미지를 가져오지 못했습니다: HTTP {status}")

		content_length = response.headers.get("content-length")
		if content_length and int(content_length) > _MAX_NOTICE_IMAGE_BYTES:
			raise HTTPException(status_code=413, detail="공지 이미지가 너무 큽니다.")

		payload = bytearray()
		for chunk in response.iter_content(65536):
			payload.extend(chunk)
			if len(payload) > _MAX_NOTICE_IMAGE_BYTES:
				raise HTTPException(status_code=413, detail="파일이 너무 큽니다.")
		payload = bytes(payload)
		if len(payload) > _MAX_NOTICE_IMAGE_BYTES:
			raise HTTPException(status_code=413, detail="공지 이미지가 너무 큽니다.")

		media_type = _detect_image_media_type(
			payload,
			response.headers.get("content-type", ""),
		)
		if kind == "pdf":
			media_type = "application/pdf" if payload.startswith(b"%PDF-") else None
		if media_type is None:
			raise HTTPException(status_code=415, detail="요청한 파일 형식이 올바르지 않습니다.")

		return Response(
			content=payload,
			media_type=media_type,
			headers={
				"Cache-Control": "public, max-age=86400",
				"X-Content-Type-Options": "nosniff",
			},
		)
	except HTTPException:
		raise
	except (requests.RequestException, ValueError) as exc:
		raise HTTPException(status_code=502, detail="학교 파일 요청에 실패했습니다.") from exc
	finally:
		if response is not None:
			response.close()


@router.post("/", response_model=NoticeResponse, status_code=201)
def create_notice(
    data: NoticeCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return notice_service.create_notice(db, data)

@router.get("/", response_model=list[NoticeResponse])
def get_notices(category: str = None, keyword: str = None, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notices(db, category, keyword)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.get("/{notice_id}", response_model=NoticeResponse)
def get_notice(notice_id: int, db: Session = Depends(get_db)):
	try:
		notice = notice_service.get_notice(db, notice_id)
		if not notice:
			raise HTTPException(status_code=404, detail="Notice not found")
		return notice
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))

@router.post("/crawl")
def crawl_notices(
		max_items: int | None = None,
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		# Playwright는 크롤링 요청이 실제로 들어올 때만 로드한다.
		from app.crawlers.notice_crawler import crawl_notice_list, save_notices

		notices = crawl_notice_list(max_items=max_items)
		save_notices(notices)
		return {"message": "Notice crawling completed", "count": len(notices)}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@router.put("/{notice_id}", response_model=NoticeResponse)
def update_notice(
		notice_id: int,
		data: NoticeUpdate,
		db: Session = Depends(get_db),
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		notice = notice_service.update_notice(db, notice_id, data)
		return notice
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{notice_id}")
def delete_notice(
		notice_id: int,
		db: Session = Depends(get_db),
		current_admin: User = Depends(get_current_admin_user), # 관리자 검증
	):
	try:
		notice = notice_service.delete_notice(db, notice_id)
		return {"message": "삭제되었습니다"}	
	except ValueError as e:
		raise HTTPException(status_code=404, detail=str(e))
