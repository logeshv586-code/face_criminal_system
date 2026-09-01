"""One-time/idempotent hardening for legacy JSON-first deployments.

The application intentionally keeps JSON as the current write format. This helper
protects secret fields in-place before services load them, while leaving normal
metadata readable for the JSON -> DB migration bridge.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from auth.config import AUTH_DATA_DIR, DATA_DIR
from auth.secret_store import encrypt_fields, encrypt_value, PREFIX
from auth.storage import atomic_write_json

SECRET_SETTING_FIELDS = {
    "smtp_password", "smtp_api_key", "redis_password", "database_password",
    "backup_password", "client_secret", "api_secret"
}


def _load(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def secure_existing_json_secrets() -> Dict[str, Any]:
    result = {"settings_files": 0, "camera_records": 0, "legacy_tokens_revoked": 0, "errors": []}

    # Encrypt secret values in every company/global settings JSON.
    for path in AUTH_DATA_DIR.glob("settings*.json"):
        try:
            data = _load(path, {})
            if not isinstance(data, dict):
                continue
            protected = encrypt_fields(data, SECRET_SETTING_FIELDS)
            if protected != data:
                atomic_write_json(path, protected)
            result["settings_files"] += 1
        except Exception as exc:
            result["errors"].append(f"{path.name}: {exc}")

    # Encrypt full RTSP URLs on disk. They are decrypted only inside the backend.
    cameras_path = DATA_DIR / "camera_management" / "cameras.json"
    try:
        cameras = _load(cameras_path, [])
        if isinstance(cameras, list):
            changed = False
            for camera in cameras:
                if not isinstance(camera, dict):
                    continue
                url = camera.get("rtsp_url")
                if isinstance(url, str) and url and not url.startswith(PREFIX):
                    camera["rtsp_url"] = encrypt_value(url)
                    changed = True
                    result["camera_records"] += 1
            if changed:
                atomic_write_json(cameras_path, cameras)
    except Exception as exc:
        result["errors"].append(f"cameras.json: {exc}")

    # Old releases stored raw bearer tokens as JSON keys. New releases store only
    # SHA-256 fingerprints. Revoke legacy entries rather than carrying them over.
    tokens_path = AUTH_DATA_DIR / "tokens.json"
    try:
        tokens = _load(tokens_path, {})
        if isinstance(tokens, dict):
            safe = {k: v for k, v in tokens.items() if len(k) == 64 and all(c in "0123456789abcdef" for c in k.lower())}
            result["legacy_tokens_revoked"] = len(tokens) - len(safe)
            if safe != tokens:
                atomic_write_json(tokens_path, safe)
    except Exception as exc:
        result["errors"].append(f"tokens.json: {exc}")

    # An obsolete secret file from older builds must not be used or shipped.
    legacy_secret = AUTH_DATA_DIR / "jwt_secret.txt"
    try:
        if legacy_secret.exists():
            legacy_secret.unlink()
    except Exception as exc:
        result["errors"].append(f"jwt_secret.txt: {exc}")

    return result


if __name__ == "__main__":
    print(secure_existing_json_secrets())
