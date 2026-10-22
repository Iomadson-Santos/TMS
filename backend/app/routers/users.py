from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.security import hash_password, validate_password_policy
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import DriverOption, UserCreate, UserRead, UserUpdate
from app.services.audit import register_audit
from app.services.auth_security import client_ip
from app.services.sessions import revoke_user_sessions


router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserRead])
def list_users(
    role: UserRole | None = Query(default=None),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[User]:
    statement = select(User).order_by(User.name)
    if role is not None:
        statement = statement.where(User.role == role)
    if active is not None:
        statement = statement.where(User.is_active == active)
    return list(db.scalars(statement).all())


@router.get("/drivers/options", response_model=list[DriverOption])
def list_driver_options(
    active: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> list[User]:
    # O seletor retorna somente ID e nome e fica restrito a operacao.
    statement = (
        select(User)
        .where(User.role == UserRole.DRIVER)
        .order_by(User.name)
    )
    if active:
        statement = statement.where(User.is_active.is_(True))
    return list(db.scalars(statement).all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    email = str(payload.email).strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(status_code=409, detail="E-mail ja cadastrado")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    register_audit(
        db,
        user_id=current_user.id,
        action="create",
        entity_type="user",
        entity_id=user.id,
        details={"email": user.email, "role": user.role.value},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    changes = payload.model_dump(exclude_unset=True)
    changed_fields = set(changes)

    if user.id == current_user.id:
        if changes.get("is_active") is False:
            raise HTTPException(status_code=409, detail="Voce nao pode desativar o proprio usuario")
        if "role" in changes and changes["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=409, detail="Voce nao pode remover o proprio perfil de administrador")
        if "password" in changes:
            raise HTTPException(
                status_code=409,
                detail="Use a tela Trocar senha para alterar a propria credencial",
            )

    removing_active_admin = (
        user.role == UserRole.ADMIN
        and user.is_active
        and (
            changes.get("is_active") is False
            or ("role" in changes and changes["role"] != UserRole.ADMIN)
        )
    )
    if removing_active_admin:
        active_admins = int(
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
            )
            or 0
        )
        if active_admins <= 1:
            raise HTTPException(
                status_code=409,
                detail="O sistema precisa manter ao menos um administrador ativo",
            )

    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).strip().lower()
        duplicate = db.scalar(
            select(User).where(func.lower(User.email) == email, User.id != user_id)
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="E-mail ja cadastrado")
        changes["email"] = email

    if "password" in changes:
        password = changes.pop("password")
        if password:
            try:
                validate_password_policy(
                    password,
                    email=str(changes.get("email") or user.email),
                    name=str(changes.get("name") or user.name),
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            user.password_hash = hash_password(password)
            user.must_change_password = True

    invalidate_sessions = bool(
        changed_fields.intersection({"password", "email", "role", "is_active"})
    )
    revoked_sessions = 0
    if invalidate_sessions:
        user.auth_version += 1
        revoked_sessions = revoke_user_sessions(db, user.id)

    for field, value in changes.items():
        setattr(user, field, value)

    register_audit(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="user",
        entity_id=user.id,
        details={
            "fields": sorted(changed_fields),
            "sessions_invalidated": invalidate_sessions,
            "sessions_revoked": revoked_sessions,
        },
        ip_address=client_ip(request),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dados duplicados") from exc

    db.refresh(user)
    return user

