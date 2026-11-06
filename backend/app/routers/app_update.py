from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin_user
from app.database import get_db
from app.models.app_release import AppRelease
from app.models.user import User
from app.schemas.app_update import (
    AppReleaseCreate,
    AppReleaseResponse,
    AppReleaseUpdate,
    AppUpdateCheckResponse,
)


router = APIRouter(prefix="/api/app-updates", tags=["app-updates"])


def _latest_active_android_release(db: Session) -> AppRelease | None:
    return (
        db.query(AppRelease)
        .filter(
            AppRelease.platform == "android",
            AppRelease.is_active.is_(True),
        )
        .order_by(AppRelease.version_code.desc(), AppRelease.id.desc())
        .first()
    )


def _deactivate_platform_releases(
    db: Session,
    platform: str,
    except_release_id: int | None = None,
) -> None:
    query = db.query(AppRelease).filter(
        AppRelease.platform == platform,
        AppRelease.is_active.is_(True),
    )
    if except_release_id is not None:
        query = query.filter(AppRelease.id != except_release_id)
    query.update({AppRelease.is_active: False}, synchronize_session=False)


@router.get("/android", response_model=AppUpdateCheckResponse)
def check_android_update(
    current_version_code: int = Query(ge=0),
    db: Session = Depends(get_db),
):
    release = _latest_active_android_release(db)
    update_available = release is not None and release.version_code > current_version_code
    mandatory = bool(
        update_available
        and release is not None
        and (release.mandatory or current_version_code < release.minimum_version_code)
    )
    return AppUpdateCheckResponse(
        current_version_code=current_version_code,
        update_available=update_available,
        mandatory=mandatory,
        latest_release=release,
    )


@router.get("/releases", response_model=list[AppReleaseResponse])
def list_app_releases(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return (
        db.query(AppRelease)
        .order_by(AppRelease.platform.asc(), AppRelease.version_code.desc())
        .all()
    )


@router.post("/releases", response_model=AppReleaseResponse, status_code=201)
def create_app_release(
    data: AppReleaseCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    if data.is_active:
        _deactivate_platform_releases(db, data.platform)
    release = AppRelease(
        **data.model_dump(exclude={"apk_url", "sha256"}),
        apk_url=str(data.apk_url),
        sha256=data.sha256.lower() if data.sha256 else None,
        published_at=datetime.now(timezone.utc) if data.is_active else None,
    )
    db.add(release)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="같은 플랫폼과 version_code의 릴리스가 이미 있습니다.") from exc
    db.refresh(release)
    return release


@router.patch("/releases/{release_id}", response_model=AppReleaseResponse)
def update_app_release(
    release_id: int,
    data: AppReleaseUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    release = db.query(AppRelease).filter(AppRelease.id == release_id).first()
    if release is None:
        raise HTTPException(status_code=404, detail="앱 릴리스를 찾을 수 없습니다.")

    values = data.model_dump(exclude_unset=True, exclude={"apk_url"})
    if data.apk_url is not None:
        values["apk_url"] = str(data.apk_url)
    if data.sha256 is not None:
        values["sha256"] = data.sha256.lower()

    minimum_version_code = values.get("minimum_version_code", release.minimum_version_code)
    if minimum_version_code > release.version_code:
        raise HTTPException(
            status_code=422,
            detail="minimum_version_code는 version_code보다 클 수 없습니다.",
        )

    activating = values.get("is_active") is True
    if activating:
        _deactivate_platform_releases(db, release.platform, except_release_id=release.id)
        values["published_at"] = datetime.now(timezone.utc)
    elif values.get("is_active") is False:
        values["published_at"] = None

    for field, value in values.items():
        setattr(release, field, value)
    db.commit()
    db.refresh(release)
    return release
