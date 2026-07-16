from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.enums import AIProvider, ScanStatus, UserRole
from app.models.ai_configuration import AIConfiguration
from app.models.incident import Incident
from app.models.scan import Scan
from app.schemas.ai import (
    AIAnalysisRead,
    AIConfigurationRead,
    AIConfigurationUpdate,
    AIConnectionTestRead,
    AIStatusRead,
)
from app.security.dependencies import CurrentUser, get_current_user, require_roles
from app.services.ai.base import AIProviderError
from app.services.ai.encryption import (
    AIEncryptionError,
    decrypt_api_key,
    encrypt_api_key,
)
from app.services.ai.service import (
    generate_incident_ai_analysis,
    generate_scan_ai_analysis,
    get_ai_configuration,
    latest_analysis_for_incident,
    latest_analysis_for_scan,
    test_provider_connection,
)
from app.services.audit_log import create_audit_log
from app.services.rate_limiter import ai_analysis_rate_limiter, ai_test_rate_limiter

router = APIRouter(tags=["ai"])

AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
AIAdministrator = Annotated[CurrentUser, Depends(require_roles(UserRole.administrator))]
AIRequester = Annotated[
    CurrentUser,
    Depends(require_roles(UserRole.administrator, UserRole.security_analyst)),
]


@router.get("/ai/status", response_model=AIStatusRead)
async def get_ai_status(current_user: AuthenticatedUser) -> AIStatusRead:
    with SessionLocal() as db:
        config = get_ai_configuration(db, current_user.organization_id)
        return ai_status_read(config)


@router.get("/ai/config", response_model=AIConfigurationRead)
async def get_ai_config(current_user: AIAdministrator) -> AIConfigurationRead:
    with SessionLocal() as db:
        config = get_ai_configuration(db, current_user.organization_id)
        return ai_config_read(config)


@router.put("/ai/config", response_model=AIConfigurationRead)
async def save_ai_config(
    payload: AIConfigurationUpdate,
    current_user: AIAdministrator,
) -> AIConfigurationRead:
    validate_config_payload(payload)
    with SessionLocal() as db:
        config = get_ai_configuration(db, current_user.organization_id)
        created = config is None
        if config is None:
            config = AIConfiguration(
                organization_id=current_user.organization_id,
                created_by=current_user.id,
                updated_by=current_user.id,
                provider=None,
                model=None,
                base_url=None,
                is_enabled=False,
                timeout_seconds=get_settings().ai_timeout_seconds,
            )
            db.add(config)
            db.flush()
        previous_provider = config.provider
        previous_model = config.model
        previous_enabled = config.is_enabled
        had_key = bool(config.encrypted_api_key)

        config.provider = payload.provider
        config.model = payload.model
        config.base_url = normalized_base_url(payload)
        config.is_enabled = payload.is_enabled
        config.timeout_seconds = payload.timeout_seconds
        config.updated_by = current_user.id
        if payload.api_key:
            try:
                config.encrypted_api_key = encrypt_api_key(
                    payload.api_key, get_settings()
                )
            except AIEncryptionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unable to store AI provider API key securely",
                ) from exc
            config.api_key_last_four = payload.api_key[-4:]

        db.flush()
        audit_configuration_changes(
            db,
            current_user=current_user,
            config=config,
            created=created,
            previous_provider=previous_provider,
            previous_model=previous_model,
            previous_enabled=previous_enabled,
            had_key=had_key,
            has_new_key=bool(payload.api_key),
        )
        db.commit()
        db.refresh(config)
        return ai_config_read(config)


@router.delete("/ai/config/key", response_model=AIConfigurationRead)
async def remove_ai_key(current_user: AIAdministrator) -> AIConfigurationRead:
    with SessionLocal() as db:
        config = get_ai_configuration(db, current_user.organization_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI configuration not found",
            )
        config.encrypted_api_key = None
        config.api_key_last_four = None
        config.updated_by = current_user.id
        db.flush()
        create_audit_log(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="ai.config.api_key_removed",
            resource_type="ai_configuration",
            resource_id=config.id,
            metadata=safe_config_metadata(config),
        )
        db.commit()
        db.refresh(config)
        return ai_config_read(config)


