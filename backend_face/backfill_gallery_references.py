"""Synchronize existing augmented registration references into the live tenant gallery.

The project does not train a new model for each identity. Registration creates a reference
set (up to 50 images) and live recognition embeds/matches those gallery images. This helper
backfills older registrations that may only have a single gallery reference.
"""
from __future__ import annotations

from pathlib import Path
import shutil
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GALLERY_DIR = DATA_DIR / "gallery"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
RESERVED = {"auth", "camera_management", "gallery", "logs", "temp_bulk"}


def backfill_gallery_references(company_id: Optional[str] = None, max_references: int = 50) -> Dict[str, int]:
    max_references = max(1, min(int(max_references), 50))
    companies = [DATA_DIR / company_id] if company_id else [
        p for p in DATA_DIR.iterdir() if p.is_dir() and p.name not in RESERVED
    ] if DATA_DIR.exists() else []

    stats = {"companies": 0, "people": 0, "images_copied": 0, "skipped": 0}
    touched_companies = set()
    for company_dir in companies:
        if not company_dir.exists() or not company_dir.is_dir():
            continue
        cid = company_dir.name
        people = [p for p in company_dir.iterdir() if p.is_dir()]
        for person_dir in people:
            images = sorted(
                [p for p in person_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
                key=lambda p: (0, int(p.stem)) if p.stem.isdigit() else (1, p.name.lower()),
            )[:max_references]
            if not images:
                stats["skipped"] += 1
                continue
            gallery_person = GALLERY_DIR / cid / person_dir.name
            gallery_person.mkdir(parents=True, exist_ok=True)
            copied = 0
            for idx, source in enumerate(images, 1):
                target = gallery_person / f"{idx}.jpg"
                if source.resolve() == target.resolve():
                    continue
                # Preserve encoded bytes when source is already JPG; OpenCV can read PNG too,
                # but the target extension should match content, so keep the source suffix when needed.
                target = gallery_person / (f"{idx}{source.suffix.lower()}" if source.suffix.lower() not in {".jpg", ".jpeg"} else f"{idx}.jpg")
                if not target.exists() or source.stat().st_mtime_ns != target.stat().st_mtime_ns or source.stat().st_size != target.stat().st_size:
                    shutil.copy2(source, target)
                    copied += 1
            stats["people"] += 1
            stats["images_copied"] += copied
            touched_companies.add(cid)

    stats["companies"] = len(touched_companies)
    # Force safe embedding cache rebuild for modified tenants.
    for cid in touched_companies:
        cache = DATA_DIR / f"embeddings_cache_{cid}.npz"
        cache.unlink(missing_ok=True)
    return stats


if __name__ == "__main__":
    print(backfill_gallery_references())
