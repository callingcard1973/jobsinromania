#!/usr/bin/env python3
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from app.core.analytics import Analytics, posthog
from app.core.security import decode_access_token


def _user_id_from_request(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    payload = decode_access_token(auth[7:])
    if not payload:
        return None
    return payload.get("sub")


class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if posthog.disabled:
            return await call_next(request)

        start_time = time.time()
        try:
            user_id = _user_id_from_request(request)
        except Exception:
            user_id = None

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        Analytics.track_api_request(
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
