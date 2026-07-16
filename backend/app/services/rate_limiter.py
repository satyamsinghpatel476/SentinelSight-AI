from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.utils.time import utc_now


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        settings = get_settings()
        if (
            key not in self._attempts
            and len(self._attempts) >= settings.login_rate_limit_max_keys
        ):
            self._prune_oldest_key()

        now = utc_now().timestamp()
        window_start = now - settings.login_rate_limit_window_seconds
        self._attempts[key] = [
            attempt for attempt in self._attempts[key] if attempt >= window_start
        ]
        if len(self._attempts[key]) >= settings.login_rate_limit_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )

    def record_failure(self, key: str) -> None:
        self._attempts[key].append(utc_now().timestamp())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()

    def _prune_oldest_key(self) -> None:
        if not self._attempts:
            return
        oldest_key = min(
            self._attempts,
            key=lambda item: min(self._attempts[item]) if self._attempts[item] else 0,
        )
        self._attempts.pop(oldest_key, None)


login_rate_limiter = LoginRateLimiter()


class ScanRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check_and_record(self, user_id: str, organization_id: str) -> None:
        settings = get_settings()
        user_key = f"user:{user_id}"
        org_key = f"org:{organization_id}"
        self._check_key(
            user_key,
            settings.scan_rate_limit_user_attempts,
            settings.scan_rate_limit_window_seconds,
            settings.scan_rate_limit_max_keys,
            "Too many scans started by this user. Try again later.",
        )
        self._check_key(
            org_key,
            settings.scan_rate_limit_org_attempts,
            settings.scan_rate_limit_window_seconds,
            settings.scan_rate_limit_max_keys,
            "Too many scans started by this organization. Try again later.",
        )
        now = utc_now().timestamp()
        self._attempts[user_key].append(now)
        self._attempts[org_key].append(now)

    def clear(self) -> None:
        self._attempts.clear()

    def _check_key(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        max_keys: int,
        message: str,
    ) -> None:
        if key not in self._attempts and len(self._attempts) >= max_keys:
            self._prune_oldest_key()

        now = utc_now().timestamp()
        window_start = now - window_seconds
        self._attempts[key] = [
            attempt for attempt in self._attempts[key] if attempt >= window_start
        ]
        if len(self._attempts[key]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
            )

    def _prune_oldest_key(self) -> None:
        if not self._attempts:
            return
        oldest_key = min(
            self._attempts,
            key=lambda item: min(self._attempts[item]) if self._attempts[item] else 0,
        )
        self._attempts.pop(oldest_key, None)


scan_rate_limiter = ScanRateLimiter()


class ActionRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def check_and_record(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        max_keys: int,
        message: str,
    ) -> None:
        if key not in self._attempts and len(self._attempts) >= max_keys:
            self._prune_oldest_key()

        now = utc_now().timestamp()
        window_start = now - window_seconds
        self._attempts[key] = [
            attempt for attempt in self._attempts[key] if attempt >= window_start
        ]
        if len(self._attempts[key]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message,
            )
        self._attempts[key].append(now)

    def clear(self) -> None:
        self._attempts.clear()

    def _prune_oldest_key(self) -> None:
        if not self._attempts:
            return
        oldest_key = min(
            self._attempts,
            key=lambda item: min(self._attempts[item]) if self._attempts[item] else 0,
        )
        self._attempts.pop(oldest_key, None)


ai_test_rate_limiter = ActionRateLimiter()
ai_analysis_rate_limiter = ActionRateLimiter()
