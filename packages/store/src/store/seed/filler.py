"""Background customers and orders, so lookups search a realistic crowd.

No eval ticket refers to filler rows. They come from a fixed random seed rather
than Faker: Faker's output can change between its releases, and a seed that
shifts under the tickets is worse than one with plain names. Filler first names
never overlap the scenario customers', so a scenario lookup stays unambiguous.
"""

import random

from .spec import (
    CustomerSpec,
    Line,
    OrderSpec,
    Timeline,
    cancelled,
    delivered,
    in_transit,
    lost,
    placed,
)

FILLER_SEED = 20260601

FIRST_NAMES = (
    "Aaron", "Beatriz", "Carlos", "Dmitri", "Esther", "Farah", "Gabriel", "Helga",
    "Ivan", "Kofi", "Laila", "Marco", "Nadia", "Oscar", "Paula", "Quentin",
    "Rosa", "Stefan", "Tariq", "Ursula", "Victor", "Wendy", "Yusuf",
)  # fmt: skip
LAST_NAMES = (
    "Abbott", "Brennan", "Castillo", "Dubois", "Eriksen", "Fontaine", "Gallagher",
    "Holm", "Ibrahim", "Jensen", "Kowalski", "Lam", "Moreau", "Novak", "Olsen",
    "Pereira", "Quinn", "Rossi", "Schmidt", "Tanaka",
)  # fmt: skip


def _timeline(rng: random.Random) -> Timeline:
    kind = rng.choices(
        ("delivered", "in_transit", "placed", "cancelled", "lost"),
        weights=(70, 10, 5, 10, 5),
    )[0]
    if kind == "delivered":
        return delivered(rng.randint(1, 365))
    if kind == "in_transit":
        return in_transit(rng.randint(1, 4), due_in_days=rng.randint(1, 5))
    if kind == "placed":
        return placed(rng.randint(1, 2))
    if kind == "cancelled":
        return cancelled(rng.randint(2, 200))
    shipped = rng.randint(40, 300)
    return lost(shipped, due_in_days=-(shipped - 7))


def _order(rng: random.Random, skus: list[str]) -> OrderSpec:
    timeline = _timeline(rng)
    chosen = rng.sample(skus, rng.choice((1, 1, 2, 2, 3)))
    return OrderSpec(timeline, tuple(Line(sku, qty=rng.choice((1, 1, 1, 2))) for sku in chosen))


def filler_customers(n_customers: int, n_orders: int, skus: list[str]) -> tuple[CustomerSpec, ...]:
    """n_customers people sharing n_orders orders; everyone gets at least one."""
    rng = random.Random(FILLER_SEED)
    names = rng.sample([(f, last) for f in FIRST_NAMES for last in LAST_NAMES], n_customers)
    orders: list[list[OrderSpec]] = [[] for _ in names]
    for i in range(n_orders):
        owner = i if i < n_customers else rng.randrange(n_customers)
        orders[owner].append(_order(rng, skus))
    return tuple(
        CustomerSpec(
            f"{first} {last}",
            f"{first}.{last}@example.com".lower(),
            tuple(sorted(own, key=lambda o: o.timeline.placed_at)),
        )
        for (first, last), own in zip(names, orders, strict=True)
    )
