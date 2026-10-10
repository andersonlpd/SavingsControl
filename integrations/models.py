from django.db import models


class SyncRun(models.Model):
    class Source(models.TextChoices):
        PLUGGY = "PLUGGY", "Pluggy"
        MARKET = "MARKET", "Cotações e índices"

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Em execução"
        SUCCESS = "SUCCESS", "Concluída"
        FAILED = "FAILED", "Falhou"

    source = models.CharField(max_length=12, choices=Source.choices)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices)
    records_seen = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    safe_error_code = models.CharField(max_length=64, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["source", "-started_at"], name="sync_source_started_idx")]
