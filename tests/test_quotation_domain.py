# -*- coding: utf-8 -*-
import pytest

from app.domain.quotation.quotation import Quotation


def test_lead_time_range_uses_conservative_max():
    quote = Quotation(
        quote_id="Q-1",
        supplier_id="SUP-1",
        quantity=5000,
        unit_price=3.65,
        currency="USD",
        lead_time_min_days=25,
        lead_time_max_days=30,
    )
    assert quote.lead_time_days == 30
    assert quote.lead_time_min_days == 25
    assert quote.lead_time_max_days == 30


def test_missing_unit_price_is_explicit_and_not_computable():
    quote = Quotation(
        quote_id="Q-1",
        supplier_id="SUP-1",
        quantity=5000,
        unit_price=None,
        currency="USD",
        logo_fee_per_unit=0,
        packaging_fee_per_unit=0,
        fixed_fee=0,
    )
    assert quote.missing_required_fields() == ["unit_price"]
    assert quote.calculate_effective_unit_cost(assume_missing_fees_zero=True) is None


def test_invalid_lead_range_rejected():
    with pytest.raises(ValueError, match="min"):
        Quotation(
            quote_id="Q-1",
            supplier_id="SUP-1",
            quantity=5000,
            unit_price=3.65,
            currency="USD",
            lead_time_min_days=30,
            lead_time_max_days=20,
        )
