from django.shortcuts import render
from django.views.decorators.http import require_GET
from django_otp.decorators import otp_required

from integrations.models import SyncRun


@otp_required
@require_GET
def status(request):
    sources = []
    for source, label in SyncRun.Source.choices:
        sources.append(
            {
                "label": label,
                "run": SyncRun.objects.filter(source=source).first(),
                "success": SyncRun.objects.filter(
                    source=source, status=SyncRun.Status.SUCCESS
                ).first(),
            }
        )
    return render(request, "integrations/status.html", {"sources": sources})
