from datetime import timedelta

from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Remove registros de tentativas e sessões do Axes com mais de 30 dias."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        for model in (AccessAttempt, AccessFailureLog, AccessLog):
            model.objects.filter(attempt_time__lt=cutoff).delete()
        self.stdout.write("Registros de autenticação antigos removidos.")
