import unicodedata

from django.db.models import Sum

from expenses.models import Budget, BudgetAlert, CategoryRule, ExpenseTransaction


def normalize_description(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(ch for ch in decomposed if not unicodedata.combining(ch)).split())


def category_for_description(description):
    normalized = normalize_description(description)
    rule = CategoryRule.objects.select_related("category").filter(pattern=normalized).first()
    return rule.category if rule else None


def monthly_spend(budget):
    transactions = ExpenseTransaction.objects.filter(
        category=budget.category,
        currency="BRL",
        transaction_date__year=budget.month.year,
        transaction_date__month=budget.month.month,
        status=ExpenseTransaction.Status.POSTED,
    )
    debit = (
        transactions.filter(direction=ExpenseTransaction.Direction.DEBIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    credit = (
        transactions.filter(direction=ExpenseTransaction.Direction.CREDIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    return debit - credit


def reconcile_budget_alerts(budget):
    spent = monthly_spend(budget)
    for threshold in (80, 100):
        reached = spent * 100 >= budget.limit_minor_brl * threshold
        alert = BudgetAlert.objects.filter(budget=budget, threshold=threshold).first()
        if reached and alert is None:
            BudgetAlert.objects.create(budget=budget, threshold=threshold, active=True)
        elif alert is not None and alert.active != reached:
            alert.active = reached
            alert.save(update_fields=["active"])


def reconcile_transaction_budgets(transaction_item, old_category=None, old_date=None):
    affected = {
        (
            transaction_item.category_id,
            transaction_item.transaction_date.year,
            transaction_item.transaction_date.month,
        )
    }
    if old_category:
        affected.add((old_category.pk, old_date.year, old_date.month))
    for category_id, year, month in affected:
        for budget in Budget.objects.filter(
            category_id=category_id, month__year=year, month__month=month
        ):
            reconcile_budget_alerts(budget)
