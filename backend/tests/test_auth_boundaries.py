"""Authentication and authorization behavior at request/database boundaries."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from src import admin_auth, api_auth, auth_middleware


def _request(
    path: str = "/api/private",
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> Request:
    encoded_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": encoded_headers,
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 123),
        }
    )


def test_resolve_authenticated_user_from_state_and_headers(monkeypatch):
    db = object()
    user = SimpleNamespace(id=3, is_admin=False)
    get_user = MagicMock(return_value=user)
    by_key = MagicMock(return_value=user)
    monkeypatch.setattr(api_auth.crud, "get_user", get_user)
    monkeypatch.setattr(api_auth.crud, "get_user_by_api_key", by_key)

    request = _request()
    request.state.authenticated_user_id = 3
    assert api_auth._resolve_authenticated_user(request, db) is user
    get_user.assert_called_once_with(db, 3)

    key = str(uuid.uuid4())
    assert api_auth._resolve_authenticated_user(_request(headers={"x-api-key": key}), db) is user
    assert by_key.call_args.args[1] == uuid.UUID(key)
    assert api_auth._resolve_authenticated_user(
        _request(headers={"authorization": f"Bearer {key}"}), db
    ) is user
    assert api_auth._resolve_authenticated_user(_request(), db) is None
    assert api_auth._resolve_authenticated_user(
        _request(headers={"x-api-key": "invalid"}), db
    ) is None


def test_authenticated_and_admin_dependencies(monkeypatch):
    request = _request()
    user = SimpleNamespace(id=7, is_admin=True)
    monkeypatch.setattr(api_auth, "_resolve_authenticated_user", lambda _request, _db: user)
    assert api_auth.authenticated_user_id(request, object()) == 7
    assert request.state.authenticated_is_admin is True
    assert api_auth.require_admin_user(request, object()) == 7

    request = _request()
    monkeypatch.setattr(
        api_auth,
        "_resolve_authenticated_user",
        lambda _request, _db: SimpleNamespace(id=8, is_admin=False),
    )
    with pytest.raises(HTTPException) as exc:
        api_auth.require_admin_user(request, object())
    assert exc.value.status_code == 403

    monkeypatch.setattr(api_auth, "_resolve_authenticated_user", lambda _request, _db: None)
    with pytest.raises(HTTPException) as exc:
        api_auth.authenticated_user_id(_request(), object())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_api_key_bearer_and_failure(monkeypatch):
    key = uuid.uuid4()
    user = SimpleNamespace(id=5)
    db = MagicMock()
    by_key = MagicMock(return_value=user)
    by_id = MagicMock(return_value=user)
    tracked = MagicMock()
    monkeypatch.setattr(api_auth.crud, "get_user_by_api_key", by_key)
    monkeypatch.setattr(api_auth.crud, "get_user", by_id)
    monkeypatch.setattr(api_auth, "_track_usage", tracked)

    request = _request()
    assert await api_auth.get_current_user(request, None, str(key), db) is user
    tracked.assert_called_with(db, 5, "/api/private", "GET", "api_key")

    tracked.reset_mock()
    credentials = SimpleNamespace(credentials=str(key))
    assert await api_auth.get_current_user(request, credentials, None, db) is user
    tracked.assert_called_with(db, 5, "/api/private", "GET", "api_key")

    by_key.return_value = None
    credentials = SimpleNamespace(credentials="5")
    assert await api_auth.get_current_user(request, credentials, None, db) is user
    tracked.assert_called_with(db, 5, "/api/private", "GET", "bearer_token")

    by_id.return_value = None
    with pytest.raises(HTTPException) as exc:
        await api_auth.get_current_user(request, SimpleNamespace(credentials="bad"), "bad", db)
    assert exc.value.status_code == 401
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


def test_usage_tracking_commits_or_rolls_back():
    db = MagicMock()
    api_auth._track_usage(db, 2, "/api", "GET", "api_key")
    usage = db.add.call_args.args[0]
    assert usage.user_id == 2
    assert usage.authenticated_via == "api_key"
    db.commit.assert_called_once()

    db = MagicMock()
    db.commit.side_effect = RuntimeError("database down")
    api_auth._track_usage(db, 2, "/api", "GET", "api_key")
    db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_auth_middleware_bypass_and_missing_key(monkeypatch):
    middleware = object.__new__(auth_middleware.AuthMiddleware)
    call_next = AsyncMock(return_value=Response("ok", status_code=200))

    assert (await middleware.dispatch(_request("/landing"), call_next)).status_code == 200
    assert (await middleware.dispatch(_request("/api/auth/login"), call_next)).status_code == 200
    assert (await middleware.dispatch(_request("/api/private", method="OPTIONS"), call_next)).status_code == 200

    monkeypatch.setenv("TESTING", "1")
    assert (await middleware.dispatch(_request("/api/private"), call_next)).status_code == 200
    monkeypatch.delenv("TESTING")

    response = await middleware.dispatch(_request("/api/private"), call_next)
    assert response.status_code == 401
    assert json.loads(response.body) == {"detail": "Authentication required."}


@pytest.mark.asyncio
async def test_auth_middleware_rejects_invalid_inactive_and_accepts_active(monkeypatch):
    middleware = object.__new__(auth_middleware.AuthMiddleware)
    monkeypatch.delenv("TESTING", raising=False)
    db = MagicMock()
    session_factory = MagicMock(return_value=db)
    monkeypatch.setattr(auth_middleware, "SessionLocal", session_factory)
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(
        _request("/api/private", headers={"x-api-key": "bad"}),
        call_next,
    )
    assert response.status_code == 401
    db.close.assert_called_once()

    key = str(uuid.uuid4())
    monkeypatch.setattr(auth_middleware.crud, "get_user_by_api_key", lambda _db, _key: None)
    response = await middleware.dispatch(
        _request("/api/private", headers={"authorization": f"Bearer {key}"}),
        call_next,
    )
    assert json.loads(response.body)["detail"] == "Invalid or expired API key."

    monkeypatch.setattr(
        auth_middleware.crud,
        "get_user_by_api_key",
        lambda _db, _key: SimpleNamespace(id=4, is_active=False, is_admin=False),
    )
    response = await middleware.dispatch(
        _request("/api/private", headers={"x-api-key": key}),
        call_next,
    )
    assert response.status_code == 403

    captured: dict[str, object] = {}

    async def next_request(request):
        captured["user_id"] = request.state.authenticated_user_id
        captured["is_admin"] = request.state.authenticated_is_admin
        return Response("ok")

    monkeypatch.setattr(
        auth_middleware.crud,
        "get_user_by_api_key",
        lambda _db, _key: SimpleNamespace(id=9, is_active=True, is_admin=True),
    )
    response = await middleware.dispatch(
        _request("/api/private", headers={"x-api-key": key}),
        next_request,
    )
    assert response.status_code == 200
    assert captured == {"user_id": 9, "is_admin": True}


@pytest.mark.parametrize(
    ("user", "status_code"),
    [
        (None, 404),
        (SimpleNamespace(is_active=False, is_admin=True), 403),
        (SimpleNamespace(is_active=True, is_admin=False), 403),
    ],
)
def test_admin_requirements_reject_invalid_users(monkeypatch, user, status_code):
    monkeypatch.setattr(admin_auth.crud, "get_user", lambda _db, _user_id: user)
    with pytest.raises(HTTPException) as exc:
        admin_auth.require_admin(1, object())
    assert exc.value.status_code == status_code


def test_admin_requirements_accept_active_admin_and_check_active(monkeypatch):
    admin = SimpleNamespace(is_active=True, is_admin=True)
    monkeypatch.setattr(admin_auth.crud, "get_user", lambda _db, _user_id: admin)
    assert admin_auth.require_admin(1, object()) is admin
    assert admin_auth.check_user_active(1, object()) is None

    monkeypatch.setattr(admin_auth.crud, "get_user", lambda _db, _user_id: None)
    with pytest.raises(HTTPException) as exc:
        admin_auth.check_user_active(1, object())
    assert exc.value.status_code == 404

    monkeypatch.setattr(
        admin_auth.crud,
        "get_user",
        lambda _db, _user_id: SimpleNamespace(is_active=False),
    )
    with pytest.raises(HTTPException) as exc:
        admin_auth.check_user_active(1, object())
    assert exc.value.status_code == 403
