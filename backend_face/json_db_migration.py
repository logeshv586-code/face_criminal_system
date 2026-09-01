"""JSON -> SQLite migration bridge for the current JSON-first deployment.

This module does not replace JSON storage. It creates a normalized, idempotent
SQLite snapshot so the application can move to DB-backed repositories later
without losing the shape/source of existing JSON records.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB = DATA_DIR / "frs_migration.db"

SKIP_NAMES = {"tokens.json", "password_resets.json"}
SKIP_PARTS = {"__pycache__", "backups", "captured_faces"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS migration_files (
            source_path TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            record_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS json_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            record_key TEXT NOT NULL,
            company_id TEXT,
            entity_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            UNIQUE(source_path, record_key, payload_sha256)
        );
        CREATE INDEX IF NOT EXISTS idx_json_records_company ON json_records(company_id);
        CREATE INDEX IF NOT EXISTS idx_json_records_entity ON json_records(entity_type);
        """
    )
    return con


def _company_id(value: Any, fallback: Optional[str] = None) -> Optional[str]:
    if isinstance(value, dict):
        cid = value.get("company_id") or value.get("companyId")
        if cid:
            return str(cid)
    return fallback


def _flatten_records(data: Any, source: Path) -> List[Tuple[str, Optional[str], str, Dict[str, Any]]]:
    entity = source.stem
    rows: List[Tuple[str, Optional[str], str, Dict[str, Any]]] = []

    if isinstance(data, dict):
        for key, value in data.items():
            payload = value if isinstance(value, dict) else {"value": value}
            cid = _company_id(payload)
            rows.append((str(key), cid, entity, payload))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            payload = value if isinstance(value, dict) else {"value": value}
            record_key = str(payload.get("id") or payload.get("username") or payload.get("name") or index)
            rows.append((record_key, _company_id(payload), entity, payload))
    else:
        rows.append(("value", None, entity, {"value": data}))
    return rows


def discover_json_files(root: Path = DATA_DIR) -> List[Path]:
    files = []
    if not root.exists():
        return files
    for path in root.rglob("*.json"):
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def migrate_json_to_sqlite(root: Path = DATA_DIR, db_path: Path = DEFAULT_DB, force: bool = False) -> Dict[str, Any]:
    files = discover_json_files(root)
    con = _connect(db_path)
    imported_files = 0
    skipped_files = 0
    records_written = 0
    errors: List[str] = []

    try:
        for path in files:
            rel = path.relative_to(BASE_DIR).as_posix()
            try:
                digest = _sha256(path)
                previous = con.execute("SELECT sha256 FROM migration_files WHERE source_path=?", (rel,)).fetchone()
                if previous and previous[0] == digest and not force:
                    skipped_files += 1
                    continue

                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                rows = _flatten_records(data, path)
                now = _utc_now()

                # Replace the current snapshot for this file while preserving the
                # migration_file audit row and avoiding duplicates on re-import.
                con.execute("DELETE FROM json_records WHERE source_path=?", (rel,))
                for record_key, company_id, entity_type, payload in rows:
                    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
                    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
                    con.execute(
                        """INSERT OR IGNORE INTO json_records
                           (source_path, record_key, company_id, entity_type, payload_json, payload_sha256, imported_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (rel, record_key, company_id, entity_type, payload_json, payload_hash, now),
                    )
                    records_written += 1
                con.execute(
                    """INSERT INTO migration_files(source_path, sha256, imported_at, record_count)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(source_path) DO UPDATE SET
                         sha256=excluded.sha256, imported_at=excluded.imported_at, record_count=excluded.record_count""",
                    (rel, digest, now, len(rows)),
                )
                con.commit()
                imported_files += 1
            except Exception as exc:
                con.rollback()
                errors.append(f"{rel}: {exc}")
    finally:
        con.close()

    return {
        "database": str(db_path),
        "json_root": str(root),
        "files_found": len(files),
        "files_imported": imported_files,
        "files_unchanged": skipped_files,
        "records_written": records_written,
        "errors": errors,
    }


def migration_status(db_path: Path = DEFAULT_DB) -> Dict[str, Any]:
    if not db_path.exists():
        return {"database": str(db_path), "exists": False, "files": 0, "records": 0}
    con = _connect(db_path)
    try:
        files = con.execute("SELECT COUNT(*) FROM migration_files").fetchone()[0]
        records = con.execute("SELECT COUNT(*) FROM json_records").fetchone()[0]
        last = con.execute("SELECT MAX(imported_at) FROM migration_files").fetchone()[0]
        return {"database": str(db_path), "exists": True, "files": files, "records": records, "last_imported_at": last}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(migrate_json_to_sqlite(), indent=2))
