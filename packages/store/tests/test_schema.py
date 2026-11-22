"""Smoke tests for the store schema. These need no database."""

from sqlalchemy import CheckConstraint

from store.models import Base

EXPECTED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
    "refunds",
    "replacements",
    "returns",
    "tickets",
    "ticket_messages",
    "audit_log",
}


def test_models_define_every_store_table():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_check_constraints_follow_the_naming_convention():
    # Migrations drop and replace CHECK constraints by name, so every one
    # must come out as ck_<table>_<name>.
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint):
                assert constraint.name.startswith(f"ck_{table.name}_"), constraint.name
