#!/usr/bin/env python3
from posthog import Posthog
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    from .config import get_settings
    settings = get_settings()
    api_key = settings.posthog_api_key
    host = settings.posthog_host
    enabled = settings.posthog_enabled and bool(api_key) and api_key != "disabled"
except Exception:
    api_key = ""
    host = "https://us.posthog.com"
    enabled = False

posthog = Posthog(
    project_api_key=api_key or "disabled",
    host=host,
    disabled=not enabled,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Analytics:
    @staticmethod
    def track_auth(user_id: str, event: str, properties: Optional[Dict] = None):
        if posthog.disabled:
            return
        props = properties or {}
        props.update({"timestamp": _now(), "category": "auth"})
        posthog.capture(event, distinct_id=user_id, properties=props)

    @staticmethod
    def track_ad_event(user_id: str, event: str, ad_id: Optional[int] = None, properties: Optional[Dict] = None):
        if posthog.disabled:
            return
        props = properties or {}
        props.update({"ad_id": ad_id, "timestamp": _now(), "category": "ad"})
        posthog.capture(event, distinct_id=user_id, properties=props)

    @staticmethod
    def track_api_request(user_id: Optional[str], method: str, path: str, status: int, duration_ms: float):
        if posthog.disabled:
            return
        props = {
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": _now(),
            "category": "api",
        }
        posthog.capture(f"api_request_{method}", distinct_id=user_id or "anonymous", properties=props)

    @staticmethod
    def track_user_action(user_id: str, action: str, properties: Optional[Dict] = None):
        if posthog.disabled:
            return
        props = properties or {}
        props.update({"timestamp": _now(), "category": "user_action"})
        posthog.capture(action, distinct_id=user_id, properties=props)

    @staticmethod
    def track_error(user_id: Optional[str], error_type: str, error_message: str, properties: Optional[Dict] = None):
        if posthog.disabled:
            return
        props = properties or {}
        props.update({
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": _now(),
            "category": "error",
        })
        posthog.capture("error", distinct_id=user_id or "anonymous", properties=props)

    @staticmethod
    def identify(user_id: str, traits: Dict[str, Any]):
        if posthog.disabled:
            return
        posthog.set(distinct_id=user_id, properties=traits)

    @staticmethod
    def flush():
        if posthog.disabled:
            return
        posthog.flush()
