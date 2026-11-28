"""The shapes a seeded world is described in, and the clock it is described against.

Every date in the seed is an offset from ANCHOR, never from the real clock, so
the data is identical on every run. Eval runs pin the store's clock
(FROZEN_NOW) to the same instant, and eval tickets are filed at or near it.
Times sit at noon UTC so that "N days before" lands on the same calendar day
in every timezone.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from store.models import OrderStatus, RefundMethod, ReturnStatus

ANCHOR = datetime(2026, 6, 1, 12, tzinfo=UTC)


def days_before(days: int) -> datetime:
    return ANCHOR - timedelta(days=days)


def due(days_from_anchor: int) -> date:
    """An expected_by date; negative means it is already overdue at ANCHOR."""
    return (ANCHOR + timedelta(days=days_from_anchor)).date()


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int


@dataclass(frozen=True)
class PriorRefund:
    """A refund that already happened before the seeded "now"."""

    amount_cents: int
    rule: str
    reason: str
    method: RefundMethod = RefundMethod.ORIGINAL_PAYMENT
    approved_by: str | None = None
    # Set when the rule needed the item back, so a return row exists too.
    return_status: ReturnStatus | None = None


@dataclass(frozen=True)
class Line:
    sku: str
    qty: int = 1
    prior_refunds: tuple[PriorRefund, ...] = ()


@dataclass(frozen=True)
class Timeline:
    """An order's status plus the timestamps that prove it (the orders CHECKs)."""

    status: OrderStatus
    placed_at: datetime
    expected_by: date
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None


@dataclass(frozen=True)
class OrderSpec:
    timeline: Timeline
    lines: tuple[Line, ...]
    scenario: str | None = None  # stable key that eval tickets refer to; None for filler
    note: str = ""


@dataclass(frozen=True)
class CustomerSpec:
    name: str
    email: str
    orders: tuple[OrderSpec, ...]


@dataclass(frozen=True)
class World:
    products: tuple[Product, ...]
    customers: tuple[CustomerSpec, ...]


# --- Timelines, one per order status ----------------------------------------


def placed(days_ago: int) -> Timeline:
    at = days_before(days_ago)
    return Timeline(OrderStatus.PLACED, placed_at=at, expected_by=(at + timedelta(days=7)).date())


def in_transit(shipped_days_ago: int, due_in_days: int) -> Timeline:
    shipped = days_before(shipped_days_ago)
    return Timeline(
        OrderStatus.SHIPPED,
        placed_at=shipped - timedelta(days=1),
        shipped_at=shipped,
        expected_by=due(due_in_days),
    )


def delivered(days_ago: int) -> Timeline:
    at = days_before(days_ago)
    return Timeline(
        OrderStatus.DELIVERED,
        placed_at=at - timedelta(days=5),
        shipped_at=at - timedelta(days=3),
        delivered_at=at,
        expected_by=(at + timedelta(days=2)).date(),
    )


def cancelled(days_ago: int) -> Timeline:
    at = days_before(days_ago)
    return Timeline(
        OrderStatus.CANCELLED,
        placed_at=at - timedelta(days=1),
        cancelled_at=at,
        expected_by=(at + timedelta(days=6)).date(),
    )


def lost(shipped_days_ago: int, due_in_days: int) -> Timeline:
    shipped = days_before(shipped_days_ago)
    return Timeline(
        OrderStatus.LOST,
        placed_at=shipped - timedelta(days=1),
        shipped_at=shipped,
        expected_by=due(due_in_days),
    )