@router.post("/ai/config/test", response_model=AIConnectionTestRead)
async def test_ai_config(
    payload: AIConfigurationUpdate,
    current_user: AIAdministrator,
) -> AIConnectionTestRead:
    validate_config_payload(payload)
    settings = get_settings()
    ai_test_rate_limiter.check_and_record(
        key=f"ai-test:{current_user.id}",
        limit=settings.ai_test_rate_limit_user_attempts,
        window_seconds=settings.ai_rate_limit_window_seconds,
        max_keys=settings.ai_rate_limit_max_keys,
        message="Too many AI provider tests. Try again later.",
    )
    with SessionLocal() as db:
        config = get_ai_configuration(db, current_user.organization_id)
        provider = payload.provider or (config.provider if config else None)
        model = payload.model or (config.model if config else None)
        base_url = normalized_base_url(payload) or (config.base_url if config else None)
        timeout_seconds = payload.timeout_seconds or (
            config.timeout_seconds if config else settings.ai_timeout_seconds
        )
        api_key = payload.api_key or decrypt_existing_key(config)
        if provider is None or not model or not api_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider, model and API key are required to test AI",
            )
        create_audit_log(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="ai.config.test_requested",
            resource_type="ai_configuration",
            resource_id=config.id if config else "unsaved",
            metadata={"provider": provider.value, "model": model},
        )
        try:
            await test_provider_connection(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
        except AIProviderError as exc:
            create_audit_log(
                db,
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                action="ai.config.test_failed",
                resource_type="ai_configuration",
                resource_id=config.id if config else "unsaved",
                metadata={
                    "provider": provider.value,
                    "model": model,
                    "safe_error_category": exc.safe_message,
                },
            )
            db.commit()
            return AIConnectionTestRead(
                success=False,
                message=exc.safe_message,
                provider=provider,
                model=model,
            )
        create_audit_log(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="ai.config.test_succeeded",
            resource_type="ai_configuration",
            resource_id=config.id if config else "unsaved",
            metadata={"provider": provider.value, "model": model},
        )
        db.commit()
        return AIConnectionTestRead(
            success=True,
            message="Provider connection succeeded",
            provider=provider,
            model=model,
        )


@router.get("/scans/{scan_id}/ai-analysis", response_model=AIAnalysisRead | None)
async def get_scan_ai_analysis(
    scan_id: str,
    current_user: AuthenticatedUser,
) -> AIAnalysisRead | None:
    with SessionLocal() as db:
        scan = get_scan_for_user(db, scan_id, current_user)
        analysis = latest_analysis_for_scan(
            db,
            scan_id=scan.id,
            organization_id=current_user.organization_id,
        )
        return AIAnalysisRead.model_validate(analysis) if analysis else None


@router.post("/scans/{scan_id}/ai-analysis", response_model=AIAnalysisRead)
async def create_scan_ai_analysis(
    scan_id: str,
    current_user: AIRequester,
) -> AIAnalysisRead:
    settings = get_settings()
    ai_analysis_rate_limiter.check_and_record(
        key=f"ai-analysis:{current_user.id}",
        limit=settings.ai_analysis_rate_limit_user_attempts,
        window_seconds=settings.ai_rate_limit_window_seconds,
        max_keys=settings.ai_rate_limit_max_keys,
        message="Too many AI analyses requested. Try again later.",
    )
    with SessionLocal() as db:
        scan = get_scan_for_user(db, scan_id, current_user)
        incident = db.scalar(
            select(Incident).where(
                Incident.organization_id == current_user.organization_id,
                Incident.scan_id == scan.id,
            )
        )
        analysis = await generate_scan_ai_analysis(
            db,
            scan=scan,
            incident=incident,
            current_user=current_user,
        )
        return AIAnalysisRead.model_validate(analysis)


@router.get(
    "/incidents/{incident_id}/ai-analysis", response_model=AIAnalysisRead | None
)
async def get_incident_ai_analysis(
    incident_id: str,
    current_user: AuthenticatedUser,
) -> AIAnalysisRead | None:
    with SessionLocal() as db:
        incident = get_incident_for_user(db, incident_id, current_user)
        analysis = latest_analysis_for_incident(
            db,
            incident_id=incident.id,
            organization_id=current_user.organization_id,
        )
        return AIAnalysisRead.model_validate(analysis) if analysis else None


@router.post("/incidents/{incident_id}/ai-analysis", response_model=AIAnalysisRead)
async def create_incident_ai_analysis(
    incident_id: str,
    current_user: AIRequester,
) -> AIAnalysisRead:
    settings = get_settings()
    ai_analysis_rate_limiter.check_and_record(
        key=f"ai-analysis:{current_user.id}",
        limit=settings.ai_analysis_rate_limit_user_attempts,
        window_seconds=settings.ai_rate_limit_window_seconds,
        max_keys=settings.ai_rate_limit_max_keys,
        message="Too many AI analyses requested. Try again later.",
    )
    with SessionLocal() as db:
        incident = get_incident_for_user(db, incident_id, current_user)
        analysis = await generate_incident_ai_analysis(
            db,
            incident=incident,
            current_user=current_user,
        )
        return AIAnalysisRead.model_validate(analysis)


def ai_config_read(config: AIConfiguration | None) -> AIConfigurationRead:
    if config is None:
        return AIConfigurationRead(
            provider=None,
            model=None,
            base_url=None,
            is_enabled=False,
            timeout_seconds=get_settings().ai_timeout_seconds,
            has_api_key=False,
            api_key_last_four=None,
        )
    return AIConfigurationRead(
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        is_enabled=config.is_enabled,
        timeout_seconds=config.timeout_seconds,
        has_api_key=bool(config.encrypted_api_key),
        api_key_last_four=config.api_key_last_four,
    )


def ai_status_read(config: AIConfiguration | None) -> AIStatusRead:
    return AIStatusRead(
        is_configured=bool(config and config.provider and config.model),
        provider=config.provider if config else None,
        model=config.model if config else None,
        is_enabled=bool(config and config.is_enabled),
        has_api_key=bool(config and config.encrypted_api_key),
    )


def validate_config_payload(payload: AIConfigurationUpdate) -> None:
    if payload.is_enabled and (payload.provider is None or not payload.model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provider and model are required when AI is enabled",
        )
    if payload.provider == AIProvider.openai_compatible and not payload.base_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OpenAI-compatible provider requires a base URL",
        )


