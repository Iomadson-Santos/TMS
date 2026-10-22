from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import tempfile

# As configuracoes precisam existir antes da importacao da aplicacao.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="tms-security-tests-"))
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite:///{(_TEST_DIR / 'security.db').as_posix()}",
        "SECRET_KEY": "security-test-secret-" + "x" * 64,
        "AUTO_CREATE_TABLES": "true",
        "BOOTSTRAP_ADMIN_ENABLED": "false",
        "DEMO_SEED_ENABLED": "false",
        "LOGIN_MAX_ATTEMPTS": "3",
        "LOGIN_IP_MAX_ATTEMPTS": "50",
        "LOGIN_LOCK_SECONDS": "5",
        "LOGIN_LOCK_MAX_SECONDS": "30",
        "PASSWORD_MIN_LENGTH": "12",
        "ENABLE_API_DOCS": "false",
        "ENABLE_API_TOKEN_ENDPOINT": "true",
        "ALLOWED_HOSTS": "*",
        "COOKIE_SECURE": "false",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        "SESSION_IDLE_MINUTES": "720",
    }
)

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select

from app.core.config import Settings, settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.auth import AuthSession, LoginThrottle, RevokedToken
from app.models.base import Base, utc_now
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, RouteStatus, UserRole, VehicleStatus
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.scripts.create_admin import create_admin
from app.scripts.ensure_initial_admin import ensure_initial_admin


ADMIN_EMAIL = "security.admin@example.com"
ADMIN_PASSWORD = "Uma senha longa #2026"
OPERATOR_EMAIL = "security.operator@example.com"
OPERATOR_PASSWORD = "Outra senha longa #2026"
FORCED_EMAIL = "security.forced@example.com"
FORCED_PASSWORD = "Temporaria forte #2026"
NEW_PASSWORD = "Nova senha segura #2026"
DRIVER_A_EMAIL = "driver.a@example.com"
DRIVER_A_PASSWORD = "Motorista A seguro #2026"
DRIVER_B_EMAIL = "driver.b@example.com"
DRIVER_B_PASSWORD = "Motorista B seguro #2026"


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add_all(
            [
                User(
                    name="Administrador de Seguranca",
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    is_active=True,
                    must_change_password=False,
                ),
                User(
                    name="Operador de Seguranca",
                    email=OPERATOR_EMAIL,
                    password_hash=hash_password(OPERATOR_PASSWORD),
                    role=UserRole.OPERATOR,
                    is_active=True,
                    must_change_password=False,
                ),
                User(
                    name="Usuario Temporario",
                    email=FORCED_EMAIL,
                    password_hash=hash_password(FORCED_PASSWORD),
                    role=UserRole.DRIVER,
                    is_active=True,
                    must_change_password=True,
                ),
                User(
                    name="Motorista A",
                    email=DRIVER_A_EMAIL,
                    password_hash=hash_password(DRIVER_A_PASSWORD),
                    role=UserRole.DRIVER,
                    is_active=True,
                    must_change_password=False,
                ),
                User(
                    name="Motorista B",
                    email=DRIVER_B_EMAIL,
                    password_hash=hash_password(DRIVER_B_PASSWORD),
                    role=UserRole.DRIVER,
                    is_active=True,
                    must_change_password=False,
                ),
            ]
        )
        db.commit()
    yield


