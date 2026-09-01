# Face Recognition System - Final SIP / Implementation Handover

**Product:** Electron Face Recognition System - Criminal Identification  
**Source:** `electron_frs_source.zip` supplied through Google Drive  
**Document date:** 31 August 2026  
**Purpose:** Final implementation/handover record for the updated source package. This is a source-code handover for user-side testing, not a production certification.

## 1. Target recognition design

This project uses **reference-image matching rather than per-person model retraining**.

Implemented flow:

1. Register a person with a source/reference photograph.
2. Registration creates a reference set of up to **50 augmented images** using controlled geometric and brightness variation.
3. The references are synchronized to the tenant gallery under `backend_face/data/gallery/<company>/<person>/`.
4. `fr1.py` loads a maximum of 50 deterministic references for each identity and builds face embeddings.
5. Live RTSP frames enter `face_pipeline.py` and are compared against those gallery embeddings.
6. The stream manager keeps a short frame buffer. When a face is eligible for saving, `get_best_frame_for_bbox()` selects the sharper buffered crop rather than always saving the latest frame.
7. Known and unknown face captures are stored independently with confidence/cooldown controls.
8. Known detections can also be written to SQLite attendance/event storage where the existing application requires it.

Adding a new identity therefore updates the reference gallery/cache; it does **not** require training a new recognition model for every identity.

## 2. Existing registrations / 50-reference backfill

`backend_face/backfill_gallery_references.py` supports older registrations that already contain augmented folders outside the live gallery. It copies up to 50 references into the live company gallery and invalidates that tenant's safe embedding cache so it rebuilds from the updated images.

The startup setting `FRS_AUTO_BACKFILL_GALLERY=1` runs this synchronization automatically. A SuperAdmin can also invoke the migration API manually.

## 3. Safer recognition cache

Live embedding cache handling uses NumPy `.npz` files with `allow_pickle=False`. Old company-specific pickle caches are invalidated during the updated workflow. This removes the need to deserialize executable Python pickle data for the normal recognition cache path.

## 4. JSON-first now, DB-ready later

The current product keeps JSON as its operational configuration/data format where the original application expects JSON.

`backend_face/json_db_migration.py` adds an idempotent JSON -> SQLite bridge:

- discovers supported JSON files under `backend_face/data/`;
- calculates a SHA-256 checksum per source file;
- records each source and normalized JSON record in `data/frs_migration.db`;
- records company IDs when present;
- skips unchanged JSON files on later startup runs;
- replaces only the changed source snapshot when JSON changes;
- excludes transient token/reset files from DB snapshots.

With `FRS_AUTO_MIGRATE_JSON=1`, the snapshot runs automatically on startup. This allows the project to transition later to DB-backed repositories without losing the source JSON structure or requiring a manual one-time reconstruction.

> Important: the migration bridge creates a DB-ready normalized snapshot; the current application services still intentionally write to their existing JSON/filesystem repositories unless they already use SQLite.

## 5. JSON secret hardening

`backend_face/security_migration.py` runs before the automatic JSON -> SQLite snapshot. It protects legacy JSON data in place:

- camera `rtsp_url` values are encrypted at rest;
- SMTP/API/database/backup secret fields in settings are encrypted at rest;
- old raw-JWT token keys are revoked rather than carried forward;
- obsolete legacy JWT secret files are removed.

Encryption uses Fernet through `backend_face/auth/secret_store.py`. Production deployments should provide a stable `FRS_DATA_ENCRYPTION_KEY`; otherwise a machine-local key is created with best-effort restricted filesystem permissions.

## 6. Authentication and session security

Updated authentication includes:

- configurable JWT signing secret instead of a fixed code secret;
- JWT `iat`, `exp` and `jti` claims;
- configurable access-token lifetime;
- active-session token fingerprints stored instead of raw bearer tokens;
- login attempt throttling/window protection;
- one-time random password-reset tokens with expiry;
- reset-token hashes rather than plaintext reset tokens in normal storage;
- active sessions revoked after password reset;
- password hashes removed from user API responses;
- frontend bearer token stored in `sessionStorage` rather than persistent `localStorage`;
- development reset-token exposure disabled by default.

## 7. Multi-tenant and RBAC rules

Role baseline implemented in frontend and backend middleware:

| Role | Baseline access |
|---|---|
| SuperAdmin | Dashboard, Companies, Registration, Matching, Reports, Gallery, Events, Cameras, Live Streams, Video, Users/Roles, Settings, Backup |
| Admin | All tenant operational functions plus tenant Users/Roles, Settings and Backup; no platform Companies administration |
| Supervisor | Operational recognition functions only; no Companies, Users/Roles, Settings or Backup administration |

