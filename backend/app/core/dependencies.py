from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.auth import RevokedToken
from app.models.enums import UserRole
from app.models.user import User
from app.services.sessions import get_active_session


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token",
    auto_error=False,
)
DbSession = Annotated[Session, Depends(get_db)]
OptionalBearerToken = Annotated[str | None, Depends(oauth2_scheme)]

_PASSWORD_CHANGE_ALLOWED_PATHS = {
    f"{settings.api_v1_prefix}/auth/me",
    f"{settings.api_v1_prefix}/auth/logout",
    f"{settings.api_v1_prefix}/auth/refresh",
    f"{settings.api_v1_prefix}/auth/change-password",
}


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas ou sessao expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )


def token_from_request(request: Request, bearer_token: str | None) -> tuple[str | None, str]:
    if bearer_token:
        return bearer_token, "bearer"
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    return cookie_token, "cookie" if cookie_token else "none"


def get_current_user(
    request: Request,
    db: DbSession,
    bearer_token: OptionalBearerToken,
) -> User:
    token, source = token_from_request(request, bearer_token)
    if not token:
        raise _credentials_error()

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", ""))
        auth_version = int(payload.get("ver", 0))
        jti = str(payload.get("jti", ""))
        session_id = str(payload.get("sid", "")) or None
        token_kind = str(payload.get("typ", ""))
    except (ValueError, TypeError):
        raise _credentials_error()

    if not jti:
        raise _credentials_error()

    if session_id:
        browser_session = get_active_session(db, session_id)
        if not browser_session or browser_session.user_id != user_id:
            raise _credentials_error()
    elif token_kind == "api_access":
        if db.get(RevokedToken, jti) is not None:
            raise _credentials_error()
    else:
        # Tokens de navegador precisam estar ligados a uma sessao persistida.
        raise _credentials_error()

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active or user.auth_version != auth_version:
        raise _credentials_error()

    request.state.auth_token = token
    request.state.auth_payload = payload
    request.state.auth_source = source
    request.state.session_id = session_id

    if user.must_change_password and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "password_change_required",
                "message": "Troca de senha obrigatoria antes de continuar",
            },
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _role_value(role: UserRole | str) -> str:
    return role.value if isinstance(role, UserRole) else str(role)


def require_roles(*roles: UserRole) -> Callable[..., User]:
    allowed_values = {_role_value(role) for role in roles}

    def role_checker(current_user: CurrentUser) -> User:
        if _role_value(current_user.role) not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Voce nao possui permissao para esta acao",
            )
        return current_user

    return role_checker
