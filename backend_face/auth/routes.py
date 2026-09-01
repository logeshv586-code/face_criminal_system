import hashlib
import logging
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES, DEV_SHOW_RESET_TOKEN, LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS, RESET_TOKEN_EXPIRE_MINUTES,
)
from .license_dates import parse_license_datetime
from .secret_store import fingerprint
from .security import authenticate_user, create_access_token
from .storage import (
    ensure_auth_data_dir, get_tokens, save_tokens, get_password_resets,
    save_password_resets,
)
from .users import create_user, get_user, list_users, update_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

_attempts = defaultdict(deque)
_attempt_lock = threading.Lock()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=512)
    role: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    email: Optional[str] = None
    assigned_menus: list
    license_start_date: Optional[str] = None
    license_end_date: Optional[str] = None
    company_id: Optional[str] = None
    expires_in: int


class BootstrapSuperAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=512)


class ForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)


class ResetPasswordRequest(BaseModel):
    username: str
    token: str
    new_password: str = Field(min_length=8, max_length=512)


class UserResponse(BaseModel):
    username: str
    role: str
    email: Optional[str] = None
    is_active: bool
    assigned_cameras: list
    assigned_menus: list
    max_users_limit: Optional[int] = 0
    max_cameras_limit: Optional[int] = 0
    company_id: Optional[str] = None
    license_start_date: Optional[str] = None
    license_end_date: Optional[str] = None


def _key(username: str, request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{username.strip().lower()}"


def _check_rate_limit(key: str):
    now = time.time()
    with _attempt_lock:
        q = _attempts[key]
        while q and now - q[0] > LOGIN_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= LOGIN_MAX_ATTEMPTS:
            retry = max(1, int(LOGIN_WINDOW_SECONDS - (now - q[0])))
            raise HTTPException(status_code=429, detail=f"Too many login attempts. Try again in {retry} seconds.")


def _record_failure(key: str):
    with _attempt_lock:
        _attempts[key].append(time.time())


def _clear_failures(key: str):
    with _attempt_lock:
        _attempts.pop(key, None)


def _revoke_user_tokens(username: str):
    tokens = get_tokens()
    changed = False
    for token, meta in list(tokens.items()):
        if meta.get("username") == username:
            tokens.pop(token, None)
            changed = True
    if changed:
        save_tokens(tokens)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request):
    ensure_auth_data_dir()
    key = _key(payload.username, request)
    _check_rate_limit(key)

    user = get_user(payload.username)
    effective_role = payload.role or (user.get("role") if user else None)
    auth_user = authenticate_user(payload.username, payload.password, effective_role)
    if not auth_user:
        _record_failure(key)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if auth_user.get("role") == "Admin" and auth_user.get("license_end_date"):
        end_dt = parse_license_datetime(auth_user.get("license_end_date"))
        if not end_dt or end_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="License expired. Contact SuperAdmin.")

    _clear_failures(key)
    token_data = {
        "sub": auth_user["username"],
        "role": auth_user["role"],
        "company_id": auth_user.get("company_id"),
    }
    access_token = create_access_token(token_data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    now = int(datetime.now(timezone.utc).timestamp())
    tokens = get_tokens()
    # prune stale metadata so tokens.json does not grow forever
    for token, meta in list(tokens.items()):
        if meta.get("expires_at", now + 1) <= now:
            tokens.pop(token, None)
    tokens[fingerprint(access_token)] = {
        "username": auth_user["username"],
        "role": auth_user["role"],
        "company_id": auth_user.get("company_id"),
        "issued_at": now,
        "expires_at": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    save_tokens(tokens)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=auth_user["role"],
        username=auth_user["username"],
        email=auth_user.get("email"),
        assigned_menus=auth_user.get("assigned_menus", auth_user.get("menus", [])),
        license_start_date=auth_user.get("license_start_date"),
        license_end_date=auth_user.get("license_end_date"),
        company_id=auth_user.get("company_id"),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request):
    user = request.scope.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse(
        username=user["username"], role=user["role"], email=user.get("email"),
        is_active=user.get("is_active", True), assigned_cameras=user.get("assigned_cameras", []),
        assigned_menus=user.get("assigned_menus", user.get("menus", [])),
        max_users_limit=user.get("max_users_limit", 0), max_cameras_limit=user.get("max_cameras_limit", 0),
        company_id=user.get("company_id"), license_start_date=user.get("license_start_date"),
        license_end_date=user.get("license_end_date"),
    )


@router.post("/bootstrap/superadmin")
async def bootstrap_superadmin(payload: BootstrapSuperAdminRequest):
    ensure_auth_data_dir()
    if any(user.get("role") == "SuperAdmin" for user in list_users()):
        raise HTTPException(status_code=400, detail="SuperAdmin already exists")
    created = create_user(payload.username, payload.password, "SuperAdmin", "system")
    return {"message": "SuperAdmin created successfully", "username": created["username"]}


@router.post("/logout")
async def logout(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        tokens = get_tokens()
        token_key = fingerprint(token)
        if token_key in tokens:
            tokens.pop(token_key, None)
            save_tokens(tokens)
    return {"message": "Logout successful"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    generic = {"message": "If the account is valid and email is configured, reset instructions have been sent."}
    user = get_user(payload.username)
    if not user or not user.get("email"):
        return generic

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = int(datetime.now(timezone.utc).timestamp())
    resets = get_password_resets()
    resets[payload.username] = {
        "token_hash": token_hash,
        "expires_at": now + RESET_TOKEN_EXPIRE_MINUTES * 60,
        "created_at": now,
        "used": False,
    }
    save_password_resets(resets)

    from .email_utils import send_email
    body = (
        f"Hello {payload.username},\n\n"
        f"Use this one-time reset token within {RESET_TOKEN_EXPIRE_MINUTES} minutes:\n\n"
        f"{raw_token}\n\nIf you did not request this, ignore this message."
    )
    sent = send_email(user["email"], "Face Recognition System password reset", body)
    if not sent:
        logger.warning("Password reset token created but SMTP is not configured for %s", payload.username)

    response = dict(generic)
    if DEV_SHOW_RESET_TOKEN:
        response["dev_reset_token"] = raw_token
    return response


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    user = get_user(payload.username)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    resets = get_password_resets()
    entry = resets.get(payload.username) or {}
    now = int(datetime.now(timezone.utc).timestamp())
    supplied_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    if (
        entry.get("used") or entry.get("expires_at", 0) < now or
        not secrets.compare_digest(entry.get("token_hash", ""), supplied_hash)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    update_user(payload.username, {"password": payload.new_password})
    entry["used"] = True
    resets[payload.username] = entry
    save_password_resets(resets)
    _revoke_user_tokens(payload.username)
    logger.info("Password reset completed for %s", payload.username)
    return {"message": "Password has been reset successfully. Please sign in again."}
