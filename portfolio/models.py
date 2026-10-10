from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Asset(models.Model):
    class Market(models.TextChoices):
        BR = "BR", "Brasil"
        US = "US", "Estados Unidos"

    class AssetClass(models.TextChoices):
        FIXED = "FIXED_INCOME", "Renda fixa"
        VARIABLE = "VARIABLE_INCOME", "Renda variável"

    class Subtype(models.TextChoices):
        STOCK = "STOCK", "Ação"
        FII = "FII", "FII"
        REIT = "REIT", "REIT"
        TREASURY = "TREASURY", "Tesouro Direto"
        CDB = "CDB", "CDB"
        LCI = "LCI", "LCI"
        LCA = "LCA", "LCA"

    class Currency(models.TextChoices):
        BRL = "BRL", "BRL"
        USD = "USD", "USD"

    name = models.CharField(max_length=120)
    market = models.CharField(max_length=2, choices=Market.choices)
    ticker = models.CharField(max_length=24, blank=True)
    asset_class = models.CharField(max_length=20, choices=AssetClass.choices)
    subtype = models.CharField(max_length=12, choices=Subtype.choices)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    active = models.BooleanField(default=True)
    quote_source = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name", "ticker"]
        constraints = [
            models.UniqueConstraint(
                fields=["market", "ticker"],
                condition=~Q(ticker=""),
                name="portfolio_unique_ticker_market",
            )
        ]

    def save(self, *args, **kwargs):
        self.ticker = self.ticker.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticker or self.name


class InvestmentOperation(models.Model):
    class Side(models.TextChoices):
        BUY = "BUY", "Compra"
        SELL = "SELL", "Venda"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="operations")
    side = models.CharField(max_length=4, choices=Side.choices)
    trade_date = models.DateField()
    quantity_u6 = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    unit_price_e8 = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    fees_minor = models.PositiveBigIntegerField(default=0)
    taxes_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3, choices=Asset.Currency.choices)
    fx_to_brl_e8 = models.PositiveBigIntegerField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trade_date", "pk"]


class FixedIncomeContract(models.Model):
    class Indexer(models.TextChoices):
        CDI = "CDI_PERCENT", "% do CDI"
        IPCA = "IPCA_PLUS", "IPCA+"
        SELIC = "SELIC", "Selic"
        FIXED = "FIXED", "Prefixado"

    class RateUnit(models.TextChoices):
        ANNUAL = "ANNUAL", "Ao ano"
        DAILY = "DAILY", "Ao dia"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="contracts")
    principal_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    application_date = models.DateField()
    maturity_date = models.DateField()
    indexer = models.CharField(max_length=16, choices=Indexer.choices)
    contract_rate_e8 = models.PositiveBigIntegerField()
    rate_unit = models.CharField(max_length=8, choices=RateUnit.choices, default=RateUnit.ANNUAL)
    liquidity_date = models.DateField(null=True, blank=True)
    tax_exempt = models.BooleanField(default=False)

    class Meta:
        ordering = ["maturity_date", "pk"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.maturity_date
            and self.application_date
            and self.maturity_date < self.application_date
        ):
            raise ValidationError({"maturity_date": "O vencimento não pode anteceder a aplicação."})
        if self.asset_id and self.asset.asset_class != Asset.AssetClass.FIXED:
            raise ValidationError({"asset": "O contrato deve usar um ativo de renda fixa."})