def login_browser(client: TestClient, email: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


def csrf_header(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("tms_csrf")
    assert token
    return {"X-CSRF-Token": token}


def create_driver_routes() -> tuple[int, int, int, int]:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        driver_a = db.scalar(select(User).where(User.email == DRIVER_A_EMAIL))
        driver_b = db.scalar(select(User).where(User.email == DRIVER_B_EMAIL))
        assert admin and driver_a and driver_b

        vehicle_a = Vehicle(
            plate="AAA1A11",
            brand="Teste",
            model="Van A",
            current_km=0,
            status=VehicleStatus.AVAILABLE,
        )
        vehicle_b = Vehicle(
            plate="BBB2B22",
            brand="Teste",
            model="Van B",
            current_km=0,
            status=VehicleStatus.AVAILABLE,
        )
        db.add_all([vehicle_a, vehicle_b])
        db.flush()

        route_a = Route(
            name="Rota privada A",
            vehicle_id=vehicle_a.id,
            driver_id=driver_a.id,
            created_by_id=admin.id,
            status=RouteStatus.OPEN,
        )
        route_b = Route(
            name="Rota privada B",
            vehicle_id=vehicle_b.id,
            driver_id=driver_b.id,
            created_by_id=admin.id,
            status=RouteStatus.OPEN,
        )
        db.add_all([route_a, route_b])
        db.flush()

        delivery_a = Delivery(
            invoice_number="NF-A",
            customer_name="Cliente A",
            address="Rua A, 1",
            city="Sao Paulo",
            state="SP",
            status=DeliveryStatus.PENDING,
            route_id=route_a.id,
            sequence=1,
        )
        delivery_b = Delivery(
            invoice_number="NF-B",
            customer_name="Cliente B",
            address="Rua B, 2",
            city="Sao Paulo",
            state="SP",
            status=DeliveryStatus.PENDING,
            route_id=route_b.id,
            sequence=1,
        )
        db.add_all([delivery_a, delivery_b])
        db.commit()
        return route_a.id, route_b.id, delivery_a.id, delivery_b.id


def test_create_admin_service_uses_argon2_and_forces_first_password_change():
    email = "novo.admin@example.com"
    password = "Senha temporaria segura #2026"

    created = create_admin("Novo Administrador", email, password)

    with SessionLocal() as db:
        stored = db.scalar(select(User).where(User.email == email))
        assert stored is not None
        assert stored.id == created.id
        assert stored.role == UserRole.ADMIN
        assert stored.is_active is True
        assert stored.must_change_password is True
        assert stored.password_hash.startswith("$argon2")
        assert verify_password(password, stored.password_hash) is True



def test_security_headers_are_present():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "https://tile.openstreetmap.org" in response.headers["content-security-policy"]
    assert response.headers["cache-control"].startswith("no-store")
    assert response.headers.get("x-request-id")
    assert "server" not in {key.lower() for key in response.headers}


def test_tracking_page_sends_origin_referrer_for_map_tiles():
    with TestClient(app) as client:
        response = client.get("/tracking")
    assert response.status_code == 200
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "https://tile.openstreetmap.org" in response.headers["content-security-policy"]


def test_three_failures_lock_identity_and_success_clears_counter():
    with TestClient(app) as client:
        first = login_browser(client, ADMIN_EMAIL, "senha errada 1")
        second = login_browser(client, ADMIN_EMAIL, "senha errada 2")
        third = login_browser(client, ADMIN_EMAIL, "senha errada 3")
        locked_valid = login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.headers["retry-after"] == "5"
        assert locked_valid.status_code == 429

        with SessionLocal() as db:
            identity = db.scalar(
                select(LoginThrottle).where(LoginThrottle.scope == "identity")
            )
            assert identity
            identity.locked_until = utc_now() - timedelta(seconds=1)
            db.commit()

        success = login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert success.status_code == 200
        assert "access_token" not in success.json()
        assert success.json()["user"]["email"] == ADMIN_EMAIL

        with SessionLocal() as db:
            assert list(db.scalars(select(LoginThrottle)).all()) == []


def test_lock_duration_progresses_after_another_failed_sequence():
    with TestClient(app) as client:
        for _ in range(3):
            response = login_browser(client, ADMIN_EMAIL, "senha incorreta")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "5"

        with SessionLocal() as db:
            identity = db.scalar(
                select(LoginThrottle).where(LoginThrottle.scope == "identity")
            )
            assert identity
            identity.locked_until = utc_now() - timedelta(seconds=1)
            db.commit()

        for _ in range(3):
            response = login_browser(client, ADMIN_EMAIL, "senha incorreta")
        assert response.status_code == 429
        assert response.headers["retry-after"] == "10"


def test_browser_session_uses_httponly_cookies_signed_csrf_and_revocable_logout():
    with TestClient(app) as client:
        response = login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert response.status_code == 200
        cookie_headers = response.headers.get_list("set-cookie")
        access_cookie = next(item for item in cookie_headers if item.startswith("tms_session="))
        refresh_cookie = next(item for item in cookie_headers if item.startswith("tms_refresh="))
        csrf_cookie = next(item for item in cookie_headers if item.startswith("tms_csrf="))
        assert "HttpOnly" in access_cookie
        assert "HttpOnly" in refresh_cookie
        assert "SameSite=lax" in access_cookie
        assert "HttpOnly" not in csrf_cookie

        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 403

        logged_out = client.post("/api/v1/auth/logout", headers=csrf_header(client))
        assert logged_out.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

        with SessionLocal() as db:
            session = db.scalar(select(AuthSession))
            assert session is not None
            assert session.revoked_at is not None


def test_csrf_token_is_bound_to_the_browser_session():
    with TestClient(app) as first, TestClient(app) as second:
        assert login_browser(first, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        assert login_browser(second, OPERATOR_EMAIL, OPERATOR_PASSWORD).status_code == 200

        stolen_csrf = first.cookies.get("tms_csrf")
        assert stolen_csrf
        second.cookies.set("tms_csrf", stolen_csrf)
        response = second.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": stolen_csrf},
        )
        assert response.status_code == 403
        assert second.get("/api/v1/auth/me").status_code == 200


def test_parallel_refresh_within_grace_never_issues_token_to_stale_request(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "refresh_rotation_grace_seconds", 30)
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        old_refresh = client.cookies.get("tms_refresh")
        old_csrf = client.cookies.get("tms_csrf")
        assert old_refresh and old_csrf

        refreshed = client.post("/api/v1/auth/refresh", headers=csrf_header(client))
        assert refreshed.status_code == 200

        with TestClient(app) as stale_client:
            stale_client.cookies.set("tms_refresh", old_refresh)
            stale_client.cookies.set("tms_csrf", old_csrf)
            stale = stale_client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": old_csrf},
            )
            assert stale.status_code == 409
            assert stale.json()["detail"]["code"] == "refresh_already_rotated"
            assert "set-cookie" not in stale.headers

        # A tentativa concorrente nao invalida a sessao legitima nem entrega uma
        # nova credencial ao portador do token antigo.
        assert client.get("/api/v1/auth/me").status_code == 200


def test_refresh_token_rotates_and_reuse_revokes_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "refresh_rotation_grace_seconds", 0)
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        old_refresh = client.cookies.get("tms_refresh")
        old_csrf = client.cookies.get("tms_csrf")
        assert old_refresh and old_csrf

        refreshed = client.post("/api/v1/auth/refresh", headers=csrf_header(client))
        assert refreshed.status_code == 200
        new_refresh = client.cookies.get("tms_refresh")
        assert new_refresh and new_refresh != old_refresh

        with TestClient(app) as attacker:
            attacker.cookies.set("tms_refresh", old_refresh)
            attacker.cookies.set("tms_csrf", old_csrf)
            reused = attacker.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": old_csrf},
            )
            assert reused.status_code == 401

        # O uso de um refresh antigo fora da janela revoga a sessao inteira.
        assert client.get("/api/v1/auth/me").status_code == 401