`assigned_menus` is treated as a **restriction** of the role baseline, never as an elevation mechanism.

Company/tenant checks were added or strengthened around users, cameras, stream operations, recordings, WebSocket recognition channels, biometric image retrieval and matching-related company handling.

## 8. Camera / RTSP security

Updated camera handling includes:

- camera duplicate validation scoped by company;
- company-specific camera/license limits;
- RTSP URLs encrypted when saved to JSON and decrypted only inside the backend process;
- credential masking in log output;
- no built-in guessed/default camera passwords in the frontend;
- camera stream/start/stop/frame/recording operations verify tenant ownership;
- arbitrary legacy direct-stream and WebRTC-connect interfaces are disabled by default;
- native MJPEG consumers use the authenticated stream path supported by middleware.

## 9. Biometric image security

Gallery and captured-face image folders are no longer intended to be globally public static folders. Updated authenticated routes enforce tenant access before returning biometric image files.

The React client includes `ProtectedImage` for authenticated image retrieval using the bearer token and local blob URLs.

## 10. Event/input hardening

Legacy event ingestion endpoints that accepted filesystem-oriented input are disabled by default with `FRS_ENABLE_LEGACY_EVENT_INGESTION=0`. Upload limits and validation were strengthened in the active registration/video/image paths where updated.

## 11. Electron desktop hardening

Updated Electron shell includes:

- `nodeIntegration: false`;
- `contextIsolation: true`;
- sandbox enabled;
- web security enabled;
- DevTools only in development;
- external/new-window navigation denied;
- production application menu removed;
- Electron-compatible `HashRouter`;
- local backend default instead of a fixed LAN IP;
- renderer -> Electron API-base synchronization;
- file/video paths must come from user-approved pickers for sensitive IPC operations;
- selected bulk-registration images are constrained to user-approved folders;
- obsolete packaged stream-debug page removed.

## 12. Premium light UI

The desktop shell was changed from the inconsistent/dark visual system into one compact light product system. The information architecture remains the existing FRS application rather than a new marketing dashboard.

Four accent choices are implemented:

- **Sapphire:** `#2563EB`
- **Teal:** `#0F9D94`
- **Indigo:** `#6366F1`
- **Graphite:** `#475569`

The accents change primary controls, selected navigation and focus states while keeping the application light and consistent.

UI direction includes a compact ~224 px sidebar, compact desktop header, consistent page spacing, cleaner tables/forms, subtle borders/elevation, role-aware navigation and a Companies administration view for SuperAdmin.

## 13. Login experience

The existing animated security/login concept is retained and hardened rather than replaced with a generic form. It includes:

- role auto-detection option;
- password visibility control;
- clearer error/reset workflow;
- one-time password-reset flow;
- replaceable background animation/media.

Use `REACT_APP_LOGIN_MEDIA` to point to a GIF/image/video under `frontend/public/assets/`. If it is not set, the included login media is used. See `frontend/public/assets/LOGIN_MEDIA_README.txt`.

## 14. Companies administration

A missing Companies screen is now connected to the application for SuperAdmin. It supports company listing/search and create/edit/delete operations using the existing backend company APIs. Company deletion continues through the backend cleanup path so tenant-scoped tokens, camera/collection records, caches/streams and related company data can be cleaned consistently.

## 15. Startup order

The updated backend startup sequence performs the important compatibility steps in this order:

1. harden legacy JSON secrets;
2. backfill existing augmented registration references into the live gallery when enabled;
3. start license/background operational services;
4. restore configured active streams where possible;
5. create/update the JSON -> SQLite migration snapshot when enabled.

This order ensures secrets are protected before they are copied into the migration DB and existing registrations are connected to the live recognition gallery before normal operation.

## 16. Configuration

Use the root `.env.example` as the configuration checklist. Important production values are:

- `FRS_JWT_SECRET`
- `FRS_DATA_ENCRYPTION_KEY`
- `FRS_CORS_ORIGINS`
- `FRS_ACCESS_TOKEN_MINUTES`
- `FRS_AUTO_MIGRATE_JSON`
- `FRS_AUTO_BACKFILL_GALLERY`
- legacy endpoint flags kept at `0`
- `API_BASE_URL` / `REACT_APP_API_BASE_URL`

## 17. Verification performed for this handover

- Full Python `compileall` completed successfully for `backend_face` after the final backend changes.
- Electron `frontend/main.js` passed `node --check`.
- Electron `frontend/preload.js` passed `node --check`.
- Release JSON files are validated during packaging.
- Runtime secrets/biometric/customer data are removed from the push-ready release copy rather than publishing the supplied live data.

