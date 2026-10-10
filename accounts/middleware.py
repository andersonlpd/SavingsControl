from django.shortcuts import redirect
from two_factor.utils import default_device


class RequireSecondFactorMiddleware:
    """Let an authenticated user reach only MFA verification/enrollment until verified."""

    public_prefixes = (
        "/static/",
        "/health/",
        "/account/login/",
        "/account/logout/",
        "/account/verify/",
    )
    enrollment_prefixes = (
        "/account/two_factor/setup/",
        "/account/two_factor/qrcode/",
        "/account/two_factor/setup/complete/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path
        if (
            user.is_authenticated
            and not user.is_verified()
            and not path.startswith(self.public_prefixes)
        ):
            if default_device(user):
                return redirect("accounts:verify")
            if not path.startswith(self.enrollment_prefixes):
                return redirect("two_factor:setup")
        return self.get_response(request)
