"""Authentication and authorization helpers for Streamlit app."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLE_USER = "user"
ROLE_ADMIN = "admin"
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"

ROLE_PERMISSIONS = {
    ROLE_USER: {"view_app"},
    ROLE_ADMIN: {"view_app", "run_pipeline", "manage_users"},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _db_path() -> Path:
    env_path = os.environ.get("COT_AUTH_DB_PATH", "").strip()
    if env_path:
        return Path(env_path).resolve()
    return Path(__file__).resolve().parents[2] / "data" / "app" / "auth.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending',
                auth_provider TEXT NOT NULL DEFAULT 'local',
                created_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                last_login_at_utc TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at_utc TEXT NOT NULL,
                last_seen_at_utc TEXT NOT NULL,
                expires_at_utc TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()


def _session_ttl_days() -> int:
    raw = os.environ.get("COT_SESSION_TTL_DAYS", "30").strip()
    try:
        days = int(raw)
        return max(1, min(days, 365))
    except Exception:
        return 30


def _utc_after_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _get_query_param_auth_token() -> str | None:
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get("auth")
            if isinstance(val, list):
                return str(val[0]).strip() if val else None
            return str(val).strip() if val else None
    except Exception:
        pass

    try:
        params = st.experimental_get_query_params()
        val = params.get("auth", [""])[0]
        return str(val).strip() if val else None
    except Exception:
        return None


def _set_query_param_auth_token(token: str) -> None:
    try:
        if hasattr(st, "query_params"):
            st.query_params["auth"] = token
            return
    except Exception:
        pass

    try:
        st.experimental_set_query_params(auth=token)
    except Exception:
        pass


def _clear_query_param_auth_token() -> None:
    try:
        if hasattr(st, "query_params"):
            if "auth" in st.query_params:
                del st.query_params["auth"]
            return
    except Exception:
        pass

    try:
        params = st.experimental_get_query_params()
        params.pop("auth", None)
        st.experimental_set_query_params(**params)
    except Exception:
        pass


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _admin_email() -> str:
    return _normalize_email(os.environ.get("COT_ADMIN_EMAIL", ""))


def _is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def _status_label(status: str) -> str:
    s = (status or "").strip().lower()
    if s == STATUS_PENDING:
        return "pending approval"
    if s == STATUS_DISABLED:
        return "disabled"
    return "active"


def _parse_hash(password_hash: str) -> tuple[int, bytes, bytes] | None:
    # Format: pbkdf2_sha256$<iterations>$<salt_b64>$<digest_b64>
    try:
        algo, iters, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return None
        return int(iters), base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    except Exception:
        return None


def verify_password(password: str, password_hash: str) -> bool:
    parsed = _parse_hash(password_hash)
    if parsed is None:
        return False
    iterations, salt, expected_digest = parsed
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def hash_password(password: str, iterations: int = 210_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def _upsert_admin_role_if_needed(email: str) -> None:
    admin_email = _admin_email()
    if not admin_email or email != admin_email:
        return

    with _connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET role = ?, status = ?, updated_at_utc = ?
            WHERE email = ?
            """,
            (ROLE_ADMIN, STATUS_ACTIVE, _utc_now(), email),
        )
        conn.commit()


def _get_user_by_email(email: str) -> sqlite3.Row | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return row


def _create_session_for_user(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    now = _utc_now()
    expires = _utc_after_days(_session_ttl_days())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at_utc, last_seen_at_utc, expires_at_utc, revoked)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (token, user_id, now, now, expires),
        )
        conn.commit()
    return token


