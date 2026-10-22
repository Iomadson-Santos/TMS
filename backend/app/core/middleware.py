from __future__ import annotations

import hmac
import re
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.security import decode_access_token, parse_refresh_token, validate_csrf_token


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestTooLargeError(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Bloqueia corpos maiores que o limite, inclusive transferencias em partes."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length:
            try:
                parsed_length = int(content_length)
                if parsed_length < 0:
                    raise ValueError
                if parsed_length > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    status_code=400,
                    content={"detail": "Content-Length invalido"},
                )(scope, receive, send)
                return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLargeError
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestTooLargeError:
            if not response_started:
                await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            status_code=413,
            content={"detail": "Corpo da requisicao excede o limite permitido"},
        )(scope, receive, send)


class BrowserRequestProtectionMiddleware(BaseHTTPMiddleware):
    """Valida origem e aplica CSRF assinado para autenticacao por cookie."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method.upper() not in SAFE_METHODS and request.url.path.startswith(
            settings.api_v1_prefix
        ):
            rejection = self._validate_origin(request)
            if rejection is not None:
                return rejection

            credential_paths = {
                f"{settings.api_v1_prefix}/auth/login",
                f"{settings.api_v1_prefix}/auth/token",
            }
            is_credential_endpoint = request.url.path in credential_paths
            auth_header = request.headers.get("authorization", "")
            cookie_token = request.cookies.get(settings.auth_cookie_name)
            refresh_token = request.cookies.get(settings.refresh_cookie_name)
            uses_bearer = auth_header.lower().startswith("bearer ")

            if (cookie_token or refresh_token) and not uses_bearer and not is_credential_endpoint:
                session_id = self._session_id(cookie_token, refresh_token)
                cookie_csrf = request.cookies.get(settings.csrf_cookie_name, "")
                header_csrf = request.headers.get("x-csrf-token", "")
                valid = bool(
                    session_id
                    and cookie_csrf
                    and header_csrf
                    and hmac.compare_digest(cookie_csrf, header_csrf)
                    and validate_csrf_token(cookie_csrf, session_id)
                )
                if not valid:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Token CSRF ausente ou invalido"},
                    )

        return await call_next(request)

    @staticmethod
    def _session_id(cookie_token: str | None, refresh_token: str | None) -> str | None:
        parsed_refresh = parse_refresh_token(refresh_token)
        if parsed_refresh:
            return parsed_refresh.session_id
        if cookie_token:
            try:
                return str(decode_access_token(cookie_token).get("sid") or "") or None
            except ValueError:
                return None
        return None

    @staticmethod
    def _validate_origin(request: Request) -> JSONResponse | None:
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if fetch_site == "cross-site":
            return JSONResponse(
                status_code=403,
                content={"detail": "Origem da requisicao nao permitida"},
            )

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        if not origin and not referer:
            # Clientes Bearer e scripts nao enviam necessariamente esses cabecalhos.
            return None

        host = request.headers.get("host", "")
        request_origin = f"{request.url.scheme}://{host}".rstrip("/")
        allowed = {request_origin, *settings.cors_origin_list}
        if settings.public_base_url:
            allowed.add(settings.public_base_url.rstrip("/"))

        candidate = origin
        if not candidate and referer:
            parsed = urlparse(referer)
            candidate = (
                f"{parsed.scheme}://{parsed.netloc}"
                if parsed.scheme and parsed.netloc
                else ""
            )

        if not candidate or candidate.rstrip("/") not in allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origem da requisicao nao permitida"},
            )
        return None


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_request_id = Headers(scope=scope).get("x-request-id", "")
        request_id = raw_request_id if REQUEST_ID_PATTERN.fullmatch(raw_request_id) else uuid4().hex
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id
        path = scope.get("path", "")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = (
                    "strict-origin-when-cross-origin"
                    if path in {"/tracking", "/tracking/"}
                    else "no-referrer"
                )
                headers["Permissions-Policy"] = (
                    "camera=(), microphone=(), geolocation=(self), payment=(), usb=()"
                )
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                headers["Cross-Origin-Resource-Policy"] = "same-origin"
                headers["X-Permitted-Cross-Domain-Policies"] = "none"
                headers["X-DNS-Prefetch-Control"] = "off"
                headers["Origin-Agent-Cluster"] = "?1"
                headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
                headers["Content-Security-Policy"] = self._content_security_policy()

                if path.startswith(settings.api_v1_prefix) or not path.startswith("/assets/"):
                    headers["Cache-Control"] = "no-store, max-age=0"
                    headers["Pragma"] = "no-cache"
                elif "cache-control" not in headers:
                    headers["Cache-Control"] = "public, max-age=604800, immutable"

                if settings.hsts_enabled and scope.get("scheme") == "https":
                    value = f"max-age={settings.hsts_max_age_seconds}"
                    if settings.hsts_include_subdomains:
                        value += "; includeSubDomains"
                    headers["Strict-Transport-Security"] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)

    @staticmethod
    def _websocket_sources() -> list[str]:
        sources: list[str] = []
        if settings.public_base_url:
            parsed = urlparse(settings.public_base_url)
            if parsed.hostname:
                ws_scheme = "wss" if parsed.scheme == "https" else "ws"
                port = f":{parsed.port}" if parsed.port else ""
                sources.append(f"{ws_scheme}://{parsed.hostname}{port}")
        if not settings.is_production:
            sources.extend(["ws://127.0.0.1:*", "ws://localhost:*"])
        return sources

    @classmethod
    def _content_security_policy(cls) -> str:
        websocket_sources = " ".join(cls._websocket_sources())
        connect_sources = "'self'" + (f" {websocket_sources}" if websocket_sources else "")
        directives = [
            "default-src 'self'",
            "script-src 'self' https://unpkg.com",
            "script-src-attr 'none'",
            "style-src 'self' https://unpkg.com",
            "style-src-attr 'unsafe-inline'",
            "img-src 'self' data: blob: https://tile.openstreetmap.org",
            f"connect-src {connect_sources}",
            "font-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            "frame-src 'none'",
            "form-action 'self'",
            "manifest-src 'self'",
            "worker-src 'self' blob:",
        ]
        if settings.is_production:
            directives.append("upgrade-insecure-requests")
        return "; ".join(directives)
