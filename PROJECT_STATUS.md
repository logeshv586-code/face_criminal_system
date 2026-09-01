# Face Recognition System — Project Status

**Repository:** `electron_frs`  
**Document date:** 31 August 2026  
**Purpose:** A code-based record of the system that has been implemented so far. This is a current-state document, not a deployment certificate.

## 1. Product overview

The project is a desktop face-recognition and camera-monitoring system. It combines an Electron/React desktop application with a FastAPI backend. The application is designed to manage users and companies, register people, connect RTSP cameras, process live or uploaded video, recognize faces, save face captures, record attendance, and review events and analytics.

The backend is multi-tenant: company IDs are carried through users, cameras, galleries, events, face captures, and WebSocket recognition updates.

## 2. Implemented architecture

```text
Electron desktop shell
        |
React user interface (port 3000 during development)
        |
HTTP / WebSocket API
        |
FastAPI unified backend (default launcher port: 8005)
        |
 +------+-------+---------+----------+----------+---------+
 | Auth | Camera| Register| Matching | Video    | Backup  |
 +------+-------+---------+----------+----------+---------+
        |
Face pipeline / RTSP streams / local JSON files / SQLite / image storage
```

### Main backend entry points

- `backend_face/main.py` creates the unified FastAPI application and mounts the service modules.
- `backend_face/start_server.py` starts the application on `0.0.0.0:8005`.
- `backend_face/face_pipeline.py` processes camera frames, performs recognition and manages stream-side face captures.
- `backend_face/save_face.py` is the shared implementation for writing known and unknown face captures and attendance data.

### Desktop client

- `frontend/main.js` is the Electron main process.
- `frontend/preload.js` exposes a controlled IPC API to the renderer.
- `frontend/src/App.js` controls authentication, backend discovery, and the active application view.
- React components are grouped by dashboard, camera, authentication, administration, and reporting concerns.

## 3. Completed functional areas

| Area | Implemented capabilities |
|---|---|
| Authentication and access control | Login/session handling, JWT-related storage, role-based middleware, user management, company management, per-company settings and camera assignments. |
| Multi-tenancy | Company-aware user, camera, gallery, capture and WebSocket recognition handling. Recent work strengthens company deletion cleanup and isolates duplicate-camera validation by company. |
| License controls | Background license checker and camera-count enforcement based on an administrator's `max_cameras_limit`. Automated tests exist for RBAC/license camera limits. |
| Camera management | Camera and collection CRUD, camera validation, RTSP stream lifecycle, activation/deactivation, persistent-stream startup, frame retrieval, recordings, and bounding-box settings. |
| Live recognition | RTSP stream processing, face detection/recognition pipeline, rendered bounding boxes, per-company real-time recognition WebSocket endpoint. |
| Registration and gallery | Single and bulk face registration, gallery browsing, person metadata, status updates, person deletion and statistics. |
| Face matching | One-to-one and one-to-many matching services plus gallery statistics and cache reload. |
| Face capture and attendance | Known/unknown face saving, confidence gates, per-identity cooldowns, capture CSV logging, and known-person attendance in SQLite. Manual file and Base64 capture endpoints are also available. |
| Events and analytics | Filterable face-event APIs, event deletion, overview statistics, trends, confidence distribution, activity by hour/camera, frequency and person analytics. |
| Video processing | Upload, asynchronous processing, task status/result retrieval, cancellation, format discovery, and video deletion. |
| Backup and retention | Redis-oriented backup service, scheduled monthly backups when available, backup listing/download/preview/delete, full or tenant restore, audit logs, and retention enforcement. |
| Operations | Startup attempts to restore active camera streams, start the license checker, backup scheduler and image-retention worker; failures are logged so on-demand features can still operate. |

## 4. User interface modules

The application currently includes these views:

- Dashboard and face-recognition analytics
- Face gallery and person cards
- Face event browser and occurrence search
- Single/bulk registration
- One-to-one and one-to-many face matching
- Camera manager, stream viewer, recordings, collection management and multiple player implementations
- Video-processing workspace
- User management, settings and backup dashboard
- Holiday calendar and weekly/monthly attendance reports

State is managed with Zustand stores for authentication, cameras, and archive-related data. The app checks candidate backend URLs at startup and lets an operator enter a backend IP manually when automatic detection fails.

## 5. API surface (grouped)

The unified API exposes the following major route groups. The interactive API schema is available at `/docs` when the backend is running.

| Prefix / endpoint | Responsibility |
|---|---|
| `/api` | Authentication, users, companies, legacy camera assignments, settings and system status. |
| `/api/registration` | Face registration, gallery, metadata and registration statistics. |
| `/api/collections` | Enhanced camera management, collections, validation, streaming and recordings. |
| `/api/events` | Event listing/filtering, face-event matching and deletion. |
| `/api/matching` | One-to-one and one-to-many matching plus gallery cache/statistics. |
| `/api/video` | Video upload and asynchronous processing task APIs. |
| `/api/webrtc` | WebRTC signaling and WebSocket compatibility routes. |
| `/api/backup` | Backup, restore, preview, retention and audit-log APIs. |
| `/api/analytics/*` | Detection, person, confidence, camera and activity analytics. |
| `/capture_face_upload`, `/capture_face_b64` | Manual face-capture inputs. |
| `/ws/recognitions/{company_id}` | Real-time company-scoped recognition updates. |

