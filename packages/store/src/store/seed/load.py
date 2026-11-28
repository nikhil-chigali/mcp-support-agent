"""Write a World into the store database: truncate everything, then insert.

The same reset() will back POST /v1/admin/reset, which also inserts the eval
run's tickets. Rows are inserted in a fixed order after RESTART IDENTITY, so a
scenario's order id is the same on every run.

Timestamps are always set explicitly. The server_default now() on created_at
would stamp seeded rows with the real clock, months after ANCHOR.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from store.models import Base, Customer, Order, OrderItem, Product, Refund, Return

from .spec import OrderSpec, PriorRefund, World

ALL_TABLES = ", ".join(table.name for table in Base.metadata.sorted_tables)


@dataclass(frozen=True)
class SeededOrder:
    """Where a scenario landed: what an eval ticket author needs to know."""

    scenario: str
    order_id: int
    email: str
    note: str


def reset(session: Session, world: World) -> list[SeededOrder]:
    session.execute(text(f"TRUNCATE {ALL_TABLES} RESTART IDENTITY CASCADE"))
    return _write(session, world)


def _write(session: Session, world: World) -> list[SeededOrder]:
    products = {
        p.sku: Product(sku=p.sku, name=p.name, price_cents=p.price_cents) for p in world.products
    }
    session.add_all(products.values())
    session.flush()

    seeded = []
    for spec in world.customers:
        first_order = min(o.timeline.placed_at for o in spec.orders)
        customer = Customer(
            name=spec.name, email=spec.email, created_at=first_order - timedelta(days=30)
        )
        session.add(customer)
        session.flush()
        for order_spec in spec.orders:
            order = _write_order(session, customer.id, order_spec, products)
            if order_spec.scenario:
                seeded.append(
                    SeededOrder(order_spec.scenario, order.id, spec.email, order_spec.note)
                )
    return seeded


def _write_order(
    session: Session, customer_id: int, spec: OrderSpec, products: dict[str, Product]
) -> Order:
    t = spec.timeline
    order = Order(
        customer_id=customer_id,
        status=t.status,
        placed_at=t.placed_at,
        shipped_at=t.shipped_at,
        delivered_at=t.delivered_at,
        expected_by=t.expected_by,
        cancelled_at=t.cancelled_at,
    )
    session.add(order)
    session.flush()

    # A prior refund happened the day after delivery or cancellation.
    refunded_at = (t.delivered_at or t.cancelled_at or t.placed_at) + timedelta(days=1)
    for line in spec.lines:
        product = products[line.sku]
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            qty=line.qty,
            unit_price_cents=product.price_cents,
            refunded_cents=sum(r.amount_cents for r in line.prior_refunds),
        )
        session.add(item)
        session.flush()
        for n, prior in enumerate(line.prior_refunds, start=1):
            _write_refund(session, item, prior, f"seed-{item.id}-{n}", refunded_at)
    return order


def _write_refund(
    session: Session, item: OrderItem, prior: PriorRefund, key: str, at: datetime
) -> None:
    body = {"order_item_id": item.id, "amount_cents": prior.amount_cents, "reason": prior.reason}
    refund = Refund(
        order_item_id=item.id,
        amount_cents=prior.amount_cents,
        method=prior.method,
        reason=prior.reason,
        rule=prior.rule,
        approved_by=prior.approved_by,
        idempotency_key=key,
        request_hash=hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
        created_at=at,
    )
    session.add(refund)
    session.flush()
    if prior.return_status:
        session.add(
            Return(
                order_item_id=item.id,
                refund_id=refund.id,
                status=prior.return_status,
                created_at=at,
            )
        )