class FixedIncomeRedemption(models.Model):
    contract = models.ForeignKey(
        FixedIncomeContract, on_delete=models.PROTECT, related_name="redemptions"
    )
    date = models.DateField()
    gross_amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    principal_redeemed_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    withheld_tax_minor = models.PositiveBigIntegerField(default=0)
    fees_minor = models.PositiveBigIntegerField(default=0)
    net_amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["date", "pk"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.date and self.contract_id and self.date < self.contract.application_date:
            raise ValidationError({"date": "O resgate não pode anteceder a aplicação."})
        if (
            self.net_amount_minor
            and self.gross_amount_minor
            and self.net_amount_minor > self.gross_amount_minor
        ):
            raise ValidationError({"net_amount_minor": "O valor líquido não pode superar o bruto."})
        already_redeemed = (
            sum(
                self.contract.redemptions.exclude(pk=self.pk).values_list(
                    "principal_redeemed_minor", flat=True
                )
            )
            if self.contract_id
            else 0
        )
        if (
            self.contract_id
            and already_redeemed + (self.principal_redeemed_minor or 0)
            > self.contract.principal_minor
        ):
            raise ValidationError(
                {"principal_redeemed_minor": "O resgate excede o principal ainda disponível."}
            )


class FixedIncomeValuationOverride(models.Model):
    contract = models.ForeignKey(
        FixedIncomeContract, on_delete=models.CASCADE, related_name="valuations"
    )
    observed_at = models.DateField()
    gross_amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    source = models.CharField(max_length=20, default="BROKER_MANUAL")

    class Meta:
        ordering = ["-observed_at"]


class IncomeEvent(models.Model):
    class Kind(models.TextChoices):
        DIVIDEND = "DIVIDEND", "Dividendo"
        JCP = "JCP", "JCP"
        FIXED = "FIXED_INCOME", "Rendimento de renda fixa"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="income_events")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    payment_date = models.DateField()
    gross_amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    withheld_tax_minor = models.PositiveBigIntegerField(default=0)
    net_amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    currency = models.CharField(max_length=3, choices=Asset.Currency.choices)
    fx_to_brl_e8 = models.PositiveBigIntegerField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-payment_date", "-pk"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.asset_id
            and self.kind == self.Kind.FIXED
            and self.asset.asset_class != Asset.AssetClass.FIXED
        ):
            raise ValidationError({"asset": "Rendimento de renda fixa exige ativo de renda fixa."})
        if (
            self.asset_id
            and self.kind in {self.Kind.DIVIDEND, self.Kind.JCP}
            and self.asset.asset_class != Asset.AssetClass.VARIABLE
        ):
            raise ValidationError({"asset": "Dividendo/JCP exige ativo de renda variável."})
        if (
            self.withheld_tax_minor
            and self.gross_amount_minor
            and self.withheld_tax_minor > self.gross_amount_minor
        ):
            raise ValidationError(
                {"withheld_tax_minor": "O imposto retido não pode superar o valor bruto."}
            )
        if (
            self.net_amount_minor
            and self.gross_amount_minor
            and self.net_amount_minor > self.gross_amount_minor
        ):
            raise ValidationError({"net_amount_minor": "O valor líquido não pode superar o bruto."})


class MarketQuote(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="quotes")
    observed_at = models.DateTimeField()
    price_e8 = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    currency = models.CharField(max_length=3, choices=Asset.Currency.choices)
    source = models.CharField(max_length=80)
    manual = models.BooleanField(default=False)

    class Meta:
        ordering = ["-observed_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "observed_at", "source"], name="portfolio_quote_source_time_unique"
            )
        ]


class ExchangeRate(models.Model):
    date = models.DateField()
    base = models.CharField(max_length=3, default="USD")
    quote = models.CharField(max_length=3, default="BRL")
    rate_e8 = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    source = models.CharField(max_length=30, default="BCB_PTAX")
    observed_at = models.DateTimeField()

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "base", "quote", "source"], name="portfolio_exchange_rate_unique"
            )
        ]


class PortfolioSnapshot(models.Model):
    class Scope(models.TextChoices):
        TOTAL = "TOTAL", "Total"
        FIXED = "FIXED_INCOME", "Renda fixa"
        VARIABLE = "VARIABLE_INCOME", "Renda variável"

    class Source(models.TextChoices):
        MANUAL = "MANUAL_SHEET", "Manual/planilha"
        APP = "APP", "Aplicação"

    snapshot_date = models.DateField()
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.TOTAL)
    value_minor_brl = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["snapshot_date", "scope"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "scope"], name="portfolio_snapshot_date_scope_unique"
            )
        ]
