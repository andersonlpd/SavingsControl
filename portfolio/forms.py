from datetime import date, datetime, time
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from portfolio.models import (
    Asset,
    FixedIncomeContract,
    FixedIncomeRedemption,
    FixedIncomeValuationOverride,
    IncomeEvent,
    InvestmentOperation,
    MarketQuote,
    PortfolioSnapshot,
)
from portfolio.services import (
    MONEY_SCALE,
    PRICE_SCALE,
    QUANTITY_SCALE,
    calculate_position,
    to_scaled,
)


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ["name", "market", "ticker", "asset_class", "subtype", "currency"]
        labels = {
            "name": "Nome",
            "market": "Mercado",
            "ticker": "Ticker",
            "asset_class": "Classe do ativo",
            "subtype": "Tipo de ativo",
            "currency": "Moeda",
        }

    def clean(self):
        cleaned = super().clean()
        market = cleaned.get("market")
        currency = cleaned.get("currency")
        subtype = cleaned.get("subtype")
        asset_class = cleaned.get("asset_class")
        if market and currency and currency != ("BRL" if market == Asset.Market.BR else "USD"):
            self.add_error("currency", "A moeda deve corresponder ao mercado do ativo.")
        if subtype and asset_class:
            variable = subtype in {Asset.Subtype.STOCK, Asset.Subtype.FII, Asset.Subtype.REIT}
            if variable != (asset_class == Asset.AssetClass.VARIABLE):
                self.add_error("subtype", "O tipo de ativo não corresponde à classe selecionada.")
        if subtype and market:
            if subtype == Asset.Subtype.FII and market != Asset.Market.BR:
                self.add_error("market", "FII deve ser cadastrado no mercado brasileiro.")
            if subtype == Asset.Subtype.REIT and market != Asset.Market.US:
                self.add_error("market", "REIT deve ser cadastrado no mercado dos EUA.")
            fixed_subtypes = {
                Asset.Subtype.TREASURY,
                Asset.Subtype.CDB,
                Asset.Subtype.LCI,
                Asset.Subtype.LCA,
            }
            if subtype in fixed_subtypes and market != Asset.Market.BR:
                self.add_error(
                    "market", "Este tipo de ativo deve ser cadastrado no mercado brasileiro."
                )
        return cleaned


class InvestmentOperationForm(forms.Form):
    asset = forms.ModelChoiceField(
        queryset=Asset.objects.filter(active=True, asset_class=Asset.AssetClass.VARIABLE),
        label="Ativo",
    )
    side = forms.ChoiceField(
        choices=InvestmentOperation.Side.choices,
        label="Operação",
        widget=forms.RadioSelect(attrs={"class": "side-choice"}),
    )
    trade_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data da operação"
    )
    quantity = forms.DecimalField(
        max_digits=18, decimal_places=6, min_value=Decimal("0.000001"), label="Quantidade"
    )
    unit_price = forms.DecimalField(
        max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"), label="Preço unitário"
    )
    fees = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, initial=0, label="Taxas"
    )
    taxes = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, initial=0, label="Impostos"
    )
    currency = forms.ChoiceField(choices=Asset.Currency.choices, label="Moeda")
    fx_to_brl = forms.DecimalField(
        max_digits=18,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
        required=False,
        label="Câmbio para BRL",
    )
    note = forms.CharField(max_length=500, required=False, label="Observação")

    def clean(self):
        cleaned = super().clean()
        asset = cleaned.get("asset")
        if cleaned.get("trade_date") and cleaned["trade_date"] > timezone.localdate():
            self.add_error("trade_date", "Lançamentos de execução não podem usar uma data futura.")
        if asset and cleaned.get("currency") != asset.currency:
            self.add_error("currency", "A moeda deve corresponder à moeda do ativo.")
        if all(
            cleaned.get(key) is not None
            for key in ("asset", "side", "trade_date", "quantity", "unit_price", "fees", "taxes")
        ):
            candidate = self.as_operation()
            existing = list(InvestmentOperation.objects.filter(asset=asset))
            try:
                calculate_position([*existing, candidate])
            except ValueError as error:
                self.add_error("quantity", str(error))
        return cleaned

    def as_operation(self):
        values = self.cleaned_data
        fx = values.get("fx_to_brl")
        return InvestmentOperation(
            asset=values["asset"],
            side=values["side"],
            trade_date=values["trade_date"],
            quantity_u6=to_scaled(values["quantity"], QUANTITY_SCALE),
            unit_price_e8=to_scaled(values["unit_price"], PRICE_SCALE),
            fees_minor=to_scaled(values["fees"], MONEY_SCALE),
            taxes_minor=to_scaled(values["taxes"], MONEY_SCALE),
            currency=values["currency"],
            fx_to_brl_e8=to_scaled(fx, PRICE_SCALE) if fx else None,
            note=values.get("note", ""),
        )

    def save(self):
        operation = self.as_operation()
        with transaction.atomic():
            existing = list(
                InvestmentOperation.objects.select_for_update().filter(asset=operation.asset)
            )
            calculate_position([*existing, operation])
            operation.save()
        return operation


