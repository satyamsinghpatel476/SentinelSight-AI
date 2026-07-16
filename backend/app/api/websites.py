from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import UserRole, WebsiteRiskCategory
from app.models.website_asset import WebsiteAsset
from app.schemas.websites import (
    WebsiteAssetCreate,
    WebsiteAssetRead,
    WebsiteAssetUpdate,
)
from app.security.dependencies import CurrentUser, get_current_user, require_roles
from app.security.url_normalization import normalize_public_url

router = APIRouter(prefix="/websites", tags=["websites"])

AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_roles(UserRole.administrator))]


def require_authorization_confirmation(confirmed: bool | None) -> None:
    if confirmed is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must confirm ownership or authorization to monitor this website",
        )


def get_asset_in_current_organization(
    db: Session,
    website_id: str,
    current_user: CurrentUser,
) -> WebsiteAsset:
    asset = db.get(WebsiteAsset, website_id)
    if asset is None or asset.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website asset not found",
        )
    return asset


@router.get("", response_model=list[WebsiteAssetRead])
async def list_websites(
    current_user: AuthenticatedUser,
    risk_category: WebsiteRiskCategory | None = None,
    monitoring_enabled: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[WebsiteAssetRead]:
    with SessionLocal() as db:
        filters = [WebsiteAsset.organization_id == current_user.organization_id]
        if risk_category is not None:
            filters.append(WebsiteAsset.risk_category == risk_category)
        if monitoring_enabled is not None:
            filters.append(WebsiteAsset.monitoring_enabled == monitoring_enabled)

        assets = db.scalars(
            select(WebsiteAsset)
            .where(*filters)
            .order_by(WebsiteAsset.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [WebsiteAssetRead.model_validate(asset) for asset in assets]


@router.post("", response_model=WebsiteAssetRead, status_code=status.HTTP_201_CREATED)
async def create_website(
    payload: WebsiteAssetCreate, current_user: AdminUser
) -> WebsiteAssetRead:
    require_authorization_confirmation(payload.authorization_confirmed)
    normalized_url = normalize_public_url(payload.url)

    with SessionLocal() as db:
        asset = WebsiteAsset(
            organization_id=current_user.organization_id,
            name=payload.name.strip(),
            url=payload.url.strip(),
            normalized_url=normalized_url,
            authorization_confirmed=True,
            monitoring_enabled=payload.monitoring_enabled,
            risk_category=payload.risk_category,
            contact_email=str(payload.contact_email).lower(),
            created_by=current_user.id,
        )
        db.add(asset)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This website URL is already registered for your organization",
            ) from exc
        db.refresh(asset)
        return WebsiteAssetRead.model_validate(asset)


@router.get("/{website_id}", response_model=WebsiteAssetRead)
async def get_website(
    website_id: str, current_user: AuthenticatedUser
) -> WebsiteAssetRead:
    with SessionLocal() as db:
        asset = get_asset_in_current_organization(db, website_id, current_user)
        return WebsiteAssetRead.model_validate(asset)


@router.patch("/{website_id}", response_model=WebsiteAssetRead)
async def update_website(
    website_id: str,
    payload: WebsiteAssetUpdate,
    current_user: AdminUser,
) -> WebsiteAssetRead:
    with SessionLocal() as db:
        asset = get_asset_in_current_organization(db, website_id, current_user)

        if payload.name is not None:
            asset.name = payload.name.strip()
        if payload.url is not None:
            require_authorization_confirmation(payload.authorization_confirmed)
            asset.url = payload.url.strip()
            asset.normalized_url = normalize_public_url(payload.url)
            asset.authorization_confirmed = True
        elif payload.authorization_confirmed is not None:
            require_authorization_confirmation(payload.authorization_confirmed)
            asset.authorization_confirmed = True
        if payload.contact_email is not None:
            asset.contact_email = str(payload.contact_email).lower()
        if payload.risk_category is not None:
            asset.risk_category = payload.risk_category
        if payload.monitoring_enabled is not None:
            asset.monitoring_enabled = payload.monitoring_enabled

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This website URL is already registered for your organization",
            ) from exc
        db.refresh(asset)
        return WebsiteAssetRead.model_validate(asset)


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_website(website_id: str, current_user: AdminUser) -> Response:
    with SessionLocal() as db:
        asset = get_asset_in_current_organization(db, website_id, current_user)
        asset.monitoring_enabled = False
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
