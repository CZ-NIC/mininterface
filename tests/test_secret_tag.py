from mininterface.tag import SecretTag
from shared import TestAbstract


class TestSecretTag(TestAbstract):
    """Tests for SecretTag functionality"""

    def test_secret_masking(self):
        secret = SecretTag("mysecret")
        self.assertEqual("••••••••", secret._get_masked_val())

        self.assertFalse(secret.toggle_visibility())
        self.assertEqual("mysecret", secret._get_masked_val())

    def test_toggle_visibility(self):
        secret = SecretTag("test", show_toggle=False)
        self.assertTrue(secret._masked)
        self.assertFalse(secret.toggle_visibility())
        self.assertFalse(secret._masked)

    def test_repr_safety(self):
        secret = SecretTag("sensitive_data")
        self.assertEqual("SecretTag(masked_value)", repr(secret))

    def test_annotation_default(self):
        secret = SecretTag("test")
        self.assertEqual(str, secret.annotation)
