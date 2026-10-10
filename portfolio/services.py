import json
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MONEY_SCALE = Decimal(100)
QUANTITY_SCALE = Decimal(1_000_000)
PRICE_SCALE = Decimal(100_000_000)

BRAPI_SUBTYPES = {
    "stock": "STOCK",
    "fii": "FII",
    "etf": "ETF",
    "bdr": "BDR",
    "unit": "UNIT",
}


def search_brapi_assets(query):
    params = urlencode({"search": query, "limit": 30})
    request = Request(
        f"https://brapi.dev/api/v2/tickers?{params}",
        headers={"Accept": "application/json", "User-Agent": "SavingControl"},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.load(response)

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return []

    assets = []
    for item in payload["results"]:
        if not isinstance(item, dict):
            continue
        brapi_subtype = item.get("subType")
        subtype = BRAPI_SUBTYPES.get(brapi_subtype) if isinstance(brapi_subtype, str) else None
        asset_type = item.get("assetType")
        symbol = item.get("symbol")
        name = item.get("name") or item.get("longName")
        if (
            not subtype
            or not isinstance(asset_type, str)
            or asset_type not in {"stock", "fund", "bdr"}
            or item.get("exchange") != "B3"
            or item.get("currency") != "BRL"
            or item.get("isActive") is False
            or not isinstance(symbol, str)
            or not isinstance(name, str)
        ):
            continue
        symbol, name = symbol.strip(), name.strip()
        if not symbol or not name or len(symbol) > 24 or len(name) > 120:
            continue
        assets.append(
            {
                "symbol": symbol,
                "name": name,
                "market": "BR",
                "asset_class": "VARIABLE_INCOME",
                "subtype": subtype,
                "currency": "BRL",
            }
        )
        if len(assets) == 10:
            break
    return assets


def to_scaled(value: Decimal, scale: Decimal) -> int:
    return int(value * scale)


def from_scaled(value: int, scale: Decimal) -> Decimal:
    return Decimal(value) / scale


@dataclass
class Position:
    quantity: Decimal = Decimal(0)
    cost_basis: Decimal = Decimal(0)
    realized: Decimal = Decimal(0)

    @property
    def average_cost(self):
        return self.cost_basis / self.quantity if self.quantity else Decimal(0)


def calculate_position(operations: Iterable) -> Position:
    """Weighted-average cost, with a chronological short-position guard."""
    position = Position()
    ordered = sorted(operations, key=lambda op: (op.trade_date, op.pk or 2**63))
    for operation in ordered:
        quantity = from_scaled(operation.quantity_u6, QUANTITY_SCALE)
        value = quantity * from_scaled(operation.unit_price_e8, PRICE_SCALE)
        charges = from_scaled(operation.fees_minor + operation.taxes_minor, MONEY_SCALE)
        if operation.side == "BUY":
            position.quantity += quantity
            position.cost_basis += value + charges
        else:
            if quantity > position.quantity:
                raise ValueError("A venda excede a posição disponível na data da operação.")
            position.realized += value - charges - position.average_cost * quantity
            position.cost_basis -= position.average_cost * quantity
            position.quantity -= quantity
    return position
