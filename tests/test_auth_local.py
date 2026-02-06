"""Unit tests for local authentication helpers."""

from __future__ import annotations

from src.app.auth import (
    authenticate_local,
    hash_password,
    init_auth_db,
    register_local,
    verify_password,
)


def test_hash_password_roundtrip() -> None:
    password = "StrongPass_123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong-pass", hashed)


def test_register_creates_pending_user_and_blocks_login(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("COT_AUTH_DB_PATH", str(db_path))
    monkeypatch.delenv("COT_ADMIN_EMAIL", raising=False)

    init_auth_db()
    ok, msg = register_local("user@example.com", "StrongPass_123!")
    assert ok
    assert "successful" in msg.lower()

    login_ok, login_err = authenticate_local("user@example.com", "StrongPass_123!")
    assert not login_ok
    assert "pending" in login_err.lower()


def test_admin_email_gets_admin_active_access(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("COT_AUTH_DB_PATH", str(db_path))
    monkeypatch.setenv("COT_ADMIN_EMAIL", "owner@example.com")

    init_auth_db()
    ok, msg = register_local("owner@example.com", "StrongPass_123!")
    assert ok
    assert "successful" in msg.lower()

    login_ok, login_err = authenticate_local("owner@example.com", "StrongPass_123!")
    assert login_ok
    assert login_err == ""
