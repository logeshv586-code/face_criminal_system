from fastapi import APIRouter, HTTPException, Request
from json_db_migration import migrate_json_to_sqlite, migration_status
from backfill_gallery_references import backfill_gallery_references

router = APIRouter(prefix="/api/migration", tags=["Migration"])


def _require_superadmin(request: Request):
    user = request.scope.get("user") or {}
    if user.get("role") != "SuperAdmin":
        raise HTTPException(status_code=403, detail="SuperAdmin access required")


@router.get("/status")
async def get_status(request: Request):
    _require_superadmin(request)
    return migration_status()


@router.post("/json-to-sqlite")
async def run_migration(request: Request, force: bool = False):
    _require_superadmin(request)
    return migrate_json_to_sqlite(force=force)


@router.post("/backfill-gallery")
async def backfill_gallery(request: Request, company_id: str | None = None, max_references: int = 50):
    """Copy existing augmented registration images into the live tenant gallery (max 50/person)."""
    _require_superadmin(request)
    return backfill_gallery_references(company_id=company_id, max_references=max_references)