## 6. Data and storage currently used

| Location | Contents |
|---|---|
| `backend_face/data/auth/` | Local JSON-backed users, companies, tokens, settings, camera assignments and audit information. |
| `backend_face/data/camera_management/` | Camera and collection records. |
| `backend_face/data/gallery/<company>/<person>/` | Registered reference images. |
| `backend_face/captured_faces/known/<company>/<camera>/<person>/` | Captures for recognized people. |
| `backend_face/captured_faces/unknown/<company>/<camera>/` | Captures for unknown faces. |
| `backend_face/captured_faces/capture_log.csv` | Face-capture audit log. |
| `backend_face/data/attendance.db` | SQLite attendance records for known faces. |
| `backend_face/backups/` and backup log data | Local backup artifacts and related logs. |

Model and recognition assets included in the repository include YOLO face-detection weights, a Haar cascade, and face-recognition embedding caches.

## 7. Face-capture workflow

1. A stream frame reaches `face_pipeline.py`.
2. The pipeline detects/identifies a face, applies quality and confidence checks, and selects eligible captures.
3. A background task calls `save_face_image()` in `save_face.py` so stream processing is not blocked.
4. The save module sanitizes labels, applies per-identity cooldowns, enhances/resizes crops, creates the required directory, writes the image and appends a CSV record.
5. For known people, it also records attendance in SQLite.

Known and unknown faces use separate confidence gates and save intervals. The current detailed reference is `IMPLEMENTATION_SUMMARY.md`.

## 8. Technology stack

| Layer | Technologies |
|---|---|
| Desktop/frontend | Electron 27, React 18, React Router, Zustand, Axios, Chart.js/Recharts, Tailwind/PostCSS. |
| API/backend | Python, FastAPI, Uvicorn, Pydantic, WebSockets and CORS middleware. |
| Computer vision | OpenCV, `face-recognition`, InsightFace, ONNX Runtime, Ultralytics/YOLO, NumPy, Pillow and SciPy/scikit-learn. |
| Storage/integration | JSON files, SQLite, Redis-backed backup support, CSV logs and filesystem image/video storage. |
| Packaging | `electron-builder` creates a Windows NSIS installer. |

Python dependencies are defined in `requirements.txt`; desktop dependencies and scripts are defined in `frontend/package.json`.

## 9. How to run

### Backend

```powershell
cd backend_face
python -m pip install -r ..\requirements.txt
python start_server.py
```

The standard launcher uses port **8005**. The backend must be running before the desktop app can connect.

### Frontend / Electron

```powershell
cd frontend
npm install
npm run dev
```

Other available commands are `npm run react-dev`, `npm run build`, `npm start`, and `npm run electron-pack`.

## 10. Work currently present in the working tree

The repository contains uncommitted implementation and runtime-data changes. The notable code changes currently visible are:

- Deleting the final Admin in a company can cascade to company deletion.
- Company cleanup now also clears company tokens, embedding caches, camera records, collections and active camera streams.
- Camera duplicate-IP validation now allows identical camera IPs for different companies.
- Camera creation applies company-specific license camera limits.
- Event bulk deletion was hardened for Windows/normalized paths and date filtering.
- Registration, the face pipeline and capture saving have active changes; the detailed face-capture document has also been updated.

Generated files and runtime data are also modified (Python caches, token data, camera data, attendance database, capture logs and captured images). These should be reviewed separately before committing or packaging.

## 11. Verification status and recommended next work

Verification performed for this documentation update:

- Python syntax compilation passed for the unified entry point and currently modified backend modules.
- `npm run build` completed successfully in `frontend`.
- The backend test suite did not collect because the active Python interpreter is missing `insightface` (`ModuleNotFoundError`), although it is listed in `requirements.txt`.

Implemented features should also be tested end to end with real credentials, cameras and a target deployment environment. In particular:

1. Run the backend tests in `backend_face/tests/`, especially the RBAC and license-limit tests.
2. Test company deletion against a disposable tenant; confirm active streams stop and no other company's data is removed.
3. Test camera creation for two tenants sharing the same IP, and validate the per-company camera limit.
4. Run registration, live recognition, capture saving and attendance recording against a real RTSP camera.
5. Validate backup/restore with Redis available and confirm retention behavior.
6. Build and smoke-test the packaged Electron installer on a clean Windows machine.
7. Add an environment-specific configuration file and remove or ignore runtime data before a production release.

## 12. Important repository references

| File / directory | Purpose |
|---|---|
| `backend_face/main.py` | Unified API composition and top-level endpoints. |
| `backend_face/auth/` | Authentication, users, companies, licensing and authorization middleware. |
| `backend_face/camera_management/` | Enhanced camera/collection/recording/streaming services. |
| `backend_face/registration/reg.py` | Face registration and metadata service. |
| `backend_face/matching/one.py` | Face matching service. |
| `backend_face/event/event_api.py` | Event APIs. |
| `backend_face/backup/` | Backup service, scheduler and routes. |
| `backend_face/face_pipeline.py`, `backend_face/save_face.py` | Live recognition capture pipeline and image persistence. |
| `frontend/src/App.js` | Frontend view selection and backend connection handling. |
| `frontend/src/components/` | Product UI modules. |
| `IMPLEMENTATION_SUMMARY.md` | Detailed current face-capture implementation reference. |
