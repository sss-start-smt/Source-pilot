# -*- coding: utf-8 -*-
"""Day 3 supplier-search tool input validation tests.

The pure validation boundary is intentionally free of AgentScope imports, so
these tests remain runnable in the constrained execution sandbox.
"""
import pytest

from app.application.tools.supplier_search_validation import validate_supplier_search_input


def test_numeric_strings_are_coerced_before_search():
    validated = validate_supplier_search_input(
        product="vacuum flask",
        quantity="5000",
        price_max_major="4.0",
        max_lead_time_days="30",
        top_k="5",
        currency="usd",
    )
    assert validated.quantity == 5000
    assert validated.price_max_major == 4.0
    assert validated.max_lead_time_days == 30
    assert validated.top_k == 5
    assert validated.currency == "USD"


def test_missing_product_is_rejected_before_supplier_search():
    with pytest.raises(ValueError, match="product required"):
        validate_supplier_search_input(
            product="", quantity=5000, price_max_major=None,
            max_lead_time_days=None, top_k=5, currency="USD",
        )


def test_invalid_quantity_is_rejected_before_supplier_search():
    with pytest.raises(ValueError, match="quantity"):
        validate_supplier_search_input(
            product="vacuum flask", quantity="many", price_max_major=None,
            max_lead_time_days=None, top_k=5, currency="USD",
        )


def test_optional_constraints_remain_optional_not_invented():
    validated = validate_supplier_search_input(
        product="nylon backpack", quantity=2000, price_max_major=None,
        max_lead_time_days=None, top_k=3, currency="USD",
    )
    assert validated.price_max_major is None
    assert validated.max_lead_time_days is None
