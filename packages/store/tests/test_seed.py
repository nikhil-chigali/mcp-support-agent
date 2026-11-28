"""The seeded world, checked as plain data. These need no database."""

from datetime import timedelta

import pytest

from store.seed import ANCHOR, build_world
from store.seed.scenarios import PRODUCTS
from store.seed.spec import days_before, due

WORLD = build_world()
ORDERS = [o for c in WORLD.customers for o in c.orders]
SCENARIOS = {o.scenario: o for o in ORDERS if o.scenario}
PRICES = {p.sku: p.price_cents for p in PRODUCTS}


def test_world_is_deterministic():
    assert build_world() == WORLD


def test_world_has_the_designed_size():
    assert len(WORLD.customers) == 40
    assert len(ORDERS) == 120


def test_keys_are_unique():
    emails = [c.email for c in WORLD.customers]
    skus = [p.sku for p in WORLD.products]
    keys = [o.scenario for o in ORDERS if o.scenario]
    assert len(set(emails)) == len(emails)
    assert len(set(skus)) == len(skus)
    assert len(set(keys)) == len(keys)


def test_three_customers_share_the_first_name_jane():
    assert sum(c.name.startswith("Jane ") for c in WORLD.customers) == 3


@pytest.mark.parametrize(
    ("scenario", "days"),
    [
        ("r2-day-30", 30),
        ("r3-day-30", 30),
        ("day-31-skillet", 31),
        ("r3-day-31", 31),
        ("r5-day-90", 90),
        ("r5-day-91", 91),
    ],
)
def test_delivery_boundaries_sit_where_their_names_say(scenario, days):
    assert SCENARIOS[scenario].timeline.delivered_at == days_before(days)


@pytest.mark.parametrize(("scenario", "overdue"), [("r4-overdue-10", 10), ("r4-overdue-9", 9)])
def test_r4_boundaries_sit_where_their_names_say(scenario, overdue):
    timeline = SCENARIOS[scenario].timeline
    assert timeline.expected_by == due(-overdue)
    assert timeline.delivered_at is None


def test_price_thresholds_are_exact():
    assert PRICES["KETTLE"] == 4999  # just under the $50 return threshold
    assert PRICES["KNIFE"] == 5000
    assert PRICES["MIXER"] == 20000  # exactly the $200 approval threshold
    assert PRICES["ESPRESSO"] * 9 // 10 < 20000 < PRICES["ESPRESSO"]


def test_prior_refunds_obey_r7_and_r8():
    for o in ORDERS:
        for line in o.lines:
            assert sum(r.amount_cents for r in line.prior_refunds) <= line.qty * PRICES[line.sku]
            for refund in line.prior_refunds:
                assert refund.amount_cents <= 20000 or refund.approved_by


def test_everything_happens_before_the_anchor():
    for o in ORDERS:
        t = o.timeline
        stamps = [t.placed_at, t.shipped_at, t.delivered_at, t.cancelled_at]
        assert all(s <= ANCHOR for s in stamps if s)
        if any(line.prior_refunds for line in o.lines):
            # load.py stamps prior refunds a day after delivery or cancellation.
            assert (t.delivered_at or t.cancelled_at) + timedelta(days=1) < ANCHOR
