"""Seed data for the store: a deterministic world shaped by the refund rules.

The seed holds the world only (products, customers, orders, past refunds).
Tickets are not seeded: the eval harness sends each run's tickets through the
admin reset endpoint, so the store never reads eval files and the holdout set
stays sealed.

    world = build_world()               # pure data, same on every call
    reset(session, world)               # truncate + insert
    uv run python -m store.seed         # or: just seed
"""

from .filler import filler_customers
from .load import SeededOrder, reset
from .scenarios import PRODUCTS, SCENARIO_CUSTOMERS
from .spec import ANCHOR, World

TOTAL_CUSTOMERS = 40
TOTAL_ORDERS = 120

__all__ = ["ANCHOR", "SeededOrder", "World", "build_world", "reset"]


def build_world() -> World:
    scenario_orders = sum(len(c.orders) for c in SCENARIO_CUSTOMERS)
    filler = filler_customers(
        n_customers=TOTAL_CUSTOMERS - len(SCENARIO_CUSTOMERS),
        n_orders=TOTAL_ORDERS - scenario_orders,
        skus=[p.sku for p in PRODUCTS],
    )
    return World(products=PRODUCTS, customers=SCENARIO_CUSTOMERS + filler)
