from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.decorators.http import require_GET
from two_factor.urls import urlpatterns as two_factor_urlpatterns

from accounts.views import login_view, logout_view


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


otp_patterns = [
    path("account/login/", login_view, name="login"),
    *(
        pattern
        for pattern in two_factor_urlpatterns[0]
        if pattern.name != "login"
    ),
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="account_login", permanent=False), name="home"),
    path("health/", health, name="health"),
    path("account/login/", login_view, name="account_login"),
    path("account/logout/", logout_view, name="account_logout"),
    path("account/", include("accounts.urls")),
    path("", include((otp_patterns, "two_factor"), namespace="two_factor")),
    path("", include("reports.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("expenses/", include("expenses.urls")),
    path("settings/integrations/", include("integrations.urls")),
]
