from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.security import (
    clear_auth_cookies,
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    hash_password,
    parse_refresh_token,
    set_browser_cookies,
    validate_password_policy,
    verify_dummy_password,
    verify_password,
)
from app.models.auth import AuthSession, RevokedToken
from app.models.user import User
from app.schemas.auth import BrowserSession, PasswordChange, SessionRead, Token
from app.schemas.user import UserRead
from app.services.audit import register_audit
from app.services.auth_security import (
    PASSWORD_CHANGE_SCOPE,
    cleanup_security_records,
    clear_action_failures,
    clear_login_failures,
    client_ip,
    get_action_lock,
    get_login_lock,
    mask_identifier,
    register_action_failure,
    register_login_failure,
)
from app.services.sessions import (
    BrowserSessionError,
    cleanup_auth_sessions,
    create_browser_session,
    list_user_sessions,
    revoke_session,
    revoke_user_sessions,
    rotate_browser_session,
)


router = APIRouter(prefix="/auth", tags=["Autenticacao"])


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _retry_exception(seconds: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "Muitas tentativas. "
            f"Aguarde {seconds} segundos antes de tentar novamente."
        ),
        headers={"Retry-After": str(seconds)},
    )


def _generic_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha invalidos",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _authenticate_credentials(
    *,
    request: Request,
    form_data: OAuth2PasswordRequestForm,
    db: Session,
    channel: str,
) -> User:
    raw_identifier = (form_data.username or "").strip()
    raw_email = raw_identifier.casefold()[:512]
    email_lookup = raw_email if 3 <= len(raw_identifier) <= 254 else ""
    ip_address = client_ip(request)

    active_lock = get_login_lock(db, raw_email, ip_address)
    if active_lock:
        raise _retry_exception(active_lock.retry_after_seconds)

    user = (
        db.scalar(select(User).where(func.lower(User.email) == email_lookup))
        if email_lookup
        else None
    )
    supplied_password = form_data.password or ""
    candidate_password = supplied_password[:128]
    password_length_valid = 1 <= len(supplied_password) <= 128
    if user and password_length_valid:
        password_matches = verify_password(candidate_password, user.password_hash)
    else:
        verify_dummy_password(candidate_password)
        password_matches = False

    # A resposta e generica para nao revelar se o e-mail existe, se o usuario
    # esta inativo ou se apenas a senha esta incorreta.
    if not user or not password_matches or not user.is_active:
        lock = register_login_failure(db, raw_email, ip_address)
        register_audit(
            db,
            user_id=user.id if user else None,
            action="login_locked" if lock else "login_failed",
            entity_type="auth",
            entity_id=user.id if user else None,
            details={
                "identifier": mask_identifier(raw_email),
                "locked": bool(lock),
                "lock_scope": lock.scope if lock else None,
                "channel": channel,
                "request_id": getattr(request.state, "request_id", None),
            },
            ip_address=ip_address,
        )
        db.commit()

        if lock:
            raise _retry_exception(lock.retry_after_seconds)
        raise _generic_credentials_error()

    clear_login_failures(db, raw_email, ip_address)
    cleanup_security_records(db)
    cleanup_auth_sessions(db)
    return user


def _revoke_api_token(db: Session, request: Request) -> None:
    payload = getattr(request.state, "auth_payload", {}) or {}
    if payload.get("typ") != "api_access":
        return
    jti = str(payload.get("jti", ""))
    exp = payload.get("exp")
    if not jti or exp is None or db.get(RevokedToken, jti) is not None:
        return
    expires_at = datetime.fromtimestamp(float(exp), tz=timezone.utc)
    db.add(RevokedToken(jti=jti, expires_at=expires_at))


def _browser_response(
    response: Response,
    *,
    user: User,
    session_id: str,
    refresh_token: str,
) -> BrowserSession:
    access = create_access_token(
        str(user.id),
        _role_value(user),
        user.auth_version,
        session_id=session_id,
    )
    csrf_token = generate_csrf_token(session_id)
    set_browser_cookies(
        response,
        access_token=access.token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
    )
    return BrowserSession(
        expires_in=settings.access_token_max_age_seconds,
        refresh_expires_in=settings.refresh_token_max_age_seconds,
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=BrowserSession)
def browser_login(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> BrowserSession:
    """Cria sessao de navegador em cookies HttpOnly e refresh rotativo."""

    user = _authenticate_credentials(
        request=request,
        form_data=form_data,
        db=db,
        channel="browser",
    )
    created = create_browser_session(db, user, request)
    register_audit(
        db,
        user_id=user.id,
        action="login",
        entity_type="auth",
        entity_id=user.id,
        details={
            "session": created.session.id[-10:],
            "channel": "browser",
            "password_change_required": user.must_change_password,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return _browser_response(
        response,
        user=user,
        session_id=created.session.id,
        refresh_token=created.refresh_token,
    )


def _refresh_failure_response() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Sessao expirada. Entre novamente."},
        headers={"WWW-Authenticate": "Bearer"},
    )
    clear_auth_cookies(response)
    return response


@router.post("/refresh", response_model=BrowserSession)
def refresh_browser_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> BrowserSession | Response:
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    parsed = parse_refresh_token(raw_refresh)
    try:
        rotated = rotate_browser_session(db, raw_refresh, request)
        user = db.get(User, rotated.session.user_id)
        if not user or not user.is_active:
            rotated.session.revoked_at = datetime.now(timezone.utc)
            raise BrowserSessionError("inactive")
    except BrowserSessionError as exc:
        user_id = None
        if parsed:
            session = db.get(AuthSession, parsed.session_id)
            user_id = session.user_id if session else None
        action = {
            "reuse": "refresh_reuse",
            "stale": "refresh_stale",
        }.get(exc.reason, "refresh_failed")
        register_audit(
            db,
            user_id=user_id,
            action=action,
            entity_type="auth",
            entity_id=parsed.session_id[-10:] if parsed else None,
            details={
                "reason": exc.reason,
                "request_id": getattr(request.state, "request_id", None),
            },
            ip_address=client_ip(request),
        )
        db.commit()
        if exc.reason == "stale":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": {
                        "code": "refresh_already_rotated",
                        "message": "A sessao ja foi renovada por outra aba.",
                    }
                },
                headers={"Retry-After": "1", "Cache-Control": "no-store"},
            )
        return _refresh_failure_response()

    db.commit()
    return _browser_response(
        response,
        user=user,
        session_id=rotated.session.id,
        refresh_token=rotated.refresh_token,
    )