def normalized_base_url(payload: AIConfigurationUpdate) -> str | None:
    if payload.provider == AIProvider.openai_compatible:
        return payload.base_url.rstrip("/") if payload.base_url else None
    return None


def decrypt_existing_key(config: AIConfiguration | None) -> str | None:
    if config is None or not config.encrypted_api_key:
        return None
    try:
        return decrypt_api_key(config.encrypted_api_key, get_settings())
    except AIEncryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored AI provider API key cannot be decrypted",
        ) from exc


def audit_configuration_changes(
    db,
    *,
    current_user: CurrentUser,
    config: AIConfiguration,
    created: bool,
    previous_provider: AIProvider | None,
    previous_model: str | None,
    previous_enabled: bool,
    had_key: bool,
    has_new_key: bool,
) -> None:
    if created:
        create_config_audit(db, current_user, config, "ai.config.created")
    if previous_provider != config.provider:
        create_config_audit(db, current_user, config, "ai.config.provider_changed")
    if previous_model != config.model:
        create_config_audit(db, current_user, config, "ai.config.model_changed")
    if has_new_key:
        action = "ai.config.api_key_replaced" if had_key else "ai.config.api_key_added"
        create_config_audit(db, current_user, config, action)
    if previous_enabled != config.is_enabled:
        action = "ai.config.enabled" if config.is_enabled else "ai.config.disabled"
        create_config_audit(db, current_user, config, action)


def create_config_audit(
    db,
    current_user: CurrentUser,
    config: AIConfiguration,
    action: str,
) -> None:
    create_audit_log(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=action,
        resource_type="ai_configuration",
        resource_id=config.id,
        metadata=safe_config_metadata(config),
    )


def safe_config_metadata(config: AIConfiguration) -> dict[str, object]:
    return {
        "provider": config.provider.value if config.provider else None,
        "model": config.model,
        "is_enabled": config.is_enabled,
        "has_api_key": bool(config.encrypted_api_key),
    }


def get_scan_for_user(db, scan_id: str, current_user: CurrentUser) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None or scan.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
        )
    if scan.status != ScanStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI analysis requires a completed scan",
        )
    return scan


def get_incident_for_user(db, incident_id: str, current_user: CurrentUser) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None or incident.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )
    return incident