def test_password_change_reauthentication_is_throttled_after_three_failures():
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200

        responses = []
        for _ in range(3):
            responses.append(
                client.post(
                    "/api/v1/auth/change-password",
                    headers=csrf_header(client),
                    json={
                        "current_password": "Senha atual incorreta #2026",
                        "new_password": NEW_PASSWORD,
                    },
                )
            )

        assert [item.status_code for item in responses] == [400, 400, 429]
        assert responses[-1].headers["retry-after"] == "5"

        # Mesmo com a senha atual correta, a reautenticacao permanece bloqueada
        # ate o prazo terminar. Isso impede tentativas automatizadas na sessao.
        locked_correct = client.post(
            "/api/v1/auth/change-password",
            headers=csrf_header(client),
            json={
                "current_password": ADMIN_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )
        assert locked_correct.status_code == 429

        with SessionLocal() as db:
            record = db.scalar(
                select(LoginThrottle).where(
                    LoginThrottle.scope == "password_change"
                )
            )
            assert record is not None
            assert record.locked_until is not None


def test_forced_password_change_blocks_other_api_actions():
    with TestClient(app) as client:
        response = login_browser(client, FORCED_EMAIL, FORCED_PASSWORD)
        assert response.status_code == 200
        assert response.json()["user"]["must_change_password"] is True

        blocked = client.get("/api/v1/routes")
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["code"] == "password_change_required"

        changed = client.post(
            "/api/v1/auth/change-password",
            headers=csrf_header(client),
            json={
                "current_password": FORCED_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )
        assert changed.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

        assert login_browser(client, FORCED_EMAIL, FORCED_PASSWORD).status_code == 401
        assert login_browser(client, FORCED_EMAIL, NEW_PASSWORD).status_code == 200


def test_users_endpoint_is_admin_only_and_bearer_token_can_be_revoked():
    with TestClient(app) as client:
        operator_token = client.post(
            "/api/v1/auth/token",
            data={"username": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD},
        )
        assert operator_token.status_code == 200
        token = operator_token.json()["access_token"]
        assert client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 403

        admin_token = client.post(
            "/api/v1/auth/token",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        ).json()["access_token"]
        users = client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert users.status_code == 200
        assert len(users.json()) == 5

        logged_out = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert logged_out.status_code == 204
        assert client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
        ).status_code == 401
        with SessionLocal() as db:
            assert db.scalar(select(RevokedToken)) is not None


def test_admin_cannot_reset_own_password_without_reauthentication():
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        me = client.get("/api/v1/auth/me").json()
        response = client.patch(
            f"/api/v1/users/{me['id']}",
            headers=csrf_header(client),
            json={"password": "Outra senha administrativa #2026"},
        )
        assert response.status_code == 409
        assert "Trocar senha" in response.json()["detail"]
        assert client.get("/api/v1/auth/me").status_code == 200



def test_api_password_grant_can_be_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "enable_api_token_endpoint", False)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/token",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
    assert response.status_code == 404


