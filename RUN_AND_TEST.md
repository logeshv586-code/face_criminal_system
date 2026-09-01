# Run and Test - Criminal Identification FRS

## 1. Backend

PowerShell / Windows:

```powershell
cd backend_face
python -m pip install -r ..\requirements.txt
python start_server.py
```

Default backend URL: `http://127.0.0.1:8005`  
Interactive API schema: `http://127.0.0.1:8005/docs`

## 2. First SuperAdmin on a clean release

The push-ready package removes customer accounts and tokens. Create the first SuperAdmin once through the bootstrap endpoint:

```powershell
$body = @{
  username = "admin"
  password = "password123"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8005/api/auth/bootstrap/superadmin" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Then login through the Electron/React application and change/configure deployment-specific values.

## 3. Frontend development

```powershell
cd frontend
npm install
npm run dev
```

To build the React bundle:

```powershell
npm run build
```

To package Electron after the React build:

```powershell
npm run electron-pack
```

## 4. Existing-site upgrade instead of a clean install

If you overlay the updated code onto an existing installation and retain its `backend_face/data/` folder:

- startup encrypts supported plaintext JSON secrets;
- legacy raw bearer-token records are revoked;
- old augmented identity folders are backfilled into the live gallery (up to 50/person);
- changed JSON files are snapshotted into `data/frs_migration.db` automatically.

Back up the live data folder before upgrading.

## 5. Live recognition test

1. Create/login as an authorized user.
2. Add a tenant camera using its real RTSP URL.
3. Register one test identity with a clear frontal reference photo.
4. Confirm the registration creates/synchronizes up to 50 references in the tenant gallery.
5. Start the camera stream.
6. Present the identity at several angles/distances.
7. Confirm the live stream recognizes against the reference embeddings without a training job.
8. Confirm the saved recognition crop is a sharp buffered frame when multiple frames are available.
9. Confirm known/unknown captures appear only for the correct company.

## 6. JSON -> DB migration check

Login as SuperAdmin and inspect:

- `GET /api/migration/status`
- `POST /api/migration/json-to-sqlite`
- `POST /api/migration/backfill-gallery`

`FRS_AUTO_MIGRATE_JSON=1` and `FRS_AUTO_BACKFILL_GALLERY=1` perform the normal compatibility work automatically on startup.

## 7. Login GIF/video customization

Place media under:

`frontend/public/assets/`

Then add to `frontend/.env` for a GIF:

```env
REACT_APP_LOGIN_MEDIA=/assets/company-login.gif
```

or for video:

```env
REACT_APP_LOGIN_MEDIA=/assets/company-login.mp4
```

Rebuild the frontend after changing `.env`.

## 8. Recommended acceptance checks

- SuperAdmin sees Companies; Admin/Supervisor do not.
- Admin cannot access another company's camera/users/biometric images.
- Supervisor cannot access Users, Settings, Backup or Companies.
- Sapphire/Teal/Indigo/Graphite accents all remain light and compact.
- Password reset token expires and old login sessions are revoked after reset.
- `cameras.json` contains encrypted `enc:v1:` RTSP values after camera configuration.
- settings secret fields are encrypted when saved.
- no raw bearer token is stored as a key in `tokens.json`.
- live recognition continues after application restart and gallery cache rebuild.

## 9. Backup without Redis

The updated application does not require Redis just to create an operational backup.

Recommended `.env` configuration:

```env
FRS_BACKUP_MODE=auto
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
```

When Redis is unavailable, **Backup & Recovery** should show `Local application backup` and **Trigger Backup** should create a JSON/SQLite/gallery application backup instead of returning `503 Service Unavailable`.

To force local-only behavior:

```env
FRS_BACKUP_MODE=local
```

Use `FRS_BACKUP_MODE=redis` only when the deployment intentionally requires Redis.

Acceptance check:

1. Open **Backup & Recovery**.
2. Confirm the mode strip says Redis or Local application backup.
3. Click **Trigger Backup**.
4. Confirm the backup appears in the table.
5. Test Preview and Download.
6. Test Restore only on disposable/test data before production use.

## 10. UI acceptance checklist

Test the desktop window at 1366x768 and 1920x1080:

- Collapse and reopen the sidebar repeatedly; navigation labels/tooltips and active menu state must remain usable.
- Dashboard: Export CSV, Export PDF and Refresh remain visible; Weekly Recognition Analytics is fully visible.
- Recognition Analytics: profile list, selected face, metrics and charts remain inside the content width.
- Weekly/Monthly Report: Search, Status, Date Range, CSV, PDF and Refresh remain visible and usable.
- Gallery: Search, status/filter, view toggle and Refresh remain visible.
- Events: filters, date inputs, Clear and Search remain typeable/clickable.
- Cameras: Camera Name, Location, Collection, Stream URL and collection description all accept typing; Add/Save/Delete/Cancel work.
- Stream Viewer: layout selector, refresh and per-camera controls remain visible after sidebar collapse.
- Settings: page fills available working area; only role-appropriate operational settings are shown.
- Backup: Trigger, Preview, Download, Restore, Delete, Retention and Audit Log controls are visible.
- Login: credential input, password visibility and password-reset flow remain usable with the configured GIF/image/video media.

If the frontend dependencies are already cached on the target machine, finish with:

```powershell
cd frontend
npm install
npm run build
```
