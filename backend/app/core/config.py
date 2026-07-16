from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SentinelSight AI"
    app_env: str = "development"
    app_secret_key: str = Field(default="change-me", min_length=8)
    database_url: str = "sqlite:///./sentinelsight.db"

    access_token_expire_minutes: int = 60
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    login_rate_limit_max_keys: int = 10_000
    max_request_body_bytes: int = 1_048_576

    ai_enabled: bool = False
    ai_provider: str = ""
    ai_model: str = ""
    ai_api_key: str = ""
    ai_timeout_seconds: int = 20
    ai_test_rate_limit_user_attempts: int = 5
    ai_analysis_rate_limit_user_attempts: int = 10
    ai_rate_limit_window_seconds: int = 3_600
    ai_rate_limit_max_keys: int = 10_000

    scan_connect_timeout_seconds: int = 5
    scan_read_timeout_seconds: int = 10
    scan_total_timeout_seconds: int = 20
    scan_max_response_bytes: int = 5_000_000
    scan_max_redirects: int = 3
    scan_max_concurrent: int = 3
    scan_visible_text_max_chars: int = 20_000
    scan_rate_limit_user_attempts: int = 10
    scan_rate_limit_org_attempts: int = 50
    scan_rate_limit_window_seconds: int = 3_600
    scan_rate_limit_max_keys: int = 10_000
    allow_internal_demo_target: bool = False
    demo_target_internal_url: str = "http://demo-target:9000"

    screenshot_timeout_ms: int = 15_000
    screenshot_width: int = 1365
    screenshot_height: int = 768
    evidence_storage_dir: str = "storage"

    visual_minor_threshold: int = 5
    visual_moderate_threshold: int = 15
    visual_major_threshold: int = 35

    incident_risk_threshold: int = 50

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_runtime_security(self) -> None:
        if not self.is_production:
            return

        weak_secrets = {"change-me", "dev-only-change-me", "test-secret-key"}
        if self.app_secret_key in weak_secrets or len(self.app_secret_key) < 32:
            raise RuntimeError(
                "APP_SECRET_KEY must be set to a strong production secret "
                "with at least 32 characters"
            )
        if not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true in production")
        if self.allow_internal_demo_target:
            raise RuntimeError(
                "ALLOW_INTERNAL_DEMO_TARGET cannot be true in production"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
