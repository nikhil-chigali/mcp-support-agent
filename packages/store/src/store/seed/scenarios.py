"""The hand-written part of the seed: the catalog and the scenario orders.

Each scenario order sits on purpose at a refund-policy boundary (Store design,
R1-R8). Eval tickets are written against these rows, so treat this file like an
API: changing a scenario means changing the tickets that use it. Scenario
customers have no other orders, so a ticket from one of them can only mean what
it is meant to, except where ambiguity is the point (the three Janes).

Scenario customers and orders are inserted first, in this order, so their ids
are the same on every run.
"""

from store.models import ReturnStatus

from .spec import (
    CustomerSpec,
    Line,
    OrderSpec,
    PriorRefund,
    Product,
    Timeline,
    cancelled,
    delivered,
    in_transit,
    lost,
    placed,
)

PRODUCTS = (
    Product("TIMER", "Kitchen timer", 900),
    Product("SPOONS", "Measuring spoon set", 1250),
    Product("MUG", "Stoneware mug", 1400),
    Product("TOWELS", "Linen tea towels, set of 3", 1800),
    Product("TEAPOT", "Cast-iron teapot", 3800),
    Product("BOARD", "Walnut cutting board", 4500),
    Product("KETTLE", "Pour-over kettle", 4999),  # just under $50: no return
    Product("KNIFE", "Chef's knife", 5000),  # exactly $50: return needed
    Product("SKILLET", "Cast-iron skillet", 6400),
    Product("GRINDER", "Burr coffee grinder", 11000),
    Product("DUTCH-OVEN", "Enamelled Dutch oven", 18900),
    Product("MIXER", "Stand mixer", 20000),  # exactly $200: no manager
    Product("ESPRESSO", "Espresso machine", 22000),  # over $200, under it after a 10% fee
    Product("COOKWARE", "Copper cookware set", 34900),
)


def customer(name: str, email: str, *orders: OrderSpec) -> CustomerSpec:
    return CustomerSpec(name, email, orders)


def order(key: str, note: str, timeline: Timeline, *lines: Line) -> OrderSpec:
    return OrderSpec(timeline, lines, scenario=key, note=note)


