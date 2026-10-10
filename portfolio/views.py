from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django_otp.decorators import otp_required

from portfolio.forms import (
    AssetForm,
    FixedIncomeContractForm,
    IncomeEventForm,
    InvestmentOperationForm,
    ManualQuoteForm,
    ManualValuationForm,
    RedemptionForm,
    SnapshotForm,
)
from portfolio.models import (
    Asset,
    ExchangeRate,
    FixedIncomeContract,
    IncomeEvent,
    InvestmentOperation,
    PortfolioSnapshot,
)
from portfolio.services import (
    PRICE_SCALE,
    calculate_position,
    from_scaled,
)


@otp_required
def portfolio_home(request):
    positions = []
    for asset in Asset.objects.filter(asset_class=Asset.AssetClass.VARIABLE).prefetch_related(
        "operations", "quotes"
    ):
        position = calculate_position(asset.operations.all())
        quote = asset.quotes.first()
        market_value = None
        market_value_brl = None
        exchange_rate = None
        if quote:
            market_value = position.quantity * from_scaled(quote.price_e8, PRICE_SCALE)
            if asset.currency == Asset.Currency.BRL:
                market_value_brl = market_value
            else:
                exchange_rate = ExchangeRate.objects.filter(
                    date__lte=timezone.localdate(), base="USD", quote="BRL"
                ).first()
                if exchange_rate:
                    market_value_brl = market_value * from_scaled(
                        exchange_rate.rate_e8, PRICE_SCALE
                    )
        positions.append(
            {
                "asset": asset,
                "position": position,
                "quote": quote,
                # ponytail: three-day age catches weekends; use holiday data before auto-prices.
                "stale_quote": bool(
                    quote and timezone.localdate() - quote.observed_at.date() > timedelta(days=3)
                ),
                "market_value": market_value,
                "market_value_brl": market_value_brl,
                "exchange_rate": exchange_rate,
                "unrealized": market_value - position.cost_basis
                if market_value is not None
                else None,
            }
        )
    fixed_contracts = FixedIncomeContract.objects.select_related("asset").prefetch_related(
        "redemptions", "valuations"
    )
    total_market_brl = sum(
        (row["market_value_brl"] for row in positions if row["market_value_brl"] is not None),
        Decimal(0),
    )
    total_market_usd = sum(
        (
            row["market_value"]
            for row in positions
            if row["asset"].currency == Asset.Currency.USD and row["market_value"] is not None
        ),
        Decimal(0),
    )
    latest_snapshot = PortfolioSnapshot.objects.filter(scope=PortfolioSnapshot.Scope.TOTAL).last()
    context = {
        "positions": positions,
        "fixed_contracts": fixed_contracts,
        "total_market_brl": total_market_brl,
        "total_market_usd": total_market_usd,
        "latest_snapshot": latest_snapshot,
        "recent_income": IncomeEvent.objects.select_related("asset")[:5],
        "recent_operations": InvestmentOperation.objects.select_related("asset")[:8],
    }
    return render(request, "portfolio/index.html", context)


@otp_required
@require_http_methods(["GET", "POST"])
def assets(request):
    form = AssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("ticker", "Já existe um ticker igual nesse mercado.")
        else:
            messages.success(request, "Ativo cadastrado.")
            return redirect("portfolio:assets")
    return render(request, "portfolio/assets.html", {"form": form, "assets": Asset.objects.all()})


@otp_required
@require_http_methods(["GET", "POST"])
def operations(request):
    form = InvestmentOperationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except (ValueError, IntegrityError):
            form.add_error("quantity", "A operação conflita com o saldo cronológico atual.")
        else:
            messages.success(request, "Operação registrada; a posição foi recalculada pelo ledger.")
            return redirect("portfolio:operations")
    return render(
        request,
        "portfolio/operations.html",
        {
            "form": form,
            "operations": InvestmentOperation.objects.select_related("asset")[:100],
        },
    )


@otp_required
@require_http_methods(["GET", "POST"])
def fixed_income(request):
    form = FixedIncomeContractForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, "Não foi possível salvar o contrato.")
        else:
            messages.success(request, "Lote de renda fixa registrado.")
            return redirect("portfolio:fixed_income")
    return render(
        request,
        "portfolio/fixed_income.html",
        {
            "form": form,
            "contracts": FixedIncomeContract.objects.select_related("asset").prefetch_related(
                "redemptions", "valuations"
            ),
        },
    )


@otp_required
@require_POST
def redeem_fixed_income(request, contract_id):
    contract = get_object_or_404(FixedIncomeContract, pk=contract_id)
    form = RedemptionForm(request.POST, contract=contract)
    if form.is_valid():
        try:
            form.save()
        except (ValueError, IntegrityError):
            form.add_error(None, "O resgate ultrapassa o principal restante.")
        else:
            messages.success(request, "Resgate registrado.")
            return redirect("portfolio:fixed_income")
    return render(
        request, "portfolio/redemption.html", {"form": form, "contract": contract}, status=400
    )


@otp_required
@require_POST
def fixed_income_valuation(request, contract_id):
    contract = get_object_or_404(FixedIncomeContract, pk=contract_id)
    form = ManualValuationForm(request.POST)
    if form.is_valid():
        form.save(contract)
        messages.success(
            request,
            "Saldo bruto informado manualmente; impostos continuam sem estimativa automática.",
        )
    else:
        messages.error(request, "Data ou saldo informado inválido.")
    return redirect("portfolio:fixed_income")


@otp_required
@require_http_methods(["GET", "POST"])
def income(request):
    form = IncomeEventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Provento registrado.")
        return redirect("portfolio:income")
    return render(
        request,
        "portfolio/income.html",
        {
            "form": form,
            "events": IncomeEvent.objects.select_related("asset")[:100],
        },
    )


@otp_required
@require_http_methods(["GET", "POST"])
def quotes(request):
    form = ManualQuoteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, "Já existe uma cotação manual para esse ativo e horário.")
        else:
            messages.success(request, "Cotação manual registrada com sua data de referência.")
            return redirect("portfolio:quotes")
    assets = Asset.objects.prefetch_related("quotes")
    return render(request, "portfolio/quotes.html", {"form": form, "assets": assets})


@otp_required
@require_http_methods(["GET", "POST"])
def snapshots(request):
    form = SnapshotForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error("month", "Já existe um snapshot para esse mês.")
        else:
            messages.success(
                request, "Snapshot histórico salvo; nenhum histórico por classe foi inferido."
            )
            return redirect("portfolio:snapshots")
    return render(
        request,
        "portfolio/snapshots.html",
        {
            "form": form,
            "snapshots": PortfolioSnapshot.objects.filter(scope=PortfolioSnapshot.Scope.TOTAL),
        },
    )
