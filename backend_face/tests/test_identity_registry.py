import unittest

from backend_face.identity_registry import identity_is_registered, registered_identity_keys


class IdentityRegistryTests(unittest.TestCase):
    def test_new_registration_becomes_allowed(self):
        metadata = {
            "logesh": {"name": "Logesh", "company_id": "acme"},
            "ram": {"name": "Ram", "company_id": "other"},
        }
        keys = registered_identity_keys(metadata, "acme")
        self.assertTrue(identity_is_registered("logesh", keys))
        self.assertFalse(identity_is_registered("ram", keys))

    def test_deleted_registration_is_not_allowed_even_if_gallery_embedding_exists(self):
        before = {"persons": {"logesh": {"name": "Logesh", "company_id": "acme"}}}
        after = {"persons": {}}
        self.assertTrue(identity_is_registered("logesh", registered_identity_keys(before, "acme")))
        self.assertFalse(identity_is_registered("logesh", registered_identity_keys(after, "acme")))

    def test_company_scope_prevents_cross_tenant_identity_leak(self):
        metadata = {
            "persons": {
                "same_name": {"name": "Same Name", "company_id": "company-a"},
                "other_person": {"name": "Other", "company_id": "company-b"},
            }
        }
        a = registered_identity_keys(metadata, "company-a")
        b = registered_identity_keys(metadata, "company-b")
        self.assertEqual(a, {"same_name"})
        self.assertEqual(b, {"other_person"})

    def test_missing_metadata_can_fail_open_for_legacy_runtime(self):
        self.assertTrue(identity_is_registered("legacy_person", None))


if __name__ == "__main__":
    unittest.main()