def test_driver_can_only_access_own_route_and_delivery():
    route_a, route_b, delivery_a, delivery_b = create_driver_routes()
    with TestClient(app) as client:
        assert login_browser(client, DRIVER_A_EMAIL, DRIVER_A_PASSWORD).status_code == 200

        routes = client.get("/api/v1/routes")
        assert routes.status_code == 200
        assert [item["id"] for item in routes.json()] == [route_a]
        assert client.get(f"/api/v1/routes/{route_b}").status_code == 403

        deliveries = client.get("/api/v1/deliveries")
        assert deliveries.status_code == 200
        assert [item["id"] for item in deliveries.json()] == [delivery_a]
        assert client.get(f"/api/v1/deliveries/{delivery_b}").status_code == 403
        assert client.get("/api/v1/tracking/live").status_code == 403
        assert client.get("/api/v1/users/drivers/options").status_code == 403


def test_driver_cannot_start_two_routes_at_the_same_time():
    route_a, _, _, _ = create_driver_routes()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        driver_a = db.scalar(select(User).where(User.email == DRIVER_A_EMAIL))
        assert admin and driver_a
        vehicle = Vehicle(
            plate="CCC3C33",
            model="Van C",
            current_km=0,
            status=VehicleStatus.AVAILABLE,
        )
        db.add(vehicle)
        db.flush()
        second_route = Route(
            name="Segunda rota A",
            vehicle_id=vehicle.id,
            driver_id=driver_a.id,
            created_by_id=admin.id,
            status=RouteStatus.OPEN,
        )
        db.add(second_route)
        db.commit()
        second_route_id = second_route.id

    with TestClient(app) as client:
        assert login_browser(client, DRIVER_A_EMAIL, DRIVER_A_PASSWORD).status_code == 200
        first = client.patch(
            f"/api/v1/routes/{route_a}/status",
            headers=csrf_header(client),
            json={"status": "em_andamento"},
        )
        assert first.status_code == 200
        duplicate = client.patch(
            f"/api/v1/routes/{second_route_id}/status",
            headers=csrf_header(client),
            json={"status": "em_andamento"},
        )
        assert duplicate.status_code == 409


