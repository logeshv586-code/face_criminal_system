from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import List

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
AUTH_DATA_DIR = DATA_DIR / "auth"
AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except Exception:
        return default


def _load_or_create_secret(env_name: str, filename: str, nbytes: int = 48) -> str:
    env_value = os.getenv(env_name)
    if env_value and env_value.strip():
        return env_value.strip()

    path = AUTH_DATA_DIR / filename
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value

    value = secrets.token_urlsafe(nbytes)
    path.write_text(value, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return value


JWT_SECRET = _load_or_create_secret("FRS_JWT_SECRET", ".jwt_secret")
JWT_ALGORITHM = os.getenv("FRS_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _int_env("FRS_ACCESS_TOKEN_MINUTES", 60)
RESET_TOKEN_EXPIRE_MINUTES = _int_env("FRS_RESET_TOKEN_MINUTES", 20)
LOGIN_MAX_ATTEMPTS = _int_env("FRS_LOGIN_MAX_ATTEMPTS", 5)
LOGIN_WINDOW_SECONDS = _int_env("FRS_LOGIN_WINDOW_SECONDS", 300)
MAX_IMAGE_UPLOAD_MB = _int_env("FRS_MAX_IMAGE_UPLOAD_MB", 12)
MAX_VIDEO_UPLOAD_MB = _int_env("FRS_MAX_VIDEO_UPLOAD_MB", 1024)

_raw_origins = os.getenv(
    "FRS_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,file://,null"
)
CORS_ORIGINS: List[str] = [x.strip() for x in _raw_origins.split(",") if x.strip()]

AUTO_MIGRATE_JSON = os.getenv("FRS_AUTO_MIGRATE_JSON", "1").lower() in {"1", "true", "yes", "on"}
AUTO_BACKFILL_GALLERY = os.getenv("FRS_AUTO_BACKFILL_GALLERY", "1").lower() in {"1", "true", "yes", "on"}
DEV_SHOW_RESET_TOKEN = os.getenv("FRS_DEV_SHOW_RESET_TOKEN", "0").lower() in {"1", "true", "yes", "on"}
ENABLE_LEGACY_DIRECT_STREAM = os.getenv("FRS_ENABLE_LEGACY_DIRECT_STREAM", "0").lower() in {"1", "true", "yes", "on"}
ENABLE_LEGACY_WEBRTC_CONNECT = os.getenv("FRS_ENABLE_LEGACY_WEBRTC_CONNECT", "0").lower() in {"1", "true", "yes", "on"}

