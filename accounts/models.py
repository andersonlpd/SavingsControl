from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django_otp.models import Device, ThrottlingMixin, TimestampMixin


class RecoveryDevice(TimestampMixin, ThrottlingMixin, Device):
    """One-time recovery codes stored as Django password hashes."""

    def get_throttle_factor(self):
        return 1

    def verify_token(self, token):
        allowed, _ = self.verify_is_allowed()
        if not allowed:
            return False

        matched = None
        with transaction.atomic():
            for recovery_token in self.tokens.select_for_update().all():
                if check_password(token, recovery_token.digest):
                    matched = recovery_token
            if matched:
                matched.delete()
                self.throttle_reset(commit=False)
                self.set_last_used_timestamp(commit=False)
                self.save(
                    update_fields=[
                        "throttling_failure_timestamp",
                        "throttling_failure_count",
                        "last_used_at",
                    ]
                )
            else:
                self.throttle_increment()
        return matched is not None

    @classmethod
    def issue_codes(cls, user, count=10):
        from secrets import token_urlsafe

        device, _ = cls.objects.get_or_create(user=user, name="recovery")
        codes = [token_urlsafe(9) for _ in range(count)]
        RecoveryToken.objects.bulk_create(
            [RecoveryToken(device=device, digest=make_password(code)) for code in codes]
        )
        return codes


class RecoveryToken(models.Model):
    device = models.ForeignKey(RecoveryDevice, on_delete=models.CASCADE, related_name="tokens")
    digest = models.CharField(max_length=128)
