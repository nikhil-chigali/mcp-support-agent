"""The seed against real Postgres: every row must pass the schema's CHECKs."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from store.models import Customer, Order, OrderItem, Refund, Return
from store.seed import build_world, reset


def count(session: Session, model) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_seed_loads_and_reloads_identically(test_engine):
    world = build_world()
    with Session(test_engine) as session, session.begin():
        first = reset(session, world)
    with Session(test_engine) as session, session.begin():
        second = reset(session, world)
        assert count(session, Customer) == 40
        assert count(session, Order) == 120
        assert count(session, Refund) == 4
        assert count(session, Return) == 1

        # R8 in the data: refunded_cents matches the refund rows behind it.
        mismatched = session.scalars(
            select(OrderItem.id)
            .outerjoin(Refund, Refund.order_item_id == OrderItem.id)
            .group_by(OrderItem.id)
            .having(OrderItem.refunded_cents != func.coalesce(func.sum(Refund.amount_cents), 0))
        ).all()
        assert mismatched == []

    # RESTART IDENTITY: every scenario keeps its order id across resets.
    assert first == second
    assert first[0].order_id == 1