def _load_user_by_session_token(token: str) -> sqlite3.Row | None:
    now = _utc_now()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
              AND s.revoked = 0
              AND s.expires_at_utc > ?
            """,
            (token, now),
        ).fetchone()
        if row is not None:
            conn.execute(
                "UPDATE sessions SET last_seen_at_utc = ? WHERE token = ?",
                (now, token),
            )
            conn.commit()
    return row


def _revoke_session_token(token: str | None) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("UPDATE sessions SET revoked = 1 WHERE token = ?", (token,))
        conn.commit()


def _remember_login(user: sqlite3.Row) -> None:
    try:
        token = _create_session_for_user(int(user["id"]))
        st.session_state["auth_token"] = token
        _set_query_param_auth_token(token)
    except Exception:
        # Keep authentication working even if remember-session fails.
        pass


def register_local(email: str, password: str) -> tuple[bool, str]:
    init_auth_db()
    email_norm = _normalize_email(email)

    if not _is_valid_email(email_norm):
        return False, "Invalid email format."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."

    if _get_user_by_email(email_norm) is not None:
        return False, "User with this email already exists."

    now = _utc_now()
    is_admin = bool(_admin_email()) and email_norm == _admin_email()
    role = ROLE_ADMIN if is_admin else ROLE_USER
    status = STATUS_ACTIVE if is_admin else STATUS_PENDING

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (email, password_hash, role, status, auth_provider, created_at_utc, updated_at_utc)
            VALUES (?, ?, ?, ?, 'local', ?, ?)
            """,
            (email_norm, hash_password(password), role, status, now, now),
        )
        conn.commit()

    return True, "Registration successful. You can sign in after admin approval." if status == STATUS_PENDING else "Registration successful."


def authenticate_local(email: str, password: str) -> tuple[bool, str]:
    init_auth_db()
    email_norm = _normalize_email(email)
    user = _get_user_by_email(email_norm)

    if user is None:
        return False, "Invalid email or password."

    _upsert_admin_role_if_needed(email_norm)
    user = _get_user_by_email(email_norm)
    if user is None:
        return False, "Invalid email or password."

    if (user["auth_provider"] or "local") not in {"local", "mixed"}:
        return False, "Use Google login for this account."

    if not verify_password(password, str(user["password_hash"] or "")):
        return False, "Invalid email or password."

    status = (user["status"] or STATUS_PENDING).strip().lower()
    if status != STATUS_ACTIVE:
        return False, f"Account is {_status_label(status)}."

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login_at_utc = ?, updated_at_utc = ? WHERE email = ?",
            (_utc_now(), _utc_now(), email_norm),
        )
        conn.commit()

    _set_auth_session(user_email=email_norm, role=str(user["role"] or ROLE_USER), status=status, method="local")
    _remember_login(user)
    return True, ""


def _google_enabled() -> bool:
    return os.environ.get("COT_ENABLE_GOOGLE_LOGIN", "false").strip().lower() in {"1", "true", "yes"}


def _streamlit_google_email() -> str | None:
    if not hasattr(st, "user"):
        return None
    try:
        user_obj = st.user
        if not getattr(user_obj, "is_logged_in", False):
            return None
        email = getattr(user_obj, "email", None)
        if not email:
            return None
        return _normalize_email(str(email))
    except Exception:
        return None


def _attempt_google_login() -> None:
    if not hasattr(st, "login"):
        st.error("Google login is not supported by current Streamlit version.")
        return
    try:
        st.login("google")
    except Exception as exc:
        st.error(f"Google login failed to start: {exc}")


def _google_logout() -> None:
    if hasattr(st, "logout"):
        try:
            st.logout()
        except Exception:
            pass


def _set_auth_session(*, user_email: str, role: str, status: str, method: str) -> None:
    role_norm = (role or ROLE_USER).strip().lower()
    if role_norm not in ROLE_PERMISSIONS:
        role_norm = ROLE_USER

    status_norm = (status or STATUS_PENDING).strip().lower()
    perms = sorted(ROLE_PERMISSIONS.get(role_norm, set())) if status_norm == STATUS_ACTIVE else []

    st.session_state["auth_email"] = _normalize_email(user_email)
    st.session_state["auth_role"] = role_norm
    st.session_state["auth_status"] = status_norm
    st.session_state["auth_permissions"] = perms
    st.session_state["auth_is_admin"] = role_norm == ROLE_ADMIN and status_norm == STATUS_ACTIVE
    st.session_state["auth_method"] = method


