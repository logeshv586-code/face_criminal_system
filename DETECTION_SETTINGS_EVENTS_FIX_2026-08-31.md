# Detection, Settings, Events and Stream Viewer Fix — 31 Aug 2026

This pass responds to live testing feedback after the CEO UI/Redis release.

## Live camera / detection
- Strengthened duplicate face-box suppression for the detector double-box pattern visible on `testcamera`.
- The tracker now reuses the same track for strongly overlapping same-face boxes, reducing duplicate `Unknown` boxes and duplicate unknown captures.
- Recognition settings are now tenant-aware and consumed by the live face pipeline with a short cache (about 2 seconds).
- Settings now control: recognition enable/disable, detection confidence target, normal match tolerance, long-distance tolerance, minimum face size, known/unknown save confidence and known/unknown capture cooldown.
- Global bounding-box setting is now combined with the per-camera `BOXES` toggle.

## Settings UI
- Rebuilt as a centered, compact desktop settings workspace (`max-width: 1180px`).
- Added only operational sections: Configuration Target, Recognition Engine, Capture & Display, General Camera Limits, and Email/SMTP Notifications.
- Added SMTP test-email action.
- Stored SMTP password is never returned to the renderer; blank password on Save preserves the existing encrypted password.
- Company settings inherit system defaults and can override them.

## Events / face images
- Corrected unknown capture WebSocket image URLs to include the required `/unknown/` path segment.
- Event API now returns both `image_path` and `image_url` using authenticated capture-image routes.
- Protected images retry once and render stable placeholders while loading.
- Event list thumbnails were enlarged and given fixed dimensions.
- Tenant ID comparison is normalized to match the sanitized storage path used by captures.
- Image response MIME type is detected from the actual file.

## Stream Viewer
- Added `Auto` layout as the default.
- One active camera now uses one full grid cell instead of being surrounded by three `No Camera` placeholders.
- Empty placeholder cells are no longer created.
- Existing manual grid layouts still limit how many cameras are shown.

## Verification performed in this environment
- `python -m compileall -q backend_face` passes.
- Electron `main.js` and `preload.js` pass Node syntax checks.
- Duplicate-box geometry based on the supplied screenshot is classified as one face; clearly separate adjacent boxes are not merged.
- Runtime settings helper returns the expected configured defaults: detection 0.35, recognition tolerance 0.55, long-distance tolerance 0.60, min face size 20px.

Final recognition accuracy still depends on the actual camera, lighting, registered reference quality and customer-side CV dependencies (`face_recognition`, `insightface`).
