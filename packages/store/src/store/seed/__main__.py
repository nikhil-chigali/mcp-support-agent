"""`python -m store.seed`: wipe the database at STORE_DATABASE_URL and seed it.

Prints where each scenario landed (order id, customer email), which is what
you need when writing an eval ticket against it.
"""

from store.db import SessionLocal, engine

from . import build_world, reset


def main() -> None:
    world = build_world()
    with SessionLocal.begin() as session:
        seeded = reset(session, world)

    orders = sum(len(c.orders) for c in world.customers)
    # Only the database name: the URL can carry a password.
    print(f"Seeded {engine.url.database}: {len(world.customers)} customers, {orders} orders\n")
    print(f"{'scenario':<24} {'order':>5}  {'customer':<28} note")
    for s in seeded:
        print(f"{s.scenario:<24} {s.order_id:>5}  {s.email:<28} {s.note}")


if __name__ == "__main__":
    main()
