import json
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from .config import AUTH_DATA_DIR, DATA_DIR
from .secret_store import encrypt_fields, decrypt_fields

USERS_FILE = AUTH_DATA_DIR / "users.json"
SETTINGS_FILE = AUTH_DATA_DIR / "settings.json"
COMPANIES_FILE = AUTH_DATA_DIR / "companies.json"
CAMERAS_FILE = DATA_DIR / "cameras.json"
TOKENS_FILE = AUTH_DATA_DIR / "tokens.json"
RESET_TOKENS_FILE = AUTH_DATA_DIR / "password_resets.json"

_lock = threading.RLock()


def ensure_auth_data_dir():
    AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Any):
    ensure_auth_data_dir()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        temp_path = path.with_suffix(path.suffix + '.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        temp_path.replace(path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {} if default is None else default


def get_users() -> Dict[str, Any]:
    return load_json(USERS_FILE, {})


def save_users(users: Dict[str, Any]):
    atomic_write_json(USERS_FILE, users)


DEFAULT_SETTINGS = {
    "max_cameras_per_admin": 10,
    "max_cameras_per_supervisor": 5,
    "require_approval_for_new_users": False,
    "face_recognition_enabled": True,
    "show_bounding_boxes": True,
    "unknown_detection_enabled": True,
    "long_distance_detection_enabled": True,
    "min_face_size": 20,
    # Runtime recognition tuning. These values are consumed by face_pipeline.py.
    "detection_confidence_target": 0.35,
    "recognition_tolerance": 0.55,
    "long_range_tolerance": 0.60,
    "known_capture_min_confidence": 0.35,
    "unknown_capture_min_confidence": 0.45,
    "known_capture_interval_seconds": 5.0,
    "unknown_capture_interval_seconds": 12.0,
    # SMTP notifications (SuperAdmin only in UI/API).
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_use_tls": True,
    "email_from": "",
}

_SECRET_SETTING_FIELDS = {
    "smtp_password", "smtp_api_key", "redis_password", "database_password",
    "backup_password", "client_secret", "api_secret"
}


def _settings_file(company_id: Optional[str]) -> Path:
    return AUTH_DATA_DIR / (f"settings_{company_id}.json" if company_id else "settings.json")


def get_settings(company_id: Optional[str] = None) -> Dict[str, Any]:
    # System settings are the baseline. Company files behave as overrides so a
    # newly introduced recognition option immediately receives the global
    # default instead of disappearing from older tenant JSON files.
    settings = dict(DEFAULT_SETTINGS)
    global_settings = load_json(SETTINGS_FILE, {})
    if isinstance(global_settings, dict):
        settings.update(global_settings)
    if company_id:
        company_settings = load_json(_settings_file(company_id), {})
        if isinstance(company_settings, dict):
            settings.update(company_settings)
    return decrypt_fields(settings, _SECRET_SETTING_FIELDS)


def save_settings(settings: Dict[str, Any], company_id: Optional[str] = None):
    protected = encrypt_fields(settings, _SECRET_SETTING_FIELDS)
    atomic_write_json(_settings_file(company_id), protected)


def get_cameras() -> Dict[str, Any]:
    return load_json(CAMERAS_FILE, {})


def save_cameras(cameras: Dict[str, Any]):
    atomic_write_json(CAMERAS_FILE, cameras)


def get_companies() -> Dict[str, Any]:
    return load_json(COMPANIES_FILE, {})


def save_companies(companies: Dict[str, Any]):
    atomic_write_json(COMPANIES_FILE, companies)


def get_tokens() -> Dict[str, Any]:
    return load_json(TOKENS_FILE, {})


def save_tokens(tokens: Dict[str, Any]):
    atomic_write_json(TOKENS_FILE, tokens)


def get_password_resets() -> Dict[str, Any]:
    return load_json(RESET_TOKENS_FILE, {})


def save_password_resets(resets: Dict[str, Any]):
    atomic_write_json(RESET_TOKENS_FILE, resets)
