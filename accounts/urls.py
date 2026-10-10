from django.urls import path

from accounts import views

app_name = "accounts"
urlpatterns = [path("verify/", views.verify_view, name="verify")]
