# Recognition Identity Stability Hardening — 1 Sep 2026

This change addresses the live gallery failure where one physical face could appear under different registered names or as `Unknown`, while blurry/distant crops were repeatedly saved.

## Live decision safeguards

- Detector boxes are de-duplicated before tracking, recognition, or evidence saving.
- Detection and identity are separated: small/far faces can still be detected, but identity is withheld below the identity-size gate.
- A named match requires multiple agreeing templates and a safe second-person distance margin.
- New identities require repeated fresh confirmation.
- A confirmed track cannot silently switch to another registered person. Conflicting evidence returns `Unknown` until the original identity is re-confirmed or a longer fresh switch-confirmation streak completes.
- Old permissive tenant recognition thresholds are capped by hard safety ceilings/floors in the runtime pipeline.
- Named detections carry `review_required: true`; recognition is candidate evidence, not an automatic criminal conclusion.

## Gallery / enrollment-reference safeguards

- Live gallery activation rejects small, dark/overexposed, low-information, multi-face, or incoherent references.
- At least three coherent references are required before an identity is eligible for live known matching.
- Only a compact maximum of 12 coherent references per identity are used, so 50 synthetic variants cannot behave like 50 independent votes.
- Cross-person gallery centres that are dangerously close are both withheld from live known matching until cleaner re-enrollment resolves the collision.
- The embedding cache has a new policy version, forcing old permissive caches to rebuild under the new reference rules.

## Evidence / gallery flood safeguards

- Known evidence is keyed by stable registered identity, not temporary tracker ID.
- Unknown evidence is grouped into short-lived camera-stream clusters that can survive tracker restarts.
- Evidence requires multiple observations and quality/size/confidence gates.
- The best crop seen during the evidence window is retained and saved, rather than blindly saving the current blurry frame.
- Known/unknown camera-level cooldowns default to 30s/20s and are enforced even if older tenant settings were more permissive.
- Camera folders use the configured camera name (or deterministic camera ID fallback), not a random stream UUID.

## Attendance isolation

No attendance database schema, punch rules, attendance endpoints, or attendance persistence code were modified in this hardening pass. `backend_face/save_face.py` is intentionally unchanged. The live recognition pipeline still calls the existing save function; this change only makes the upstream identity/evidence decision more conservative and reduces duplicate calls.

## Main modules

- `backend_face/recognition_guard.py` — dependency-free temporal identity transition guard.
- `backend_face/face_pipeline.py` — live detector de-duplication, conservative matching, re-confirmation, evidence quality, stable cooldown keys.
- `backend_face/fr1.py` — quality/coherence/collision filtering for gallery references and safe cache rebuild.
- `backend_face/auth/storage.py` and `backend_face/data/auth/settings_default.json` — safer operational defaults.
- `.env.example` — deployment-level safety ceilings/floors.
- `backend_face/tests/test_recognition_guard.py` — regression tests for `logesh -> ram` style silent switching and stable evidence keys.
- `.github/workflows/recognition-safety.yml` — dependency-free safety gate plus Python syntax checks.
