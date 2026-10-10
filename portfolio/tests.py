from datetime import date
from decimal import Decimal
from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from portfolio.forms import InvestmentOperationForm
from portfolio.models import Asset, InvestmentOperation
from portfolio.services import calculate_position


def operation(side, quantity, price, fees=0, day=1):
    return InvestmentOperation(
        side=side,
        trade_date=date(2026, 1, day),
        quantity_u6=quantity,
        unit_price_e8=price,
        fees_minor=fees,
        taxes_minor=0,
    )


class PositionCalculationTests(TestCase):
    def test_weighted_average_and_realized_result_include_fees(self):
        position = calculate_position(
            [
                operation("BUY", 10_000_000, 1_000_000_000, fees=100),
                operation("BUY", 10_000_000, 2_000_000_000, fees=200, day=2),
                operation("SELL", 5_000_000, 2_000_000_000, fees=100, day=3),
            ]
        )
        self.assertEqual(position.quantity, Decimal("15"))
        self.assertEqual(position.cost_basis, Decimal("227.25"))
        self.assertEqual(position.average_cost, Decimal("15.15"))
        self.assertEqual(position.realized, Decimal("23.25"))

    def test_retroactive_sell_cannot_create_a_negative_position(self):
        with self.assertRaisesRegex(ValueError, "excede a posição"):
            calculate_position(
                [
                    operation("BUY", 1_000_000, 1_000_000_000, day=2),
                    operation("SELL", 2_000_000, 1_000_000_000, day=1),
                ]
            )


class OperationFormTests(DjangoTestCase):
    def setUp(self):
        self.asset = Asset.objects.create(
            name="Empresa",
            market="BR",
            ticker="TEST3",
            asset_class="VARIABLE_INCOME",
            subtype="STOCK",
            currency="BRL",
        )

    def form(self, **overrides):
        data = {
            "asset": self.asset.pk,
            "side": "BUY",
            "trade_date": "2026-01-01",
            "quantity": "0.123456",
            "unit_price": "12.12345678",
            "fees": "0.34",
            "taxes": "0.00",
            "currency": "BRL",
            "fx_to_brl": "",
            "note": "",
        }
        return InvestmentOperationForm(data={**data, **overrides})

    def test_values_are_persisted_as_scaled_integers(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.quantity_u6, 123_456)
        self.assertEqual(saved.unit_price_e8, 1_212_345_678)
        self.assertEqual(saved.fees_minor, 34)

    def test_operation_form_labels_are_in_portuguese(self):
        form = self.form()
        self.assertEqual(form.fields["trade_date"].label, "Data da operação")
        self.assertEqual(form.fields["unit_price"].label, "Preço unitário")

    def test_backdated_operation_preserves_all_future_sale_balances(self):
        InvestmentOperation.objects.create(
            asset=self.asset,
            side="BUY",
            trade_date=date(2026, 1, 1),
            quantity_u6=10_000_000,
            unit_price_e8=1_000_000_000,
            currency="BRL",
        )
        InvestmentOperation.objects.create(
            asset=self.asset,
            side="SELL",
            trade_date=date(2026, 1, 3),
            quantity_u6=10_000_000,
            unit_price_e8=1_000_000_000,
            currency="BRL",
        )
        invalid = self.form(
            side="SELL",
            trade_date="2026-01-02",
            quantity="1.000000",
            unit_price="10.00000000",
            fees="0.00",
        )
        self.assertFalse(invalid.is_valid())
        self.assertIn("quantity", invalid.errors)