The complete React production build and real RTSP/CV end-to-end test remain environment-dependent. The supplied project status had already recorded that the active environment was missing `insightface` for backend test collection. The user requested the source package for local execution/testing.

## 18. First customer/deployment expectations

The release ZIP is intentionally push-ready and does not contain the supplied live camera credentials, active tokens, biometric registrations/captures or customer-specific runtime databases. For a clean deployment:

1. configure environment secrets;
2. install backend/frontend dependencies;
3. start backend;
4. bootstrap the first SuperAdmin if `users.json` is empty;
5. create the company/tenant structure;
6. configure cameras through the secured Camera UI;
7. register identities; augmentation and live gallery synchronization will occur automatically;
8. verify live RTSP recognition and best-frame saving;
9. verify JSON migration status before switching future repositories to DB-backed implementations.

See `RUN_AND_TEST.md` for commands.

## 19. CEO UI and backup stabilization pass - 31 August 2026

The supplied 52-page UI capture was used as the visual acceptance reference for the final product pass. The application keeps the same criminal-identification information architecture, but the desktop surface is now designed around compact, readable controls instead of large empty panels or hidden overflow.

Implemented in this pass:

- sidebar collapse state persists and restores correctly; collapsed parent navigation remains usable and shows tooltips;
- content pages use the available Electron working area instead of nested `100vh` layouts that hide controls;
- Dashboard and Face Recognition Analytics were compacted into clean white panels with smaller charts, readable light-theme chart text, and no cyber grid/glow/scanning decoration;
- Weekly/Monthly Recognition Report keeps Search, Status, Date Range, CSV, PDF and Refresh controls visible with wrapping on narrow screens;
- Gallery and Events filters/actions were compacted and hover motion that shifts the layout was removed;
- Camera Add/Edit was rebuilt as a typeable form for Camera Name, Location, Collection and Stream URL; collection description fields explicitly accept text and no longer sit behind overlapping UI;
- camera/collection/stream pages now use the remaining content height rather than another viewport height;
- Stream Viewer has a compact header, layout selector, refresh button and non-shifting video cards;
- Settings now fills the working area and contains only recognition/display controls plus SuperAdmin-only tenant/camera-limit/SMTP configuration;
- Backup & Recovery is a light full-width operational screen with status, backup list, preview/download/restore/delete, retention and audit log controls;
- all JSX `<button>` elements in `frontend/src` were statically audited; no potentially inert button remains after adding missing CSV/details/fullscreen actions.

### Redis-independent backup behavior

`FRS_BACKUP_MODE=auto` is now the default operational recommendation. In this mode the backend:

1. uses Redis backup when Redis is reachable;
2. automatically falls back to local JSON/SQLite/registered-gallery backup when Redis is unavailable;
3. returns a successful backup response instead of HTTP 503 solely because Redis timed out;
4. exposes `/api/backup/status` so the UI clearly shows `Redis backup` or `Local application backup`;
5. excludes runtime session tokens and the machine-local `.data_key` from local backup archives.

Use `FRS_BACKUP_MODE=redis` only when Redis is mandatory and an unavailable Redis server should block backup operations. Use `FRS_BACKUP_MODE=local` when the deployment does not use Redis.

### Verification for this final pass

- `python -m compileall -q backend_face`: **PASS**.
- TypeScript parser/transpiler syntax scan over all 58 frontend JS/JSX files: **PASS, 0 syntax errors**.
- PostCSS parser scan over all 41 frontend CSS files: **PASS, 0 parse errors**.
- Static button audit over 195 JSX buttons: **PASS, 0 potentially inert buttons**.
- Local backup test: **PASS**, 168 application files collected, preview/list successful, `.data_key` and `tokens.json` excluded.
- Auto backup fallback test with Redis unavailable: **PASS**, active mode changed to local and backup completed.
- Full `npm run build` could not be completed in this execution environment because `npm ci` dependency installation timed out. The source syntax/CSS checks above passed; run the production build on the target Windows machine as part of acceptance.

## 20. Handover package type

The `*_full_test.zip` handover intentionally keeps the supplied local criminal-identification runtime configuration required for the owner's own testing. It can therefore include encrypted camera/application configuration and the local key required to use those already-encrypted values. **Do not publish that runtime data or `.data_key` to a public repository.** For a public code push, sanitize customer data/secrets first and configure `FRS_DATA_ENCRYPTION_KEY` from the deployment environment.
