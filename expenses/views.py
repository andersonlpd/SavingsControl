from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django_otp.decorators import otp_required

from expenses.forms import (
    BudgetForm,
    CategoryForm,
    CategoryRuleForm,
    ManualExpenseForm,
    TransactionCategoryForm,
)
from expenses.models import Budget, Category, CategoryRule, ExpenseTransaction
from expenses.services import monthly_spend, reconcile_transaction_budgets


@otp_required
def expenses_home(request):
    transactions = ExpenseTransaction.objects.select_related("category")[:100]
    return render(request, "expenses/index.html", {"transactions": transactions})


@otp_required
@require_http_methods(["GET", "POST"])
def manual_expense(request):
    form = ManualExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Gasto registrado.")
        return redirect("expenses:home")
    return render(request, "expenses/manual.html", {"form": form})


@otp_required
@require_http_methods(["GET", "POST"])
def categories(request):
    category_form = CategoryForm(request.POST or None, prefix="category")
    rule_form = CategoryRuleForm(request.POST or None, prefix="rule")
    if request.method == "POST" and "save_category" in request.POST and category_form.is_valid():
        try:
            category_form.save()
        except IntegrityError:
            category_form.add_error("name", "Esta categoria já existe.")
        else:
            messages.success(request, "Categoria salva.")
            return redirect("expenses:categories")
    elif request.method == "POST" and "save_rule" in request.POST and rule_form.is_valid():
        try:
            rule_form.save()
        except IntegrityError:
            rule_form.add_error("pattern", "Já existe uma regra com essa descrição normalizada.")
        else:
            messages.success(request, "Regra local salva.")
            return redirect("expenses:categories")
    return render(
        request,
        "expenses/categories.html",
        {
            "category_form": category_form,
            "rule_form": rule_form,
            "categories": Category.objects.all(),
            "rules": CategoryRule.objects.select_related("category"),
        },
    )


@otp_required
@require_http_methods(["GET", "POST"])
def categorize(request, transaction_id):
    item = get_object_or_404(ExpenseTransaction, pk=transaction_id)
    form = TransactionCategoryForm(
        request.POST or None,
        initial={"description": item.description, "category": item.category_id},
    )
    if request.method == "POST" and form.is_valid():
        form.save(item)
        messages.success(
            request, "Descrição e categoria atualizadas; o valor original foi preservado."
        )
        return redirect("expenses:home")
    return render(request, "expenses/categorize.html", {"form": form, "transaction": item})


@otp_required
@require_http_methods(["GET", "POST"])
def edit_rule(request, rule_id):
    rule = get_object_or_404(CategoryRule, pk=rule_id)
    form = CategoryRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("pattern", "Já existe outra regra com essa descrição normalizada.")
        else:
            messages.success(request, "Regra local atualizada.")
            return redirect("expenses:categories")
    return render(request, "expenses/edit_rule.html", {"form": form, "rule": rule})


@otp_required
@require_http_methods(["GET", "POST"])
def remove_manual_transaction(request, transaction_id):
    item = get_object_or_404(
        ExpenseTransaction, pk=transaction_id, source=ExpenseTransaction.Source.MANUAL
    )
    if request.method == "GET":
        return render(request, "expenses/remove.html", {"transaction": item})
    with transaction.atomic():
        category, transaction_date = item.category, item.transaction_date
        item.delete()
        reconcile_transaction_budgets(item, category, transaction_date)
    messages.success(request, "Lançamento removido e limites recalculados.")
    return redirect("expenses:home")


@otp_required
@require_http_methods(["GET", "POST"])
def budgets(request):
    form = BudgetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, "Não foi possível salvar o limite.")
        else:
            messages.success(request, "Limite mensal salvo e alertas recalculados.")
            return redirect("expenses:budgets")
    summary = []
    for budget in Budget.objects.select_related("category").prefetch_related("alerts"):
        summary.append(
            {
                "budget": budget,
                "spent": monthly_spend(budget),
                "alerts": budget.alerts.filter(active=True),
            }
        )
    return render(request, "expenses/budgets.html", {"form": form, "summary": summary})
