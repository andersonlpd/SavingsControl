from django.urls import path

from integrations.views import status

app_name = "integrations"
urlpatterns = [path("", status, name="status")]
