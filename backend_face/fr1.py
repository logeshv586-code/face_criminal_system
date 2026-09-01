# fr1.py
# -*- coding: utf-8 -*-
"""Reference-gallery loading and conservative standalone face matching.

The live criminal-identification path uses :mod:`face_pipeline`.  This module is
kept as the gallery/cache provider and as a small standalone diagnostic path.
The gallery loader deliberately favours a small set of coherent, high-quality
references over dozens of synthetic variants: ambiguous identities are safer as
Unknown than as a wrong named match.
"""

from __future__ import annotations

import glob
import os
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import face_recognition
import numpy as np

try:
    from insightface.app import FaceAnalysis
except Exception as exc:  # pragma: no cover - runtime dependency
    raise ImportError("insightface is required. Install with: pip install insightface") from exc

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CAMERA_INDEX = 0

# Standalone diagnostic path.  Live tuning is enforced in face_pipeline.py.
TOLERANCE = 0.46
SECOND_PERSON_MARGIN = 0.06
FRAME_DISPLAY_SCALE = 1.0
INSIGHT_CTX = 0
INSIGHT_DET_SIZE = (1280, 1280)
MIN_FACE_PX = 20
MIN_IDENTITY_FACE_PX = 56

# Gallery hardening.  Registration historically generated 50 synthetic copies
# from one photo.  Loading all of them makes one weak sample look like 50 votes.
# We instead retain a compact, coherent reference set.
MAX_REFERENCES_PER_PERSON = 12
MIN_REFERENCES_PER_PERSON = 3
MIN_REFERENCE_SIDE = 80
MIN_REFERENCE_SHARPNESS = 18.0
MIN_REFERENCE_MEAN = 28.0
MAX_REFERENCE_MEAN = 230.0
WITHIN_PERSON_MAX_DISTANCE = 0.42
CROSS_PERSON_COLLISION_DISTANCE = 0.39
CACHE_POLICY_VERSION = 2

IGNORE_FOLDERS = {
    "gallery", "auth", "camera_management", "temp_bulk", "__pycache__", ".ipynb_checkpoints"
}


def _load_npz_cache(cache_path: str) -> dict:
    cache: Dict[str, dict] = {}
    if not os.path.exists(cache_path):
        return cache
    try:
        with np.load(cache_path, allow_pickle=False) as data:
            version_arr = data.get("policy_version", np.array([0], dtype=np.int64))
            version = int(np.asarray(version_arr).reshape(-1)[0]) if np.asarray(version_arr).size else 0
            if version != CACHE_POLICY_VERSION:
                return {}
            paths = data.get("paths", np.array([], dtype=str))
            mtimes = data.get("mtimes", np.array([], dtype=float))
            names = data.get("names", np.array([], dtype=str))
            encodings = data.get("encodings", np.empty((0, 128), dtype=np.float64))
            for path, mtime, name, enc in zip(paths.tolist(), mtimes.tolist(), names.tolist(), encodings):
                cache.setdefault(path, {"mtime": float(mtime), "name": str(name), "encodings": []})
                cache[path]["encodings"].append(np.asarray(enc, dtype=np.float64))
    except Exception as exc:
        print(f"[WARN] Safe cache load failed, rebuilding: {exc}")
        return {}
    return cache


def _save_npz_cache(cache_path: str, cache: dict) -> None:
    paths: List[str] = []
    mtimes: List[float] = []
    names: List[str] = []
    encodings: List[np.ndarray] = []
    for path, item in cache.items():
        for enc in item.get("encodings", []):
            arr = np.asarray(enc, dtype=np.float64).reshape(-1)
            if arr.size != 128:
                continue
            paths.append(path)
            mtimes.append(float(item.get("mtime", 0)))
            names.append(str(item.get("name", "")))
            encodings.append(arr)
    arr_enc = np.vstack(encodings) if encodings else np.empty((0, 128), dtype=np.float64)
    tmp = cache_path + ".tmp.npz"
    np.savez_compressed(
        tmp,
        paths=np.asarray(paths, dtype=str),
        mtimes=np.asarray(mtimes, dtype=np.float64),
        names=np.asarray(names, dtype=str),
        encodings=arr_enc,
        policy_version=np.asarray([CACHE_POLICY_VERSION], dtype=np.int64),
    )
    os.replace(tmp, cache_path)


def _reference_quality_ok(image_bgr: np.ndarray) -> bool:
    """Reject tiny, extremely dark/bright or information-poor references."""
    if image_bgr is None or image_bgr.size == 0:
        return False
    h, w = image_bgr.shape[:2]
    if min(h, w) < MIN_REFERENCE_SIDE:
        return False
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    mean = float(gray.mean())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return bool(
        MIN_REFERENCE_MEAN <= mean <= MAX_REFERENCE_MEAN
        and sharpness >= MIN_REFERENCE_SHARPNESS
    )


