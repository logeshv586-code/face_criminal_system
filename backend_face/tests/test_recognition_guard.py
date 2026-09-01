import json
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from recognition_guard import UNKNOWN, stable_known_evidence_key, update_identity_state


class IdentityGuardTests(unittest.TestCase):
    def test_new_identity_requires_repeated_agreement(self):
        state = {}
        self.assertEqual(
            update_identity_state(state, "logesh", candidate_is_strong=True, confirm_hits=2, switch_hits=4),
            UNKNOWN,
        )
        self.assertEqual(
            update_identity_state(state, "logesh", candidate_is_strong=True, confirm_hits=2, switch_hits=4),
            "logesh",
        )

    def test_confirmed_identity_never_silently_switches(self):
        state = {"confirmed_name": "logesh"}
        self.assertEqual(
            update_identity_state(state, "ram", candidate_is_strong=True, confirm_hits=2, switch_hits=4),
            UNKNOWN,
        )
        self.assertEqual(state["confirmed_name"], "logesh")
        self.assertTrue(state["identity_conflict"])

    def test_switch_needs_fresh_longer_confirmation(self):
        state = {"confirmed_name": "logesh"}
        outputs = [
            update_identity_state(state, "ram", candidate_is_strong=True, confirm_hits=2, switch_hits=4)
            for _ in range(4)
        ]
        self.assertEqual(outputs[:3], [UNKNOWN, UNKNOWN, UNKNOWN])
        self.assertEqual(outputs[3], "ram")
        self.assertEqual(state["confirmed_name"], "ram")

    def test_original_identity_clears_conflict(self):
        state = {"confirmed_name": "logesh"}
        self.assertEqual(update_identity_state(state, "ram", candidate_is_strong=True), UNKNOWN)
        self.assertEqual(update_identity_state(state, "logesh", candidate_is_strong=True), "logesh")
        self.assertFalse(state["identity_conflict"])

    def test_weak_evidence_cannot_complete_switch(self):
        state = {"confirmed_name": "logesh"}
        self.assertEqual(update_identity_state(state, "ram", candidate_is_strong=True), UNKNOWN)
        self.assertEqual(update_identity_state(state, "ram", candidate_is_strong=False), UNKNOWN)
        self.assertEqual(state["confirmed_name"], "logesh")
        self.assertEqual(state["pending_hits"], 1)

    def test_known_evidence_key_is_tracker_independent(self):
        self.assertEqual(stable_known_evidence_key("Logesh"), "known:logesh")
        self.assertNotIn("track", stable_known_evidence_key("Logesh"))


class ProductionDefaultsTests(unittest.TestCase):
    def test_default_settings_are_conservative(self):
        settings_path = BACKEND / "data" / "auth" / "settings_default.json"
        if not settings_path.exists():
            self.skipTest("settings_default.json is checked after the GitHub patch is assembled")
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertLessEqual(float(settings["recognition_tolerance"]), 0.50)
        self.assertLessEqual(float(settings["long_range_tolerance"]), 0.52)
        self.assertGreaterEqual(int(settings["min_identity_face_size"]), 56)
        self.assertGreaterEqual(int(settings["identity_switch_confirmations"]), 4)
        self.assertGreaterEqual(float(settings["known_capture_interval_seconds"]), 20.0)


if __name__ == "__main__":
    unittest.main()
