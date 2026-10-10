import json
import time
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from portfolio.forms import AssetForm, InvestmentOperationForm
from portfolio.models import Asset, InvestmentOperation
from portfolio.services import calculate_position, search_brapi_assets


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


class BrapiCatalogTests(TestCase):
    def test_supported_b3_tickers_fill_valid_asset_form_values(self):
        payload = {
            "results": [
                {
                    "symbol": symbol,
                    "name": f"Empresa {symbol}",
                    "exchange": exchange,
                    "currency": currency,
                    "assetType": asset_type,
                    "subType": subtype,
                    "isActive": active,
                }
                for symbol, subtype, asset_type, exchange, currency, active in [
                    ("PETR4", "stock", "stock", "B3", "BRL", True),
                    ("MXRF11", "fii", "fund", "B3", "BRL", True),
                    ("BOVA11", "etf", "fund", "B3", "BRL", True),
                    ("AAPL34", "bdr", "bdr", "B3", "BRL", True),
                    ("TAEE11", "unit", "stock", "B3", "BRL", True),
                    ("FIAG11", "fi-agro", "fund", "B3", "BRL", True),
                    ("OLD3", "stock", "stock", "B3", "BRL", False),
                    ("USST", "stock", "stock", "NASDAQ", "USD", True),
                ]
            ]
        }
        with patch(
            "portfolio.services.urlopen", return_value=BytesIO(json.dumps(payload).encode())
        ) as fetch:
            assets = search_brapi_assets("PETR")

        self.assertEqual(
            [item["subtype"] for item in assets], ["STOCK", "FII", "ETF", "BDR", "UNIT"]
        )
        request = fetch.call_args.args[0]
        self.assertIn("search=PETR", request.full_url)
        self.assertEqual(fetch.call_args.kwargs["timeout"], 5)
        for asset in assets:
            form = AssetForm(
                data={
                    "name": asset["name"],
                    "market": asset["market"],
                    "ticker": asset["symbol"],
                    "asset_class": asset["asset_class"],
                    "subtype": asset["subtype"],
                    "currency": asset["currency"],
                }
            )
            self.assertTrue(form.is_valid(), form.errors)


@override_settings(SECURE_SSL_REDIRECT=False)
class BrapiAssetSearchViewTests(DjangoTestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="owner", password="a-long-test-password"
        )
        device = TOTPDevice.objects.create(user=user, name="default", key="a" * 40)
        self.client.post(
            "/account/login/", {"username": "owner", "password": "a-long-test-password"}
        )
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = time.time()
        self.client.post("/account/verify/", {"token": str(totp.token()).zfill(6)})

    def test_short_query_does_not_call_provider(self):
        with patch("portfolio.views.search_brapi_assets") as search:
            response = self.client.get(reverse("portfolio:asset_search"), {"q": "P"})
        self.assertEqual(response.json(), {"results": []})
        search.assert_not_called()

    def test_long_query_is_rejected(self):
        with patch("portfolio.views.search_brapi_assets") as search:
            response = self.client.get(reverse("portfolio:asset_search"), {"q": "A" * 81})
        self.assertEqual(response.status_code, 400)
        search.assert_not_called()

    def test_search_returns_catalog_and_assets_page_loads_search_script(self):
        asset = {
            "symbol": "PETR4",
            "name": "Petrobras",
            "market": "BR",
            "asset_class": "VARIABLE_INCOME",
            "subtype": "STOCK",
            "currency": "BRL",
        }
        with patch("portfolio.views.search_brapi_assets", return_value=[asset]):
            response = self.client.get(reverse("portfolio:asset_search"), {"q": "PETR"})
        self.assertEqual(response.json(), {"results": [asset]})

        response = self.client.get(reverse("portfolio:assets"))
        self.assertContains(response, 'id="brapi-search"')
        self.assertContains(response, "assets.js")

    def test_provider_failure_returns_gateway_error(self):
        with patch("portfolio.views.search_brapi_assets", side_effect=OSError("unavailable")):
            response = self.client.get(reverse("portfolio:asset_search"), {"q": "PETR"})
        self.assertEqual(response.status_code, 502)


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
        side = str(form["side"])
        self.assertIn('type="radio"', side)
        self.assertIn('value="BUY"', side)
        self.assertIn('value="SELL"', side)

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
