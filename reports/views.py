from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET
from django_otp.decorators import otp_required

from expenses.models import Budget, ExpenseTransaction
from expenses.services import monthly_spend
from portfolio.models import IncomeEvent, MarketQuote, PortfolioSnapshot


@otp_required
@require_GET
def dashboard(request):
    today = timezone.localdate()
    posted = ExpenseTransaction.objects.filter(
        transaction_date__year=today.year,
        transaction_date__month=today.month,
        status=ExpenseTransaction.Status.POSTED,
    )
    brl = posted.filter(currency="BRL")
    debit_total = (
        brl.filter(direction=ExpenseTransaction.Direction.DEBIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    credit_total = (
        brl.filter(direction=ExpenseTransaction.Direction.CREDIT).aggregate(
            total=Sum("amount_minor")
        )["total"]
        or 0
    )
    monthly_total = debit_total - credit_total
    category_amounts = defaultdict(int)
    for row in brl.values("category__name", "direction").annotate(total=Sum("amount_minor")):
        factor = 1 if row["direction"] == ExpenseTransaction.Direction.DEBIT else -1
        category_amounts[row["category__name"]] += factor * row["total"]
    category_totals = sorted(
        ({"category__name": name, "total": total} for name, total in category_amounts.items()),
        key=lambda item: item["total"],
        reverse=True,
    )[:5]
    budgets = []
    for budget in Budget.objects.filter(
        month__year=today.year, month__month=today.month
    ).select_related("category"):
        budgets.append(
            {
                "budget": budget,
                "spent": monthly_spend(budget),
                "alerts": budget.alerts.filter(active=True),
            }
        )
    quotes = MarketQuote.objects.select_related("asset").order_by("-observed_at")[:5]
    chart_snapshots = PortfolioSnapshot.objects.filter(
        scope=PortfolioSnapshot.Scope.TOTAL
    ).order_by("snapshot_date")
    snapshots = PortfolioSnapshot.objects.filter(scope=PortfolioSnapshot.Scope.TOTAL).order_by(
        "-snapshot_date"
    )[:6]
    income = IncomeEvent.objects.select_related("asset").order_by("-payment_date")[:5]
    return render(
        request,
        "reports/dashboard.html",
        {
            "today": today,
            "monthly_total": monthly_total,
            "top_categories": category_totals,
            "budgets": budgets,
            "quotes": quotes,
            "snapshots": snapshots,
            "income": income,
            "chart_data": [
                {
                    "date": snap.snapshot_date.isoformat(),
                    "value": str(Decimal(snap.value_minor_brl) / Decimal(100)),
                }
                for snap in chart_snapshots
            ],
        },
    )


@otp_required
@require_GET
def portfolio_report(request):
    start = request.GET.get("from")
    end = request.GET.get("to")
    start_date = parse_date(f"{start}-01") if start else None
    end_date = parse_date(f"{end}-01") if end else None
    if (start and not start_date) or (end and not end_date):
        return JsonResponse({"error": "Use o formato YYYY-MM para from e to."}, status=400)
    if start_date and end_date and start_date > end_date:
        return JsonResponse(
            {"error": "O início deve anteceder ou corresponder ao fim."}, status=400
        )
    snapshots = PortfolioSnapshot.objects.filter(scope=PortfolioSnapshot.Scope.TOTAL)
    if start_date:
        snapshots = snapshots.filter(snapshot_date__gte=start_date)
    if end_date:
        snapshots = snapshots.filter(snapshot_date__year__lte=end_date.year).exclude(
            snapshot_date__year=end_date.year, snapshot_date__month__gt=end_date.month
        )
    return JsonResponse(
        {
            "series": [
                {
                    "date": item.snapshot_date.isoformat(),
                    "value_brl": str(Decimal(item.value_minor_brl) / Decimal(100)),
                }
                for item in snapshots
            ],
            "method": (
                "Snapshots históricos totais; nenhuma série por classe foi "
                "reconstruída retroativamente."
            ),
        }
    )