@router.post("/token", response_model=Token)
def api_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> Token:
    """Emite Bearer token de curta duracao para integracoes aprovadas."""

    if not settings.enable_api_token_endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso nao encontrado",
        )

    user = _authenticate_credentials(
        request=request,
        form_data=form_data,
        db=db,
        channel="api",
    )
    token = create_access_token(
        str(user.id),
        _role_value(user),
        user.auth_version,
        expire_minutes=settings.api_token_expire_minutes,
        token_kind="api_access",
    )
    register_audit(
        db,
        user_id=user.id,
        action="login",
        entity_type="auth",
        entity_id=user.id,
        details={"token_jti": token.jti[-8:], "channel": "api"},
        ip_address=client_ip(request),
    )
    db.commit()
    return Token(
        access_token=token.token,
        expires_in=settings.api_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    parsed_refresh = parse_refresh_token(request.cookies.get(settings.refresh_cookie_name))
    session = db.get(AuthSession, parsed_refresh.session_id) if parsed_refresh else None
    user_id = session.user_id if session else None
    revoke_session(db, parsed_refresh.session_id if parsed_refresh else None)

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(raw_token)
            if payload.get("typ") == "api_access":
                jti = str(payload.get("jti", ""))
                exp = payload.get("exp")
                if jti and exp is not None and db.get(RevokedToken, jti) is None:
                    db.add(
                        RevokedToken(
                            jti=jti,
                            expires_at=datetime.fromtimestamp(float(exp), tz=timezone.utc),
                        )
                    )
                user_id = int(payload.get("sub"))
        except (ValueError, TypeError):
            pass

    if user_id:
        register_audit(
            db,
            user_id=user_id,
            action="logout",
            entity_type="auth",
            entity_id=user_id,
            ip_address=client_ip(request),
        )
    cleanup_security_records(db)
    cleanup_auth_sessions(db)
    db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    revoked = revoke_user_sessions(db, current_user.id)
    _revoke_api_token(db, request)
    register_audit(
        db,
        user_id=current_user.id,
        action="logout_all",
        entity_type="auth",
        entity_id=current_user.id,
        details={"sessions_revoked": revoked},
        ip_address=client_ip(request),
    )
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.get("/sessions", response_model=list[SessionRead])
def get_sessions(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[SessionRead]:
    current_id = getattr(request.state, "session_id", None)
    return [
        SessionRead(
            id=item.id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            current=item.id == current_id,
        )
        for item in list_user_sessions(db, current_user.id)
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    session = db.get(AuthSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    revoke_session(db, session_id)
    register_audit(
        db,
        user_id=current_user.id,
        action="session_revoke",
        entity_type="auth_session",
        entity_id=session_id[-10:],
        ip_address=client_ip(request),
    )
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if session_id == getattr(request.state, "session_id", None):
        clear_auth_cookies(response)
    return response


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    ip_address = client_ip(request)
    reauth_key = f"{current_user.id}:{ip_address}"
    active_lock = get_action_lock(db, PASSWORD_CHANGE_SCOPE, reauth_key)
    if active_lock:
        raise _retry_exception(active_lock.retry_after_seconds)

    if not verify_password(payload.current_password, current_user.password_hash):
        lock = register_action_failure(
            db,
            PASSWORD_CHANGE_SCOPE,
            reauth_key,
            threshold=settings.login_max_attempts,
        )
        register_audit(
            db,
            user_id=current_user.id,
            action="password_change_locked" if lock else "password_change_failed",
            entity_type="auth",
            entity_id=current_user.id,
            details={"locked": bool(lock)},
            ip_address=ip_address,
        )
        db.commit()
        if lock:
            raise _retry_exception(lock.retry_after_seconds)
        raise HTTPException(status_code=400, detail="Senha atual invalida")

    clear_action_failures(db, PASSWORD_CHANGE_SCOPE, reauth_key)
    try:
        validate_password_policy(
            payload.new_password,
            email=current_user.email,
            name=current_user.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=422, detail="A nova senha deve ser diferente da atual")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.auth_version += 1
    current_user.must_change_password = False
    revoked = revoke_user_sessions(db, current_user.id)
    _revoke_api_token(db, request)
    register_audit(
        db,
        user_id=current_user.id,
        action="password_change",
        entity_type="user",
        entity_id=current_user.id,
        details={"sessions_revoked": revoked},
        ip_address=ip_address,
    )
    db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> User:
    return current_user
