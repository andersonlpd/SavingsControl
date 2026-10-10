from datetime import date
from decimal import Decimal

from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone

from expenses.forms import ManualExpenseForm
from expenses.models import Budget, BudgetAlert, Category, ExpenseTransaction
from expenses.services import (
    normalize_description,
    reconcile_budget_alerts,
    reconcile_transaction_budgets,
)
from reports.templatetags.saving_tags import money_minor


class ExpenseRulesAndLimitsTests(TestCase):
    def test_normalization_is_accent_and_case_insensitive(self):
        self.assertEqual(normalize_description("  CAFÉ   São José "), "cafe sao jose")

    def test_threshold_alerts_reconcile_without_duplicate_rows(self):
        category = Category.objects.create(name="Mercado")
        budget = Budget.objects.create(
            category=category, month=date(2026, 10, 1), limit_minor_brl=10_000
        )
        expense = ExpenseTransaction.objects.create(
            source="MANUAL",
            transaction_date=date(2026, 10, 8),
            description="Compra",
            amount_minor=8_000,
            currency="BRL",
            direction="DEBIT",
            status="POSTED",
            category=category,
        )
        reconcile_budget_alerts(budget)
        self.assertEqual(list(BudgetAlert.objects.values_list("threshold", flat=True)), [80])

        expense.amount_minor = 10_000
        expense.save(update_fields=["amount_minor"])
        reconcile_budget_alerts(budget)
        self.assertEqual(set(BudgetAlert.objects.values_list("threshold", flat=True)), {80, 100})

        expense.amount_minor = 5_000
        expense.save(update_fields=["amount_minor"])
        reconcile_budget_alerts(budget)
        expense.amount_minor = 10_000
        expense.save(update_fields=["amount_minor"])
        reconcile_budget_alerts(budget)
        self.assertEqual(BudgetAlert.objects.count(), 2)
        self.assertEqual(BudgetAlert.objects.filter(active=True).count(), 2)

    def test_removing_a_transaction_deactivates_its_month_alert(self):
        category = Category.objects.create(name="Transporte")
        budget = Budget.objects.create(
            category=category, month=date(2026, 10, 1), limit_minor_brl=10_000
        )
        item = ExpenseTransaction.objects.create(
            source="MANUAL",
            transaction_date=date(2026, 10, 8),
            description="Ônibus",
            amount_minor=8_000,
            currency="BRL",
            direction="DEBIT",
            status="POSTED",
            category=category,
        )
        reconcile_budget_alerts(budget)
        item.delete()
        reconcile_transaction_budgets(item, category, date(2026, 10, 8))
        self.assertFalse(BudgetAlert.objects.get(budget=budget, threshold=80).active)

    def test_manual_expense_date_has_today_button(self):
        html = render_to_string("partials/form_fields.html", {"form": ManualExpenseForm()})
        self.assertIn('id="set-transaction-today"', html)

    def test_manual_expense_accepts_brazilian_decimal_and_formats_reais(self):
        form = ManualExpenseForm(
            data={
                "transaction_date": timezone.localdate().isoformat(),
                "description": "Mercado",
                "amount": "1234,56",
                "currency": "BRL",
                "direction": "DEBIT",
                "category": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount"], Decimal("1234.56"))
        self.assertEqual(money_minor(123456), "R$ 1.234,56")
