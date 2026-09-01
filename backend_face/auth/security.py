from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

import bcrypt
import jwt

from .config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

SECRET_KEY = JWT_SECRET
ALGORITHM = JWT_ALGORITHM


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        hashed = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(plain, hashed)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    raw = password.encode('utf-8') if isinstance(password, str) else password
    if len(raw) < 8:
        raise ValueError("Password must be at least 8 characters")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode('utf-8')


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    expires = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = data.copy()
    payload.update({
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            return None
        return {
            "username": username,
            "role": role,
            "company_id": payload.get("company_id"),
            "jti": payload.get("jti"),
            "exp": payload.get("exp"),
        }
    except jwt.PyJWTError:
        return None


def authenticate_user(username: str, password: str, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from .storage import get_users
    user = get_users().get(username)
    if not user or not user.get("is_active", True):
        return None
    if not verify_password(password, user.get("hashed_password", "")):
        return None
    if role and user.get("role") != role:
        return None
    return user