def _encode_reference(img_path: str) -> Optional[np.ndarray]:
    probe = cv2.imread(img_path)
    if not _reference_quality_ok(probe):
        return None

    rgb = cv2.cvtColor(probe, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        locations = face_recognition.face_locations(rgb, model="cnn")
    # Enrollment evidence must contain exactly one face.  A background face in
    # a registered photo must never become a template for the named identity.
    if len(locations) != 1:
        return None

    top, right, bottom, left = locations[0]
    if min(right - left, bottom - top) < MIN_REFERENCE_SIDE // 2:
        return None

    encs = face_recognition.face_encodings(
        rgb,
        known_face_locations=locations,
        num_jitters=2,
        model="large",
    )
    if len(encs) != 1:
        return None
    return np.asarray(encs[0], dtype=np.float64)


def _medoid(encodings: Sequence[np.ndarray]) -> np.ndarray:
    if len(encodings) == 1:
        return np.asarray(encodings[0], dtype=np.float64)
    mat = np.vstack(encodings)
    # Euclidean distances match face_recognition.face_distance.
    dist = np.linalg.norm(mat[:, None, :] - mat[None, :, :], axis=2)
    return mat[int(np.argmin(dist.mean(axis=1)))]


def _coherent_subset(items: Sequence[Tuple[str, np.ndarray]]) -> List[Tuple[str, np.ndarray]]:
    if not items:
        return []
    centre = _medoid([enc for _, enc in items])
    ranked: List[Tuple[float, str, np.ndarray]] = []
    for path, enc in items:
        distance = float(np.linalg.norm(np.asarray(enc) - centre))
        if distance <= WITHIN_PERSON_MAX_DISTANCE:
            ranked.append((distance, path, enc))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [(path, enc) for _, path, enc in ranked[:MAX_REFERENCES_PER_PERSON]]


def _find_colliding_people(grouped: Dict[str, List[Tuple[str, np.ndarray]]]) -> set[str]:
    """Return identities whose gallery centres are dangerously close.

    We fail closed and remove both identities from live known matching.  An
    operator must re-enrol cleaner references before either can be named.
    """
    centres = {
        person: _medoid([enc for _, enc in refs])
        for person, refs in grouped.items()
        if refs
    }
    people = sorted(centres)
    collisions: set[str] = set()
    for i, first in enumerate(people):
        for second in people[i + 1:]:
            distance = float(np.linalg.norm(centres[first] - centres[second]))
            if distance < CROSS_PERSON_COLLISION_DISTANCE:
                collisions.add(first)
                collisions.add(second)
                print(
                    f"[SAFETY] Gallery collision {first!r} <-> {second!r} "
                    f"(distance={distance:.3f}); both withheld from live identity matching"
                )
    return collisions


def load_known_faces(
    data_dir: str,
    company_id: Optional[str] = None,
) -> Tuple[List[np.ndarray], List[str]]:
    """Load a conservative reference set from ``data/gallery/<tenant>``.

    Safety rules:
    * reject low-information/small or multi-face references;
    * cap references so synthetic augmentation cannot create artificial votes;
    * require multiple coherent templates per identity;
    * withhold cross-person gallery collisions instead of guessing.
    """
    if not os.path.isdir(data_dir):
        raise ValueError(f"Data directory does not exist: {data_dir}")

    company = str(company_id or "default")
    gallery_dir = os.path.join(data_dir, "gallery", company)
    if not os.path.isdir(gallery_dir):
        print(f"[WARN] Gallery not found for company '{company}': {gallery_dir}")
        return [], []

    cache_path = os.path.join(data_dir, f"embeddings_cache_{company}.npz")
    cache = _load_npz_cache(cache_path)
    current_files: set[str] = set()
    grouped: Dict[str, List[Tuple[str, np.ndarray]]] = defaultdict(list)
    new_computations = 0

    person_dirs = [
        d for d in sorted(os.listdir(gallery_dir))
        if os.path.isdir(os.path.join(gallery_dir, d)) and d not in IGNORE_FOLDERS
    ]
    print(f"[INFO] {len(person_dirs)} person(s) in {gallery_dir}")

    for person in person_dirs:
        files = sorted(
            f for f in glob.glob(os.path.join(gallery_dir, person, "*"))
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
        )
        # Scan a bounded number.  Old galleries often contain 50 variants from
        # one source; quality/cohesion filtering happens below.
        for img_path in files[:50]:
            current_files.add(img_path)
            try:
                mtime = os.path.getmtime(img_path)
                item = cache.get(img_path)
                enc: Optional[np.ndarray] = None
                if item and abs(float(item.get("mtime", 0)) - float(mtime)) < 0.000001:
                    cached = item.get("encodings", [])
                    if cached:
                        enc = np.asarray(cached[0], dtype=np.float64)
                else:
                    enc = _encode_reference(img_path)
                    if enc is None:
                        cache.pop(img_path, None)
                        continue
                    cache[img_path] = {"mtime": mtime, "encodings": [enc], "name": person}
                    new_computations += 1
                if enc is not None and enc.size == 128:
                    grouped[person].append((img_path, enc))
            except Exception as exc:
                print(f"[WARN] Reference skipped {img_path}: {exc}")
                cache.pop(img_path, None)

    # Drop stale cached references.
    for stale_path in [path for path in cache if path not in current_files]:
        cache.pop(stale_path, None)

    coherent: Dict[str, List[Tuple[str, np.ndarray]]] = {}
    for person, refs in grouped.items():
        filtered = _coherent_subset(refs)
        if len(filtered) < MIN_REFERENCES_PER_PERSON:
            print(
                f"[SAFETY] {person!r} has only {len(filtered)} coherent reference(s); "
                "identity withheld until re-enrolment provides multiple clear samples"
            )
            continue
        coherent[person] = filtered

    collisions = _find_colliding_people(coherent)
    known_encodings: List[np.ndarray] = []
    known_names: List[str] = []
    for person in sorted(coherent):
        if person in collisions:
            continue
        for _, enc in coherent[person]:
            known_encodings.append(np.asarray(enc, dtype=np.float64))
            known_names.append(person)

    try:
        _save_npz_cache(cache_path, cache)
    except Exception as exc:
        print(f"[WARN] Could not save safe cache: {exc}")

    legacy = os.path.join(data_dir, f"embeddings_cache_{company}.pkl")
    if os.path.exists(legacy):
        try:
            os.remove(legacy)
        except OSError:
            pass

    print(
        f"[INFO] Loaded {len(known_encodings)} safe reference embeddings "
        f"for {len(set(known_names))} identities | New computations: {new_computations}"
    )
    return known_encodings, known_names


def prepare_insightface(
    ctx: int = INSIGHT_CTX,
    det_size: Tuple[int, int] = INSIGHT_DET_SIZE,
) -> FaceAnalysis:
    app = FaceAnalysis(allowed_modules=["detection"])
    app.prepare(ctx_id=ctx, det_size=det_size)
    print(f"[INFO] InsightFace ready | ctx={ctx} | det_size={det_size}")
    return app


def _conservative_name(
    encoding: np.ndarray,
    known_encodings: Sequence[np.ndarray],
    known_names: Sequence[str],
) -> Tuple[str, Optional[float]]:
    if not known_encodings:
        return "Unknown", None
    distances = face_recognition.face_distance(list(known_encodings), encoding)
    per_person: Dict[str, float] = {}
    for name, dist in zip(known_names, distances):
        per_person[name] = min(per_person.get(name, 999.0), float(dist))
    ranked = sorted(per_person.items(), key=lambda item: item[1])
    if not ranked or ranked[0][1] > TOLERANCE:
        return "Unknown", ranked[0][1] if ranked else None
    second = ranked[1][1] if len(ranked) > 1 else 1.0
    if second - ranked[0][1] < SECOND_PERSON_MARGIN:
        return "Unknown", ranked[0][1]
    return ranked[0][0], ranked[0][1]


def recognize_frame_insight(
    frame_bgr: np.ndarray,
    app: FaceAnalysis,
    known_encodings: List[np.ndarray],
    known_names: List[str],
) -> np.ndarray:
    """Standalone diagnostic renderer; uncertain/small faces remain Unknown."""
    if frame_bgr is None:
        return frame_bgr
    h, w = frame_bgr.shape[:2]
    for face in app.get(frame_bgr):
        bbox = getattr(face, "bbox", None)
        if bbox is None or len(bbox) < 4:
            continue
        x1, y1, x2, y2 = map(int, bbox[:4])
        x1, x2 = max(0, x1), min(w - 1, x2)
        y1, y2 = max(0, y1), min(h - 1, y2)
        fw, fh = x2 - x1, y2 - y1
        if fw < MIN_FACE_PX or fh < MIN_FACE_PX:
            continue

        name = "Unknown"
        distance: Optional[float] = None
        if min(fw, fh) >= MIN_IDENTITY_FACE_PX:
            crop = frame_bgr[y1:y2, x1:x2]
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            ch, cw = rgb.shape[:2]
            encs = face_recognition.face_encodings(
                rgb,
                known_face_locations=[(0, cw - 1, ch - 1, 0)],
                num_jitters=1,
                model="large",
            )
            if encs:
                name, distance = _conservative_name(encs[0], known_encodings, known_names)

        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)
        label = name + (f" | d={distance:.2f}" if distance is not None else "")
        cv2.putText(
            frame_bgr,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return frame_bgr


def main() -> None:  # pragma: no cover - manual diagnostic
    known_encodings, known_names = load_known_faces(DATA_DIR)
    app = prepare_insightface()
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera {CAMERA_INDEX}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            annotated = recognize_frame_insight(frame, app, known_encodings, known_names)
            cv2.imshow("Conservative Face Recognition | Q to quit", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
