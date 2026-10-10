from django.urls import path

from portfolio import views

app_name = "portfolio"
urlpatterns = [
    path("", views.portfolio_home, name="home"),
    path("assets/search/", views.asset_search, name="asset_search"),
    path("assets/", views.assets, name="assets"),
    path("operations/", views.operations, name="operations"),
    path("fixed-income/", views.fixed_income, name="fixed_income"),
    path(
        "fixed-income/<int:contract_id>/redemptions/",
        views.redeem_fixed_income,
        name="redeem_fixed_income",
    ),
    path(
        "fixed-income/<int:contract_id>/valuation/",
        views.fixed_income_valuation,
        name="fixed_income_valuation",
    ),
    path("income/", views.income, name="income"),
    path("quotes/", views.quotes, name="quotes"),
    path("snapshots/", views.snapshots, name="snapshots"),
]
