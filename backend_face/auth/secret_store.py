from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from .config import AUTH_DATA_DIR

PREFIX = "enc:v1:"
KEY_FILE = AUTH_DATA_DIR / ".data_key"


def _load_fernet():
    try:
        from cryptography.fernet import Fernet
    except Exception as exc:
        raise RuntimeError(
            "cryptography package is required for encrypted JSON secrets. "
            "Install requirements.txt."
        ) from exc

    env_key = os.getenv("FRS_DATA_ENCRYPTION_KEY", "").strip()
    if env_key:
        try:
            Fernet(env_key.encode("utf-8"))
            return Fernet(env_key.encode("utf-8"))
        except Exception as exc:
            raise RuntimeError("FRS_DATA_ENCRYPTION_KEY is not a valid Fernet key") from exc

    if KEY_FILE.exists():
        raw = KEY_FILE.read_text(encoding="utf-8").strip()
        if raw:
            return Fernet(raw.encode("utf-8"))

    key = Fernet.generate_key()
    KEY_FILE.write_text(key.decode("utf-8"), encoding="utf-8")
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return Fernet(key)


def encrypt_value(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    if not value or value.startswith(PREFIX):
        return value
    token = _load_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return PREFIX + token


def decrypt_value(value: Any) -> Any:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        return value
    token = value[len(PREFIX):]
    try:
        return _load_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        # Keep the raw value so callers can surface a configuration error instead
        # of silently discarding stored credentials.
        return value


def encrypt_fields(data: Dict[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    result = dict(data)
    for field in fields:
        if field in result:
            result[field] = encrypt_value(result[field])
    return result


def decrypt_fields(data: Dict[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    result = dict(data)
    for field in fields:
        if field in result:
            result[field] = decrypt_value(result[field])
    return result


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mask_secret_url(value: Any) -> Any:
    """Mask user/password portions of URL-like secrets before logging/display."""
    if not isinstance(value, str) or not value:
        return value
    try:
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc or "@" not in parts.netloc:
            return value
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        user = parts.username or ""
        masked_user = user if user else "***"
        netloc = f"{masked_user}:***@{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        import re
        return re.sub(r"(?<=://)([^/@:]+):([^/@]+)@", r"\1:***@", value)
