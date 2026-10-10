from django.urls import path

from reports import views

app_name = "reports"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/reports/portfolio", views.portfolio_report, name="portfolio_report"),
]
