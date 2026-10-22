#!/usr/bin/env python3
"""Teste seguro e nao destrutivo de uma publicacao do TMS."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import getpass
import http.cookiejar
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _json_response(response) -> Any:
    raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else None


def _request(opener, url: str, *, method: str = "GET", data: bytes | None = None, headers=None):
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "User-Agent": "TMS-Production-Smoke-Test/1.0",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            **(headers or {}),
        },
    )
    return opener.open(request, timeout=20)


def run(base_url: str, login: bool) -> int:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        print("[ERRO] Informe uma URL HTTPS valida, por exemplo https://seu-servico.onrender.com")
        return 2

    base_url = base_url.rstrip("/")
    cookie_jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    checks: list[CheckResult] = []

    try:
        with _request(opener, f"{base_url}/api/v1/health/ready") as response:
            body = _json_response(response)
            ready = response.status == 200 and body == {
                "status": "ready",
                "service": "tms",
                "database": "ok",
            }
            checks.append(CheckResult("Saude da aplicacao e banco", ready, f"HTTP {response.status}: {body}"))

        with _request(opener, f"{base_url}/") as response:
            response.read()
            required_headers = {
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "content-security-policy": None,
                "strict-transport-security": None,
                "x-request-id": None,
            }
            missing = []
            for header, expected in required_headers.items():
                actual = response.headers.get(header)
                if not actual or (expected is not None and actual != expected):
                    missing.append(header)
            checks.append(
                CheckResult(
                    "HTTPS e cabecalhos de seguranca",
                    response.status == 200 and not missing,
                    "OK" if not missing else f"Ausentes ou invalidos: {', '.join(missing)}",
                )
            )

        if login:
            email = input("E-mail do administrador para o teste: ").strip()
            password = getpass.getpass("Senha (nao sera exibida): ")
            if not email or not password:
                raise ValueError("E-mail e senha sao obrigatorios para testar o login")

            login_data = urlencode({"username": email, "password": password}).encode("utf-8")
            with _request(
                opener,
                f"{base_url}/api/v1/auth/login",
                method="POST",
                data=login_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": base_url,
                    "Referer": f"{base_url}/",
                },
            ) as response:
                body = _json_response(response)
                user = (body or {}).get("user", {}) if isinstance(body, dict) else {}
                checks.append(
                    CheckResult(
                        "Login do administrador",
                        response.status == 200 and user.get("email", "").casefold() == email.casefold(),
                        f"HTTP {response.status}; usuario={user.get('email', 'nao retornado')}",
                    )
                )

            with _request(opener, f"{base_url}/api/v1/auth/me") as response:
                body = _json_response(response)
                checks.append(
                    CheckResult(
                        "Sessao autenticada",
                        response.status == 200 and isinstance(body, dict),
                        f"HTTP {response.status}",
                    )
                )

            csrf_cookie = next(
                (cookie.value for cookie in cookie_jar if cookie.name.endswith("tms_csrf")),
                None,
            )
            if csrf_cookie:
                with _request(
                    opener,
                    f"{base_url}/api/v1/auth/logout",
                    method="POST",
                    data=b"",
                    headers={
                        "X-CSRF-Token": csrf_cookie,
                        "Origin": base_url,
                        "Referer": f"{base_url}/",
                    },
                ) as response:
                    response.read()
                    checks.append(CheckResult("Logout protegido por CSRF", response.status == 204, f"HTTP {response.status}"))
            else:
                checks.append(CheckResult("Logout protegido por CSRF", False, "Cookie CSRF nao encontrado"))

    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        print(f"[ERRO] HTTP {exc.code} em {exc.url}: {detail[:500]}")
        return 1
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERRO] Nao foi possivel concluir o teste: {exc}")
        return 1

    print("\nResultado do teste online")
    print("=" * 31)
    for item in checks:
        marker = "OK" if item.ok else "FALHA"
        print(f"[{marker}] {item.name}: {item.detail}")

    failures = [item for item in checks if not item.ok]
    if failures:
        print(f"\nPublicacao reprovada: {len(failures)} verificacao(oes) falharam.")
        return 1

    print("\nPublicacao aprovada nos testes automaticos nao destrutivos.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa uma publicacao HTTPS do TMS")
    parser.add_argument("--url", required=True, help="URL HTTPS da aplicacao")
    parser.add_argument(
        "--login",
        action="store_true",
        help="Tambem testa login, sessao e logout; a senha e solicitada de forma oculta",
    )
    args = parser.parse_args()
    return run(args.url, args.login)


if __name__ == "__main__":
    sys.exit(main())