class FixedIncomeContractForm(forms.Form):
    asset = forms.ModelChoiceField(
        queryset=Asset.objects.filter(active=True, asset_class=Asset.AssetClass.FIXED),
        label="Ativo",
    )
    principal = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Valor aplicado"
    )
    application_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data da aplicação"
    )
    maturity_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data de vencimento"
    )
    indexer = forms.ChoiceField(choices=FixedIncomeContract.Indexer.choices, label="Indexador")
    contract_rate = forms.DecimalField(
        max_digits=18, decimal_places=8, min_value=0, label="Taxa contratada"
    )
    rate_unit = forms.ChoiceField(
        choices=FixedIncomeContract.RateUnit.choices,
        initial="ANNUAL",
        label="Periodicidade da taxa",
    )
    liquidity_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Data de liquidez"
    )
    tax_exempt = forms.BooleanField(
        required=False, label="Regime isento (confirmado para este produto)"
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("application_date") and cleaned["application_date"] > timezone.localdate():
            self.add_error("application_date", "A data da aplicação não pode ser futura.")
        if (
            cleaned.get("application_date")
            and cleaned.get("maturity_date")
            and cleaned["maturity_date"] < cleaned["application_date"]
        ):
            self.add_error("maturity_date", "O vencimento não pode anteceder a aplicação.")
        if (
            cleaned.get("tax_exempt")
            and cleaned.get("asset")
            and cleaned["asset"].subtype not in {Asset.Subtype.LCI, Asset.Subtype.LCA}
        ):
            self.add_error(
                "tax_exempt", "Confirme o regime fiscal do produto antes de marcar isenção."
            )
        return cleaned

    def save(self):
        values = self.cleaned_data
        contract = FixedIncomeContract(
            asset=values["asset"],
            principal_minor=to_scaled(values["principal"], MONEY_SCALE),
            application_date=values["application_date"],
            maturity_date=values["maturity_date"],
            indexer=values["indexer"],
            contract_rate_e8=to_scaled(values["contract_rate"], PRICE_SCALE),
            rate_unit=values["rate_unit"],
            liquidity_date=values.get("liquidity_date"),
            tax_exempt=values["tax_exempt"],
        )
        contract.full_clean()
        contract.save()
        return contract


class RedemptionForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Data do resgate")
    gross_amount = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Valor bruto"
    )
    principal_redeemed = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Principal resgatado"
    )
    withheld_tax = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, initial=0, label="Imposto retido"
    )
    fees = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, initial=0, label="Taxas"
    )
    net_amount = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Valor líquido"
    )

    def __init__(self, *args, contract, **kwargs):
        self.contract = contract
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date") and cleaned["date"] > timezone.localdate():
            self.add_error("date", "A data do resgate não pode ser futura.")
        if cleaned.get("date") and cleaned["date"] < self.contract.application_date:
            self.add_error("date", "O resgate não pode anteceder a aplicação.")
        if (
            cleaned.get("net_amount")
            and cleaned.get("gross_amount")
            and cleaned["net_amount"] > cleaned["gross_amount"]
        ):
            self.add_error("net_amount", "O líquido não pode superar o bruto.")
        remaining = self.contract.principal_minor - sum(
            self.contract.redemptions.values_list("principal_redeemed_minor", flat=True)
        )
        principal = cleaned.get("principal_redeemed")
        if principal is not None and to_scaled(principal, MONEY_SCALE) > remaining:
            self.add_error("principal_redeemed", "O resgate excede o principal ainda disponível.")
        return cleaned

    def save(self):
        v = self.cleaned_data
        redemption = FixedIncomeRedemption(
            contract=self.contract,
            date=v["date"],
            gross_amount_minor=to_scaled(v["gross_amount"], MONEY_SCALE),
            principal_redeemed_minor=to_scaled(v["principal_redeemed"], MONEY_SCALE),
            withheld_tax_minor=to_scaled(v["withheld_tax"], MONEY_SCALE),
            fees_minor=to_scaled(v["fees"], MONEY_SCALE),
            net_amount_minor=to_scaled(v["net_amount"], MONEY_SCALE),
        )
        redemption.full_clean()
        redemption.save()
        return redemption