def _clear_auth_state() -> None:
    for k in [
        "auth_email",
        "auth_role",
        "auth_status",
        "auth_permissions",
        "auth_is_admin",
        "auth_method",
        "auth_token",
    ]:
        st.session_state.pop(k, None)


def has_permission(permission: str) -> bool:
    perms = set(st.session_state.get("auth_permissions", []))
    return permission in perms


def _sync_google_user(email: str) -> tuple[bool, str]:
    init_auth_db()
    email_norm = _normalize_email(email)
    now = _utc_now()
    user = _get_user_by_email(email_norm)

    if user is None:
        is_admin = bool(_admin_email()) and email_norm == _admin_email()
        role = ROLE_ADMIN if is_admin else ROLE_USER
        status = STATUS_ACTIVE if is_admin else STATUS_PENDING
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO users (email, password_hash, role, status, auth_provider, created_at_utc, updated_at_utc, last_login_at_utc)
                VALUES (?, NULL, ?, ?, 'google', ?, ?, ?)
                """,
                (email_norm, role, status, now, now, now),
            )
            conn.commit()
        user = _get_user_by_email(email_norm)
    else:
        _upsert_admin_role_if_needed(email_norm)
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET auth_provider = 'google', last_login_at_utc = ?, updated_at_utc = ? WHERE email = ?",
                (now, now, email_norm),
            )
            conn.commit()
        user = _get_user_by_email(email_norm)

    if user is None:
        return False, "Failed to load user."

    status = (user["status"] or STATUS_PENDING).strip().lower()
    if status != STATUS_ACTIVE:
        return False, f"Account is {_status_label(status)}."

    _set_auth_session(user_email=email_norm, role=str(user["role"] or ROLE_USER), status=status, method="google")
    _remember_login(user)
    return True, ""


def _list_users_df() -> pd.DataFrame:
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, email, role, status, auth_provider, created_at_utc, updated_at_utc, last_login_at_utc FROM users ORDER BY created_at_utc DESC"
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "email", "role", "status", "auth_provider", "created_at_utc", "updated_at_utc", "last_login_at_utc"])
    return pd.DataFrame([dict(r) for r in rows])


def _update_user_role_status(email: str, role: str, status: str) -> tuple[bool, str]:
    email_norm = _normalize_email(email)
    role_norm = (role or ROLE_USER).strip().lower()
    status_norm = (status or STATUS_PENDING).strip().lower()

    if role_norm not in {ROLE_USER, ROLE_ADMIN}:
        return False, "Invalid role."
    if status_norm not in {STATUS_PENDING, STATUS_ACTIVE, STATUS_DISABLED}:
        return False, "Invalid status."

    if _admin_email() and email_norm == _admin_email() and role_norm != ROLE_ADMIN:
        return False, "Admin email role cannot be changed from admin."

    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET role = ?, status = ?, updated_at_utc = ? WHERE email = ?",
            (role_norm, status_norm, _utc_now(), email_norm),
        )
        conn.commit()

    if cur.rowcount == 0:
        return False, "User not found."
    return True, "User updated."


def _render_login_screen() -> None:
    st.title("Sign In")
    st.caption("Login required to use the platform.")

    google_available = _google_enabled()
    tabs = ["Sign In", "Register"]
    if google_available:
        tabs.append("Google")
    tab_objs = st.tabs(tabs)
    signin_tab = tab_objs[0]
    register_tab = tab_objs[1]
    google_tab = tab_objs[2] if len(tab_objs) > 2 else None

    with signin_tab:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", key="login_password", type="password")
        if st.button("Sign In", key="login_submit", use_container_width=True):
            ok, err = authenticate_local(email, password)
            if not ok:
                st.error(err)
            else:
                st.rerun()

    with register_tab:
        r_email = st.text_input("Email", key="register_email")
        r_password = st.text_input("Password", key="register_password", type="password")
        r_password2 = st.text_input("Confirm password", key="register_password2", type="password")
        if st.button("Create account", key="register_submit", use_container_width=True):
            if r_password != r_password2:
                st.error("Passwords do not match.")
            else:
                ok, msg = register_local(r_email, r_password)
                if not ok:
                    st.error(msg)
                else:
                    st.success(msg)

    if google_tab is not None:
        with google_tab:
            st.write("Continue with Google account.")
            if st.button("Continue with Google", key="login_google_btn", use_container_width=True):
                _attempt_google_login()


def require_authentication() -> bool:
    init_auth_db()

    google_email = _streamlit_google_email()
    if google_email:
        ok, err = _sync_google_user(google_email)
        if not ok:
            st.error(err)
            return False

    # Try to restore persisted session token (survives app restarts).
    if not st.session_state.get("auth_email"):
        token = _get_query_param_auth_token()
        if token:
            user = _load_user_by_session_token(token)
            if user is None:
                _clear_query_param_auth_token()
            else:
                status = (user["status"] or STATUS_PENDING).strip().lower()
                role = (user["role"] or ROLE_USER).strip().lower()
                if status == STATUS_ACTIVE:
                    _set_auth_session(
                        user_email=str(user["email"]),
                        role=role,
                        status=status,
                        method="token",
                    )
                    st.session_state["auth_token"] = token
                else:
                    _revoke_session_token(token)
                    _clear_query_param_auth_token()

    if st.session_state.get("auth_email"):
        # Enforce active status on every run in case admin changed status.
        current_user = _get_user_by_email(_normalize_email(st.session_state.get("auth_email", "")))
        if current_user is None:
            _revoke_session_token(st.session_state.get("auth_token"))
            _clear_query_param_auth_token()
            _clear_auth_state()
            _render_login_screen()
            return False

        status = (current_user["status"] or STATUS_PENDING).strip().lower()
        role = (current_user["role"] or ROLE_USER).strip().lower()
        if status != STATUS_ACTIVE:
            _revoke_session_token(st.session_state.get("auth_token"))
            _clear_query_param_auth_token()
            _clear_auth_state()
            st.error(f"Account is {_status_label(status)}.")
            _render_login_screen()
            return False

        _set_auth_session(
            user_email=str(current_user["email"]),
            role=role,
            status=status,
            method=st.session_state.get("auth_method", "local"),
        )
        return True

    _render_login_screen()
    return False


def _render_user_management() -> None:
    st.markdown("### User Management")
    users_df = _list_users_df()
    if users_df.empty:
        st.caption("No users yet.")
        return

    st.dataframe(users_df, use_container_width=True, hide_index=True)

    emails = users_df["email"].tolist()
    selected_email = st.selectbox("User", options=emails, key="admin_user_select")

    current = users_df[users_df["email"] == selected_email].iloc[0]
    role_idx = 0 if current["role"] == ROLE_USER else 1
    status_options = [STATUS_PENDING, STATUS_ACTIVE, STATUS_DISABLED]
    status_idx = status_options.index(current["status"]) if current["status"] in status_options else 0

    new_role = st.selectbox("Role", options=[ROLE_USER, ROLE_ADMIN], index=role_idx, key="admin_user_role")
    new_status = st.selectbox("Status", options=status_options, index=status_idx, key="admin_user_status")

    if st.button("Save user", key="admin_user_save", use_container_width=True):
        ok, msg = _update_user_role_status(selected_email, new_role, new_status)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def render_auth_sidebar() -> None:
    email = st.session_state.get("auth_email")
    if not email:
        return

    with st.sidebar:
        st.markdown("---")
        st.caption(f"Signed in as: {email}")
        role_label = st.session_state.get("auth_role", ROLE_USER)
        status_label = st.session_state.get("auth_status", STATUS_PENDING)
        st.caption(f"Role: {role_label}")
        st.caption(f"Status: {status_label}")

        if has_permission("manage_users"):
            with st.expander("Admin", expanded=False):
                _render_user_management()

        if st.button("Log out", key="logout_btn", use_container_width=True):
            method = st.session_state.get("auth_method")
            _revoke_session_token(st.session_state.get("auth_token"))
            _clear_query_param_auth_token()
            _clear_auth_state()
            if method == "google":
                _google_logout()
            st.rerun()
