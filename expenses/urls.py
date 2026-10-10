from django.urls import path

from expenses import views

app_name = "expenses"
urlpatterns = [
    path("", views.expenses_home, name="home"),
    path("manual/", views.manual_expense, name="manual"),
    path("categories/", views.categories, name="categories"),
    path("categories/rules/<int:rule_id>/", views.edit_rule, name="edit_rule"),
    path("<int:transaction_id>/categorize/", views.categorize, name="categorize"),
    path("<int:transaction_id>/remove/", views.remove_manual_transaction, name="remove_manual"),
    path("budgets/", views.budgets, name="budgets"),
]