class IncomeEventForm(forms.Form):
    asset = forms.ModelChoiceField(queryset=Asset.objects.filter(active=True), label="Ativo")
    kind = forms.ChoiceField(choices=IncomeEvent.Kind.choices, label="Tipo do provento")
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data do pagamento"
    )
    gross_amount = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Valor bruto"
    )
    withheld_tax = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, initial=0, label="Imposto retido"
    )
    net_amount = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Valor líquido"
    )
    currency = forms.ChoiceField(choices=Asset.Currency.choices, label="Moeda")
    fx_to_brl = forms.DecimalField(
        max_digits=18,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
        required=False,
        label="Câmbio para BRL",
    )
    note = forms.CharField(max_length=500, required=False, label="Observação")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("payment_date") and cleaned["payment_date"] > timezone.localdate():
            self.add_error("payment_date", "A data de pagamento não pode ser futura.")
        gross, net = cleaned.get("gross_amount"), cleaned.get("net_amount")
        if gross and net and net > gross:
            self.add_error("net_amount", "O valor líquido não pode superar o bruto.")
        withheld = cleaned.get("withheld_tax")
        if gross and withheld and withheld > gross:
            self.add_error("withheld_tax", "O imposto retido não pode superar o valor bruto.")
        if (
            cleaned.get("asset")
            and cleaned.get("currency")
            and cleaned["currency"] != cleaned["asset"].currency
        ):
            self.add_error("currency", "A moeda deve corresponder à moeda do ativo.")
        asset, kind = cleaned.get("asset"), cleaned.get("kind")
        if asset and kind == IncomeEvent.Kind.FIXED and asset.asset_class != Asset.AssetClass.FIXED:
            self.add_error("asset", "Rendimento de renda fixa exige ativo de renda fixa.")
        if (
            asset
            and kind in {IncomeEvent.Kind.DIVIDEND, IncomeEvent.Kind.JCP}
            and asset.asset_class != Asset.AssetClass.VARIABLE
        ):
            self.add_error("asset", "Dividendo/JCP exige ativo de renda variável.")
        return cleaned

    def save(self):
        v = self.cleaned_data
        event = IncomeEvent(
            asset=v["asset"],
            kind=v["kind"],
            payment_date=v["payment_date"],
            gross_amount_minor=to_scaled(v["gross_amount"], MONEY_SCALE),
            withheld_tax_minor=to_scaled(v["withheld_tax"], MONEY_SCALE),
            net_amount_minor=to_scaled(v["net_amount"], MONEY_SCALE),
            currency=v["currency"],
            fx_to_brl_e8=to_scaled(v["fx_to_brl"], PRICE_SCALE) if v.get("fx_to_brl") else None,
            note=v["note"],
        )
        event.full_clean()
        event.save()
        return event


class ManualQuoteForm(forms.Form):
    asset = forms.ModelChoiceField(queryset=Asset.objects.filter(active=True), label="Ativo")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Data da cotação")
    price = forms.DecimalField(
        max_digits=18, decimal_places=8, min_value=Decimal("0.00000001"), label="Preço unitário"
    )

    def clean_date(self):
        quote_date = self.cleaned_data["date"]
        if quote_date > timezone.localdate():
            raise ValidationError("A data da cotação não pode ser futura.")
        return quote_date

    def save(self):
        v = self.cleaned_data
        return MarketQuote.objects.create(
            asset=v["asset"],
            observed_at=timezone.make_aware(datetime.combine(v["date"], time.max)),
            price_e8=to_scaled(v["price"], PRICE_SCALE),
            currency=v["asset"].currency,
            source="MANUAL",
            manual=True,
        )


class ManualValuationForm(forms.Form):
    observed_at = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data do saldo informado"
    )
    gross_amount = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Saldo bruto"
    )

    def clean_observed_at(self):
        observed_at = self.cleaned_data["observed_at"]
        if observed_at > timezone.localdate():
            raise ValidationError("A data da avaliação não pode ser futura.")
        return observed_at

    def save(self, contract):
        v = self.cleaned_data
        return FixedIncomeValuationOverride.objects.create(
            contract=contract,
            observed_at=v["observed_at"],
            gross_amount_minor=to_scaled(v["gross_amount"], MONEY_SCALE),
        )


class SnapshotForm(forms.Form):
    month = forms.CharField(
        label="Mês de referência", max_length=7, widget=forms.TextInput(attrs={"type": "month"})
    )
    value = forms.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0.01"), label="Patrimônio total (R$)"
    )

    def clean_month(self):
        raw = self.cleaned_data["month"]
        try:
            year, month = (int(part) for part in raw.split("-"))
            result = date(year, month, 1)
        except (ValueError, TypeError):
            raise ValidationError("Informe um mês válido.") from None
        if result >= timezone.localdate().replace(day=1):
            raise ValidationError("Snapshots manuais devem se referir a um mês já encerrado.")
        return result

    def save(self):
        from calendar import monthrange

        month = self.cleaned_data["month"]
        return PortfolioSnapshot.objects.create(
            snapshot_date=month.replace(day=monthrange(month.year, month.month)[1]),
            scope=PortfolioSnapshot.Scope.TOTAL,
            value_minor_brl=to_scaled(self.cleaned_data["value"], MONEY_SCALE),
            source=PortfolioSnapshot.Source.MANUAL,
        )