SCENARIO_CUSTOMERS = (
    # --- R1: cancel before shipping -------------------------------------------
    customer(
        "Omar Haddad",
        "omar.haddad@example.com",
        order(
            "r1-not-shipped",
            "Placed yesterday, not shipped: R1 cancel, refund every item",
            placed(1),
            Line("KETTLE"),
            Line("MUG", qty=2),
        ),
    ),
    customer(
        "Tom Becker",
        "tom.becker@example.com",
        order(
            "r1-already-shipped",
            "Shipped 2 days ago, due in 3: too late to cancel",
            in_transit(shipped_days_ago=2, due_in_days=3),
            Line("GRINDER"),
        ),
    ),
    customer(
        "Lucia Ferraro",
        "lucia.ferraro@example.com",
        order(
            "cancelled-already",
            "Cancelled and refunded 4 days ago: nothing left to do",
            cancelled(4),
            Line("TOWELS", prior_refunds=(PriorRefund(1800, "R1", "cancelled"),)),
            Line("SPOONS", prior_refunds=(PriorRefund(1250, "R1", "cancelled"),)),
        ),
    ),
    # --- R2: damaged or defective, within 30 days -------------------------------
    customer(
        "Maya Chen",
        "maya.chen@example.com",
        order(
            "r2-day-30",
            "Damaged, delivered 30 days ago: R2 full refund; $50.00 so a return is needed",
            delivered(30),
            Line("KNIFE"),
        ),
    ),
    customer(
        "Ken Watanabe",
        "ken.watanabe@example.com",
        order(
            "r2-under-50",
            "Damaged $49.99 kettle, delivered 10 days ago: R2 full refund, no return",
            delivered(10),
            Line("KETTLE"),
        ),
    ),
    customer(
        "Priya Raman",
        "priya.raman@example.com",
        order(
            "day-31-skillet",
            "Delivered 31 days ago: damaged is R6 deny, defective is R5 store credit",
            delivered(31),
            Line("SKILLET"),
        ),
    ),
    # --- R3: change of mind, within 30 days -------------------------------------
    customer(
        "Ada Nwosu",
        "ada.nwosu@example.com",
        order(
            "r3-day-30",
            "Change of mind on day 30: R3 refund minus 10% ($99.00), return needed",
            delivered(30),
            Line("GRINDER"),
        ),
    ),
    customer(
        "Sam Patel",
        "sam.patel@example.com",
        order(
            "r3-day-31",
            "Change of mind on day 31: R6 deny",
            delivered(31),
            Line("BOARD"),
        ),
    ),
    customer(
        "Grace Kim",
        "grace.kim@example.com",
        order(
            "espresso-220",
            "$220 machine: change of mind is $198.00, no manager; damaged is $220.00, needs one",
            delivered(5),
            Line("ESPRESSO"),
        ),
    ),
    # --- R4: never arrived ------------------------------------------------------
    customer(
        "Noah Fischer",
        "noah.fischer@example.com",
        order(
            "r4-overdue-10",
            "Shipped, due 10 days before the ticket, never arrived: R4 full refund",
            in_transit(shipped_days_ago=20, due_in_days=-10),
            Line("TEAPOT"),
            Line("TOWELS"),
        ),
    ),
    customer(
        "Elena Petrova",
        "elena.petrova@example.com",
        order(
            "r4-overdue-9",
            "Due 9 days before the ticket: too early for R4",
            in_transit(shipped_days_ago=18, due_in_days=-9),
            Line("BOARD"),
        ),
    ),
    customer(
        "Ravi Iyer",
        "ravi.iyer@example.com",
        order(
            "lost",
            "Marked lost: R4 full refund",
            lost(shipped_days_ago=40, due_in_days=-33),
            Line("SKILLET"),
        ),
    ),
    # --- R5: defective, 31 to 90 days -------------------------------------------
    customer(
        "Hana Sato",
        "hana.sato@example.com",
        order(
            "r5-day-90",
            "Defective on day 90: R5 store credit of $200.00, at the R7 line, no manager",
            delivered(90),
            Line("MIXER"),
        ),
    ),
    customer(
        "Felix Wagner",
        "felix.wagner@example.com",
        order(
            "r5-day-91",
            "Defective on day 91: R6 deny",
            delivered(91),
            Line("DUTCH-OVEN"),
        ),
    ),
    # --- R7: over $200 needs a manager ------------------------------------------
    customer(
        "Zoe Martin",
        "zoe.martin@example.com",
        order(
            "r7-over-200",
            "Damaged $349.00 cookware: full refund needs a manager",
            delivered(7),
            Line("COOKWARE"),
        ),
    ),
    customer(
        "Leo Grant",
        "leo.grant@example.com",
        order(
            "r7-two-units",
            "Two damaged Dutch ovens on one line: $378.00 at once, or $189.00 twice (R7 scope)",
            delivered(6),
            Line("DUTCH-OVEN", qty=2),
        ),
    ),
    # --- R8: never refund past what was paid ------------------------------------
    customer(
        "Ines Duarte",
        "ines.duarte@example.com",
        order(
            "r8-fully-refunded",
            "Grinder already refunded in full and returned: nothing left",
            delivered(12),
            Line(
                "GRINDER",
                prior_refunds=(
                    PriorRefund(11000, "R2", "damaged", return_status=ReturnStatus.RECEIVED),
                ),
            ),
        ),
    ),
    customer(
        "Arjun Mehta",
        "arjun.mehta@example.com",
        order(
            "r8-partial",
            "4 mugs, 1 already refunded ($14.00 of $56.00): at most $42.00 left",
            delivered(8),
            Line("MUG", qty=4, prior_refunds=(PriorRefund(1400, "R2", "damaged"),)),
        ),
    ),
    # --- Who and which: three customers called Jane -----------------------------
    customer(
        "Jane Okafor",
        "jane.okafor@example.com",
        order(
            "jane-okafor-teapot",
            "One of two recent orders: a vague ticket must ask which",
            delivered(3),
            Line("TEAPOT"),
        ),
        order(
            "jane-okafor-towels",
            "The other recent order",
            delivered(14),
            Line("TOWELS"),
        ),
    ),
    customer(
        "Jane Lindqvist",
        "jane.lindqvist@example.net",
        order(
            "jane-lindqvist-kettle",
            "One recent order; shares a first name",
            delivered(20),
            Line("KETTLE"),
        ),
    ),
    customer(
        "Jane Moreno",
        "jmoreno@example.org",
        order(
            "jane-moreno-mug",
            "One open order; an email that doesn't show her name",
            placed(2),
            Line("MUG"),
        ),
    ),
)
