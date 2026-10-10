from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    active = models.BooleanField(default=True)
    group = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class CategoryRule(models.Model):
    pattern = models.CharField(max_length=160, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="rules")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pattern"]

    def save(self, *args, **kwargs):
        from expenses.services import normalize_description

        self.pattern = normalize_description(self.pattern)
        super().save(*args, **kwargs)


class ExpenseTransaction(models.Model):
    class Source(models.TextChoices):
        PLUGGY = "PLUGGY", "Pluggy"
        MANUAL = "MANUAL", "Manual"

    class Direction(models.TextChoices):
        DEBIT = "DEBIT", "Despesa"
        CREDIT = "CREDIT", "Crédito/estorno"

    class Status(models.TextChoices):
        POSTED = "POSTED", "Confirmada"
        PENDING = "PENDING", "Pendente"
        UNKNOWN = "UNKNOWN", "Desconhecido"

    class Currency(models.TextChoices):
        BRL = "BRL", "BRL"
        USD = "USD", "USD"

    source = models.CharField(max_length=8, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=160, null=True, blank=True)
    account_ref = models.CharField(max_length=32, blank=True)
    transaction_date = models.DateField()
    description = models.CharField(max_length=240)
    amount_minor = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.BRL)
    direction = models.CharField(max_length=8, choices=Direction.choices, default=Direction.DEBIT)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.POSTED)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="transactions"
    )
    category_source = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "account_ref", "external_id"],
                condition=Q(source="PLUGGY") & Q(external_id__isnull=False),
                name="expenses_external_transaction_unique",
            )
        ]


class Budget(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="budgets")
    month = models.DateField(help_text="Primeiro dia do mês")
    limit_minor_brl = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["-month", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "month"], name="expenses_budget_category_month_unique"
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.month and self.month.day != 1:
            raise ValidationError({"month": "Use o primeiro dia do mês selecionado."})


class BudgetAlert(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="alerts")
    threshold = models.PositiveSmallIntegerField(choices=[(80, "80%"), (100, "100%")])
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["threshold"]
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "threshold"], name="expenses_budget_alert_unique"
            )
        ]
