from datetime import date
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from expenses.models import Budget, Category, CategoryRule, ExpenseTransaction
from expenses.services import (
    category_for_description,
    normalize_description,
    reconcile_budget_alerts,
    reconcile_transaction_budgets,
)
from portfolio.services import MONEY_SCALE, to_scaled


class ManualExpenseForm(forms.Form):
    transaction_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(max_length=240)
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    currency = forms.ChoiceField(choices=ExpenseTransaction.Currency.choices, initial="BRL")
    direction = forms.ChoiceField(choices=ExpenseTransaction.Direction.choices, initial="DEBIT")
    category = forms.ModelChoiceField(queryset=Category.objects.filter(active=True), required=False)

    def clean_transaction_date(self):
        transaction_date = self.cleaned_data["transaction_date"]
        if transaction_date > timezone.localdate():
            raise ValidationError("A data do gasto não pode ser futura.")
        return transaction_date

    def save(self):
        values = self.cleaned_data
        rule_category = category_for_description(values["description"])
        category = values["category"] or rule_category
        if category is None:
            category, _ = Category.objects.get_or_create(name="Revisar")
        source = "MANUAL" if values["category"] else ("RULE" if rule_category else "REVIEW")
        with transaction.atomic():
            transaction_item = ExpenseTransaction.objects.create(
                source=ExpenseTransaction.Source.MANUAL,
                transaction_date=values["transaction_date"],
                description=values["description"],
                amount_minor=to_scaled(values["amount"], MONEY_SCALE),
                currency=values["currency"],
                direction=values["direction"],
                status=ExpenseTransaction.Status.POSTED,
                category=category,
                category_source=source,
            )
            reconcile_transaction_budgets(transaction_item)
        return transaction_item


class TransactionCategoryForm(forms.Form):
    description = forms.CharField(max_length=240)
    category = forms.ModelChoiceField(queryset=Category.objects.filter(active=True))
    create_rule = forms.BooleanField(
        required=False, label="Usar esta categoria para descrições idênticas no futuro"
    )

    def save(self, transaction_item):
        old_category, old_date = transaction_item.category, transaction_item.transaction_date
        transaction_item.description = self.cleaned_data["description"]
        transaction_item.category = self.cleaned_data["category"]
        transaction_item.category_source = "MANUAL"
        with transaction.atomic():
            transaction_item.save(
                update_fields=["description", "category", "category_source", "updated_at"]
            )
            if self.cleaned_data["create_rule"]:
                CategoryRule.objects.update_or_create(
                    pattern=normalize_description(transaction_item.description),
                    defaults={"category": transaction_item.category},
                )
            reconcile_transaction_budgets(transaction_item, old_category, old_date)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "group", "active"]


class CategoryRuleForm(forms.ModelForm):
    class Meta:
        model = CategoryRule
        fields = ["pattern", "category"]

    def clean_pattern(self):
        return normalize_description(self.cleaned_data["pattern"])


class BudgetForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.filter(active=True))
    month = forms.CharField(max_length=7, widget=forms.TextInput(attrs={"type": "month"}))
    limit = forms.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))

    def clean_month(self):
        try:
            year, month = (int(part) for part in self.cleaned_data["month"].split("-"))
            return date(year, month, 1)
        except (ValueError, TypeError):
            raise ValidationError("Informe um mês válido.") from None

    def save(self):
        v = self.cleaned_data
        with transaction.atomic():
            budget, _ = Budget.objects.update_or_create(
                category=v["category"],
                month=v["month"],
                defaults={"limit_minor_brl": to_scaled(v["limit"], MONEY_SCALE)},
            )
            reconcile_budget_alerts(budget)
        return budget
