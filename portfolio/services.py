from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

MONEY_SCALE = Decimal(100)
QUANTITY_SCALE = Decimal(1_000_000)
PRICE_SCALE = Decimal(100_000_000)


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
