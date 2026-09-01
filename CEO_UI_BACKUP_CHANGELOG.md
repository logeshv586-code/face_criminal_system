# CEO UI + Backup Stabilization Changelog

## User-reported issues addressed

- Redis timeout caused `POST /api/backup/trigger` to return 503.
- Weekly recognition analytics/report controls could be hidden in the available Electron window.
- Current UI had excessive empty space, oversized panels and inconsistent visual styles.
- Camera and collection description inputs could become difficult/impossible to type into.
- Settings did not use the working area efficiently and contained low-value/empty sections.
- Sidebar collapse needed reliable open/close behavior.
- Several dormant UI buttons had no action.

## Result

- Redis preferred/local fallback backup mode with `/api/backup/status`.
- Compact professional light product system using Sapphire, Teal, Indigo or Graphite accents.
- Dashboard + Face Recognition Analytics layout stabilization.
- Weekly/Monthly report toolbar and table visibility improvements.
- Gallery, Events, Camera, Stream Viewer, Settings and Backup layout improvements.
- Camera and collection fields explicitly typeable.
- Persistent 236px / 68px sidebar expansion/collapse behavior.
- Missing CSV, recognition-detail and fullscreen button actions connected.
- Backend/JSX/CSS/static-button verification completed; see `FINAL_SIP.md`.
