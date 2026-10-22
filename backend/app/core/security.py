from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Any, Protocol

from fastapi import Response
import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hashed_password: str) -> bool: ...


try:
    from pwdlib import PasswordHash

    _pwdlib_hasher = PasswordHash.recommended()

    class _PwdlibAdapter:
        def hash(self, password: str) -> str:
            return _pwdlib_hasher.hash(password)

        def verify(self, password: str, hashed_password: str) -> bool:
            try:
                return _pwdlib_hasher.verify(password, hashed_password)
            except Exception:
                return False

    password_hasher: PasswordHasher = _PwdlibAdapter()
except ImportError:  # Fallback para ambientes que ja tenham argon2-cffi.
    from argon2 import PasswordHasher as Argon2PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

    _argon2_hasher = Argon2PasswordHasher()

    class _Argon2Adapter:
        def hash(self, password: str) -> str:
            return _argon2_hasher.hash(password)

        def verify(self, password: str, hashed_password: str) -> bool:
            try:
                return _argon2_hasher.verify(hashed_password, password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                return False

    password_hasher = _Argon2Adapter()


# O hash ficticio faz logins de contas inexistentes consumirem custo semelhante ao
# de uma conta real e reduz diferencas de tempo usadas para enumerar usuarios.
_DUMMY_PASSWORD_HASH = password_hasher.hash(
    "senha-ficticia-nao-utilizada-para-proteger-o-fluxo-de-login"
)

_BLOCKED_PASSWORDS = {
    "admin",
    "admin123",
    "admin123!",
    "administrador",
    "ciranda",
    "ciranda123",
    "motorista",
    "motorista123!",
    "operador",
    "operador123!",
    "password",
    "password1",
    "password123",
    "qwerty",
    "qwerty123",
    "senha",
    "senha123",
    "senha123!",
    "tms123",
    "123456",
    "12345678",
    "123456789",
    "1234567890",
}
_TOKEN_PART_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


@dataclass(frozen=True)
class CreatedAccessToken:
    token: str
    jti: str
    expires_at: datetime
    session_id: str | None = None


@dataclass(frozen=True)
class ParsedRefreshToken:
    session_id: str
    secret: str


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


def verify_dummy_password(plain_password: str) -> None:
    # Evita processar entradas gigantes no Argon2 e preserva custo semelhante.
    candidate = (plain_password[:128] or "credencial-vazia")
    password_hasher.verify(candidate, _DUMMY_PASSWORD_HASH)


def validate_password_policy(
    password: str,
    *,
    email: str | None = None,
    name: str | None = None,
) -> str:
    """Valida comprimento e senhas previsiveis sem impor composicao artificial."""

    if len(password) < settings.password_min_length:
        raise ValueError(
            f"A senha deve possuir pelo menos {settings.password_min_length} caracteres"
        )
    if len(password) > 128:
        raise ValueError("A senha deve possuir no maximo 128 caracteres")
    if password != password.strip():
        raise ValueError("A senha nao pode iniciar ou terminar com espacos")

    normalized = password.casefold()
    compact = "".join(character for character in normalized if character.isalnum())
    if normalized in _BLOCKED_PASSWORDS or compact in {
        "admin123",
        "administrador123",
        "ciranda123",
        "motorista123",
        "operador123",
        "password123",
        "senha123",
        "tms123",
        "12345678",
        "123456789",
    }:
        raise ValueError("Escolha uma senha menos previsivel")

    if email:
        local_part = email.strip().casefold().split("@", 1)[0]
        compact_local = "".join(character for character in local_part if character.isalnum())
        if len(compact_local) >= 4 and compact_local in compact:
            raise ValueError("A senha nao deve conter o e-mail do usuario")
    if name:
        compact_name = "".join(character for character in name.casefold() if character.isalnum())
        if len(compact_name) >= 4 and compact_name in compact:
            raise ValueError("A senha nao deve conter o nome completo do usuario")
    return password


def create_access_token(
    subject: str,
    role: str,
    auth_version: int,
    *,
    session_id: str | None = None,
    expire_minutes: int | None = None,
    token_kind: str = "access",
) -> CreatedAccessToken:
    now = datetime.now(timezone.utc)
    lifetime = expire_minutes or settings.access_token_expire_minutes
    expires_at = now + timedelta(minutes=lifetime)
    jti = secrets.token_urlsafe(24)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "ver": auth_version,
        "jti": jti,
        "typ": token_kind,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": expires_at,
        "nbf": now - timedelta(seconds=5),
        "iat": now,
    }
    if session_id:
        payload["sid"] = session_id
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return CreatedAccessToken(
        token=token,
        jti=jti,
        expires_at=expires_at,
        session_id=session_id,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": [
                    "sub",
                    "ver",
                    "jti",
                    "typ",
                    "iss",
                    "aud",
                    "exp",
                    "nbf",
                    "iat",
                ]
            },
        )
    except InvalidTokenError as exc:
        raise ValueError("Token invalido ou expirado") from exc

    if payload.get("typ") not in {"access", "api_access"}:
        raise ValueError("Tipo de token invalido")
    return payload


def security_digest(scope: str, value: str) -> str:
    message = f"{scope}:{value}".encode("utf-8")
    return hmac.new(settings.secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def new_session_id() -> str:
    return secrets.token_urlsafe(24)


def new_refresh_secret() -> str:
    return secrets.token_urlsafe(48)


def build_refresh_token(session_id: str, secret: str) -> str:
    return f"{session_id}.{secret}"


def parse_refresh_token(token: str | None) -> ParsedRefreshToken | None:
    if not token or token.count(".") != 1:
        return None
    session_id, secret = token.split(".", 1)
    if not _TOKEN_PART_PATTERN.fullmatch(session_id):
        return None
    if not _TOKEN_PART_PATTERN.fullmatch(secret):
        return None
    return ParsedRefreshToken(session_id=session_id, secret=secret)


def refresh_token_hash(session_id: str, secret: str) -> str:
    return security_digest("refresh", f"{session_id}:{secret}")


def generate_csrf_token(session_id: str) -> str:
    nonce = secrets.token_urlsafe(24)
    signature = security_digest("csrf", f"{session_id}:{nonce}")
    return f"{nonce}.{signature}"


def validate_csrf_token(token: str, session_id: str) -> bool:
    if token.count(".") != 1:
        return False
    nonce, signature = token.split(".", 1)
    if not _TOKEN_PART_PATTERN.fullmatch(nonce) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        return False
    expected = security_digest("csrf", f"{session_id}:{nonce}")
    return hmac.compare_digest(signature, expected)


def _cookie_common(max_age: int) -> dict[str, Any]:
    return {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "domain": settings.cookie_domain,
        "max_age": max_age,
    }


def set_browser_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        httponly=True,
        **_cookie_common(settings.access_token_max_age_seconds),
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        **_cookie_common(settings.refresh_token_max_age_seconds),
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        **_cookie_common(settings.refresh_token_max_age_seconds),
    )
    response.headers["Cache-Control"] = "no-store"


def clear_auth_cookies(response: Response) -> None:
    for key, httponly in (
        (settings.auth_cookie_name, True),
        (settings.refresh_cookie_name, True),
        (settings.csrf_cookie_name, False),
    ):
        response.delete_cookie(
            key,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=httponly,
            samesite=settings.cookie_samesite,
        )
    response.headers["Cache-Control"] = "no-store"
