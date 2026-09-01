from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import parse_qs

from .license_dates import parse_license_datetime
from .security import verify_token
from .secret_store import fingerprint
from .storage import get_tokens
from .users import get_user

PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/bootstrap/superadmin",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/status",
    "/favicon.ico",
    "/",
}

# Query-string bearer tokens are intentionally limited to streaming endpoints,
# where native <video>/<img> style consumers cannot attach Authorization headers.
QUERY_TOKEN_PREFIXES = (
    "/api/collections/cameras/",
    "/api/get_stream_for_camera",
    "/api/webrtc/",
)

ROLE_MENUS = {
    "SuperAdmin": {
        "dashboard", "companies", "registration", "matching", "reports",
        "gallery", "events", "camera", "stream-viewer", "video",
        "users", "settings", "backup",
    },
    "Admin": {
        "dashboard", "registration", "matching", "reports", "gallery",
        "events", "camera", "stream-viewer", "video", "users",
        "settings", "backup",
    },
    "Supervisor": {
        "dashboard", "registration", "matching", "reports", "gallery",
        "events", "camera", "stream-viewer", "video",
    },
}

PATH_MENU_MAP = (
    ("/api/companies", "companies"),
    ("/api/users", "users"),
    ("/api/backup", "backup"),
    ("/api/registration", "registration"),
    ("/api/matching", "matching"),
    ("/api/events", "events"),
    ("/api/analytics", "dashboard"),
    ("/api/video", "video"),
    ("/api/collections", "camera"),
    ("/api/webrtc", "stream-viewer"),
)


def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    token_data = verify_token(token)
    if not token_data:
        return None
    user = get_user(token_data.get("username"))
    if not user or not user.get("is_active", True):
        return None
    return user


def is_admin_license_valid(user: Dict[str, Any]) -> bool:
    if user.get("role") != "Admin":
        return True
    end_str = user.get("license_end_date")
    if not end_str:
        return True
    end_dt = parse_license_datetime(end_str)
    return bool(end_dt and end_dt >= datetime.now(timezone.utc))


def _normalized_assigned_menus(user: Dict[str, Any]):
    raw = user.get("assigned_menus") or []
    aliases = {
        "cameras": "camera", "admin": "users", "backupmgmt": "backup",
        "analytics": "dashboard", "week-report": "reports", "month-report": "reports",
    }
    return {aliases.get(str(item), str(item)) for item in raw}


def check_path_permission(current_user: Dict[str, Any], path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True

    role = current_user.get("role")
    allowed = ROLE_MENUS.get(role, set())
    if not allowed:
        return False

    # Explicit hard boundaries first.
    if path.startswith("/api/companies") and role != "SuperAdmin":
        return False
    if path.startswith("/api/users") and role not in {"SuperAdmin", "Admin"}:
        return False
    if path.startswith("/api/backup") and role not in {"SuperAdmin", "Admin"}:
        return False

    required_menu = None
    for prefix, menu in PATH_MENU_MAP:
        if path.startswith(prefix):
            required_menu = menu
            break

    if required_menu and required_menu not in allowed:
        return False

    # assigned_menus is a deny/restrict list, never an elevation mechanism.
    assigned = _normalized_assigned_menus(current_user)
    if assigned and required_menu and required_menu not in assigned:
        return False

    return True


class RBACMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            token = self._extract_token(scope, allow_query=True)
            current_user = self._validate_active_token(token) if token else None
            if not current_user:
                await send({"type": "websocket.close", "code": 4001})
                return

            # Company-scoped recognition websocket: non-SuperAdmin users may only
            # connect to their own tenant channel.
            path = scope.get("path", "")
            if path.startswith("/ws/recognitions/"):
                requested_company = path.rsplit("/", 1)[-1]
                if current_user.get("role") != "SuperAdmin" and current_user.get("company_id") != requested_company:
                    await send({"type": "websocket.close", "code": 4003})
                    return

            scope["user"] = current_user
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if method == "OPTIONS" or path in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        allow_query = any(path.startswith(prefix) for prefix in QUERY_TOKEN_PREFIXES)
        token = self._extract_token(scope, allow_query=allow_query)
        current_user = self._validate_active_token(token) if token else None
        if not current_user:
            await self._send_json(send, 401, b'{"detail":"Not authenticated"}')
            return

        if current_user.get("role") == "Admin" and not is_admin_license_valid(current_user):
            await self._send_json(send, 403, b'{"detail":"License expired. Contact SuperAdmin."}')
            return

        if not check_path_permission(current_user, path, method):
            await self._send_json(send, 403, b'{"detail":"Not enough permissions"}')
            return

        scope["user"] = current_user
        await self.app(scope, receive, send)

    def _extract_token(self, scope, allow_query: bool = False) -> Optional[str]:
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode(errors="ignore")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        if allow_query:
            params = parse_qs(scope.get("query_string", b"").decode(errors="ignore"))
            values = params.get("token") or []
            if values:
                return values[0]
        return None

    def _validate_active_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        current_user = get_current_user_from_token(token)
        if not current_user:
            return None
        tokens = get_tokens()
        meta = tokens.get(fingerprint(token))
        if not meta:
            return None
        if meta.get("expires_at") and meta.get("expires_at") <= int(datetime.now(timezone.utc).timestamp()):
            tokens.pop(fingerprint(token), None)
            try:
                from .storage import save_tokens
                save_tokens(tokens)
            except Exception:
                pass
            return None
        return current_user

    async def _send_json(self, send, status: int, body: bytes):
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json; charset=utf-8"]],
        })
        await send({"type": "http.response.body", "body": body})