def test_validation_errors_do_not_echo_password_and_origin_is_checked():
    secret_payload = "nao-deve-aparecer-" * 20
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        invalid = client.post(
            "/api/v1/users",
            headers=csrf_header(client),
            json={
                "name": "Conta de Teste",
                "email": "conta@example.com",
                "password": secret_payload,
                "role": "operador",
            },
        )
        assert invalid.status_code == 422
        assert secret_payload not in invalid.text

        hostile = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://evil.example"},
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert hostile.status_code == 403


def test_request_body_limit_rejects_oversized_request():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            content=b"x" * 1_100_000,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert response.status_code == 413


def test_whitespace_and_unknown_fields_are_rejected():
    with TestClient(app) as client:
        assert login_browser(client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
        whitespace = client.post(
            "/api/v1/vehicles",
            headers=csrf_header(client),
            json={
                "plate": "ABC1D23",
                "model": "   ",
                "current_km": 0,
                "status": "disponivel",
            },
        )
        assert whitespace.status_code == 422

        unknown = client.post(
            "/api/v1/vehicles",
            headers=csrf_header(client),
            json={
                "plate": "ABC1D24",
                "model": "Van segura",
                "current_km": 0,
                "status": "disponivel",
                "is_admin": True,
            },
        )
        assert unknown.status_code == 422


def test_production_preflight_rejects_unsafe_and_accepts_hardened_configuration():
    unsafe = Settings(environment="production")
    assert unsafe.production_security_errors()

    secure = Settings(
        environment="production",
        debug=False,
        public_base_url="https://tms.example.com",
        enable_api_docs=False,
        enable_api_token_endpoint=False,
        secret_key="A7!bC2@dE3#fG4$hI5%jK6&lM7*nO8(pQ9)rS0_tU1-vW2+xY3=",
        access_token_expire_minutes=15,
        api_token_expire_minutes=30,
        refresh_token_expire_days=7,
        refresh_rotation_grace_seconds=30,
        session_idle_minutes=720,
        max_active_sessions_per_user=5,
        database_url="postgresql+psycopg://tms:secret@127.0.0.1:5432/tms",
        auto_create_tables=False,
        bootstrap_admin_enabled=False,
        bootstrap_admin_password="Senha temporaria forte #2026",
        demo_seed_enabled=False,
        auth_cookie_name="__Host-tms_session",
        refresh_cookie_name="__Host-tms_refresh",
        csrf_cookie_name="__Host-tms_csrf",
        cookie_secure=True,
        cookie_samesite="lax",
        cookie_domain=None,
        cors_origins="https://tms.example.com",
        allowed_hosts="tms.example.com",
        force_https=True,
        hsts_enabled=True,
        password_min_length=15,
        login_max_attempts=3,
        login_lock_seconds=30,
        login_lock_max_seconds=300,
        log_file="../logs/tms.log",
    )
    assert secure.production_security_errors() == []

    managed_proxy = secure.model_copy(
        update={"force_https": False, "platform_https_enforced": True}
    )
    assert managed_proxy.production_security_errors() == []


def test_readiness_endpoint_checks_database_connection():
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "tms",
        "database": "ok",
    }


def test_render_postgres_url_is_normalized_for_psycopg3():
    direct = Settings(database_url="postgresql://user:secret@db.internal:5432/tms")
    legacy = Settings(database_url="postgres://user:secret@db.internal:5432/tms")

    expected = "postgresql+psycopg://user:secret@db.internal:5432/tms"
    assert direct.database_url == expected
    assert legacy.database_url == expected


def test_initial_admin_bootstrap_is_idempotent_and_never_uses_demo_seed(
    monkeypatch: pytest.MonkeyPatch,
):
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()

    email = "initial.admin@example.com"
    password = "Frase longa exclusiva #2026"
    monkeypatch.setenv("INITIAL_ADMIN_NAME", "Responsavel Inicial")
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", email)
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", password)

    assert ensure_initial_admin() == 0
    assert ensure_initial_admin() == 0

    with SessionLocal() as db:
        users = list(db.scalars(select(User)).all())

    assert len(users) == 1
    assert users[0].email == email
    assert users[0].role == UserRole.ADMIN
    assert users[0].must_change_password is True
    assert verify_password(password, users[0].password_hash) is True
