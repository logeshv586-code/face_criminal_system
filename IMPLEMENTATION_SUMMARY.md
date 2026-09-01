# Face Capture Implementation - Current Workflow Summary

## ✅ Overview
This file documents the exact current face capture workflow in the repository.
It reflects the code present in `backend_face/save_face.py`, `backend_face/face_pipeline.py`, and `backend_face/main.py`.

## 1. Core Save Module (`backend_face/save_face.py`)
**What it does:**
- Saves face crops for known faces under `backend_face/captured_faces/known/<company>/<camera>/<label>/`
- Saves unknown faces under `backend_face/captured_faces/unknown/<company>/<camera>/`
- Ensures saved file and directory names are sanitized
- Applies confidence thresholds before writing files
- Uses a thread-safe rate-limiting cooldown map to avoid duplicate saves
- Writes save metadata to `captured_faces/capture_log.csv`
- Records attendance in SQLite for known faces
- Enhances and resizes small face crops before saving

**Key constants:**
- `DEFAULT_MIN_SAVE_INTERVAL_SECONDS = 8.0`
- `MIN_KNOWN_SAVE_CONFIDENCE = 0.35`
- `MIN_UNKNOWN_SAVE_CONFIDENCE = 0.45`

**Important functions:**
- `sanitize_label(label)`
- `ensure_dirs_for_label(label, camera_name, company_id)`
- `_append_log(row)`
- `_record_attendance_db(name, company_id, camera, confidence)`
- `save_face_image(...)`

**Behavior notes:**
- If no crop is provided, the module can derive a crop from `frame_bgr` + `bbox`
- Unknown faces use a different confidence gate
- Attendance is only recorded for non-unknown faces
- Data and capture directories are created automatically when needed

---

## 2. Stream Integration (`backend_face/face_pipeline.py`)
**What it does:**
- Evaluates each detected face for quality and save eligibility
- Uses a separate save interval for known and unknown faces
- Tracks the best available face per stream before saving
- Pads the face crop for a better saved image
- Resolves stream metadata from the streaming manager when available
- Dispatches face saves asynchronously in a background thread

**Current save timing:**
- `MIN_SAVE_INTERVAL = 5.0` seconds for known stream faces
- `UNKNOWN_MIN_SAVE_INTERVAL = 12.0` seconds for unknown faces

**Integration details:**
- Builds a `person_key` from name and track ID
- Passes `identity_key` to `save_face_image()` for per-identity cooldowns
- Calls `save_face_image(..., source="stream")`
- Keeps frame processing non-blocking

---

## 3. Manual Capture Endpoints (`backend_face/main.py`)
**Implemented endpoints:**

### `/capture_face_upload` (POST)
- Accepts multipart file upload via `UploadFile`
- Optional `label` and `confidence` form fields
- Decodes image bytes using OpenCV
- Calls `save_face_image(img, label, confidence, source="upload")`
- Returns JSON with `saved`, `path`, `label`, and `source`

### `/capture_face_b64` (POST)
- Accepts JSON payload with `image_b64`, `label`, and optional `confidence`
- Supports data URLs like `data:image/jpeg;base64,...`
- Decodes base64 and saves the image
- Returns JSON with `saved`, `path`, `label`, and `source = "upload_b64"`

**Endpoint behavior:**
- Returns HTTP 400 for invalid image content
- Logs errors and returns HTTP 500 for internal failures
- Uses FastAPI validation and request handling

---

## 4. Storage and Logging
**On-disk layout:**
- `backend_face/captured_faces/known/<company>/<camera>/<label>/`
- `backend_face/captured_faces/unknown/<company>/<camera>/`
- `backend_face/captured_faces/capture_log.csv`
- `backend_face/data/attendance.db`

**CSV log fields:**
- `filename`
- `label`
- `timestamp_iso`
- `saved_path`
- `confidence`
- `source`
- `company_id`

---

## 5. Run and Verify
### Verify Python syntax
```bash
cd d:\electron_frs\backend_face
python -m py_compile save_face.py face_pipeline.py main.py
```

### Start backend
```bash
cd d:\electron_frs\backend_face
python start_server.py
# or
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test endpoints
```bash
curl -X POST http://127.0.0.1:8000/capture_face_b64 \
  -H "Content-Type: application/json" \
  -d '{"image_b64":"data:image/jpeg;base64,/9j/4AAQ...", "label":"test"}'

curl -X POST http://127.0.0.1:8000/capture_face_upload \
  -F "file=@test_face.jpg" \
  -F "label=test" \
  -F "confidence=0.95"
```

---

## 6. Data Flow Summary
```
Detection Loop (face_pipeline.py)
    ↓
Face detection + quality gating
    ↓
Eligible face? → yes
    ↓
Async save thread spawned
    ↓
save_face_image()
      ├─ Sanitize label
      ├─ Check save cooldown
      ├─ Prepare/enhance crop
      ├─ Create directories
      ├─ Write image file
      ├─ Append CSV log row
      └─ Optionally record attendance
    ↓
Pipeline continues without blocking
```

---

## 7. Current Feature Set
| Feature | Status | Notes |
|---------|--------|-------|
| Stream face capture | ✓ | Async save from `face_pipeline.py` |
| Manual file upload | ✓ | `/capture_face_upload` |
| Manual base64 upload | ✓ | `/capture_face_b64` |
| Rate limiting | ✓ | Per-label cooldowns + stream gating |
| CSV logging | ✓ | Includes source and company metadata |
| Label sanitization | ✓ | Safe file and directory names |
| Auto directory creation | ✓ | Company/camera/label hierarchy |
| Attendance DB | ✓ | Known faces recorded in SQLite |
| Error handling | ✓ | Validation and logging |

---

## 8. Notes
- This summary is the current implementation reference.
- There are no additional companion docs such as `FACE_CAPTURE_IMPLEMENTATION.md` or `FRONTEND_CAPTURE_EXAMPLE.js` in this repository.
- The save module supports optional metadata fields and identity-based cooldowns.
- `save_face_image()` is the single point of truth for saving captured faces.

---

## 9. Files Included
| File | Purpose |
|------|---------|
| `backend_face/save_face.py` | Save logic, logging, and attendance recording |
| `backend_face/face_pipeline.py` | Stream face detection integration and async saves |
| `backend_face/main.py` | FastAPI manual capture endpoints |
| `IMPLEMENTATION_SUMMARY.md` | This document |

---

## ✅ Implementation Current Status
The current face capture workflow is implemented and documented in this summary.
All details above reflect the code as it exists in the repository today.

