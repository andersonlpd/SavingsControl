from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.forms import LoginForm, VerificationForm
from accounts.models import RecoveryDevice


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if TOTPDevice.objects.devices_for_user(user, confirmed=True).exists():
            return redirect("accounts:verify")
        return redirect("two_factor:setup")
    return render(request, "accounts/login.html", {"form": form})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def verify_view(request):
    devices = list(TOTPDevice.objects.devices_for_user(request.user, confirmed=True))
    recovery_devices = list(RecoveryDevice.objects.devices_for_user(request.user, confirmed=True))
    if not devices:
        return redirect("two_factor:setup")

    form = VerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]
        verified = next((device for device in devices if device.verify_token(token)), None)
        if verified is None:
            verified = next(
                (device for device in recovery_devices if device.verify_token(token)), None
            )
        if verified:
            otp_login(request, verified)
            next_url = (
                request.POST.get("next") or request.GET.get("next") or reverse("reports:dashboard")
            )
            if url_has_allowed_host_and_scheme(
                next_url, {request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("reports:dashboard")
        form.add_error("token", "Código inválido ou temporariamente bloqueado.")
    return render(request, "accounts/verify.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("account_login")
