import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import RecoveryDevice, RecoveryToken


@override_settings(SECURE_SSL_REDIRECT=False)
class RecoveryCodeTests(TestCase):
    def test_codes_are_hashed_and_consumed_once(self):
        user = get_user_model().objects.create_user(
            username="owner", password="a-long-test-password"
        )
        codes = RecoveryDevice.issue_codes(user, count=1)
        device = RecoveryDevice.objects.get(user=user)
        stored = RecoveryToken.objects.get(device=device)
        self.assertNotEqual(stored.digest, codes[0])
        self.assertTrue(device.verify_token(codes[0]))
        self.assertFalse(device.tokens.exists())

    def test_password_only_session_is_forced_to_mfa_setup_or_verification(self):
        user = get_user_model().objects.create_user(
            username="owner", password="a-long-test-password"
        )
        response = self.client.post(
            "/account/login/",
            {"username": "owner", "password": "a-long-test-password"},
        )
        self.assertRedirects(response, "/account/two_factor/setup/", fetch_redirect_response=False)
        response = self.client.get("/dashboard/")
        self.assertRedirects(response, "/account/two_factor/setup/", fetch_redirect_response=False)

        TOTPDevice.objects.create(user=user, name="default", key="a" * 40)
        response = self.client.get("/dashboard/")
        self.assertRedirects(response, "/account/verify/", fetch_redirect_response=False)
        device = TOTPDevice.objects.get(user=user)
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = time.time()
        response = self.client.post("/account/verify/", {"token": str(totp.token()).zfill(6)})
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        for url in ("/dashboard/", "/portfolio/", "/expenses/", "/settings/integrations/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
