# -*- coding: utf-8 -*-
import pytest

from app.application.quotation_parser import (
    normalize_structured_quotation,
    parse_quotation_text,
)


def test_structured_extraction_preserves_decimal_and_calculates_cost():
    result = normalize_structured_quotation(
        quote_id="Q-1",
        supplier_id="SUP-1",
        quantity="5000",
        unit_price="USD 3.65/pc",
        currency="USD",
        logo_fee_per_unit="0.12",
        packaging_fee_per_unit="0.18",
        fixed_fee="80",
        lead_time_days="25",
        certifications_confirmed=["LFGB"],
    )
    quote = result.quotation
    assert quote.unit_price == pytest.approx(3.65)
    assert quote.effective_unit_cost == pytest.approx(3.966)
    assert quote.lead_time_days == 25


def test_invalid_decimal_is_rejected_instead_of_silently_reinterpreted():
    with pytest.raises(ValueError, match="unit_price"):
        normalize_structured_quotation(
            quote_id="Q-1",
            supplier_id="SUP-1",
            quantity=5000,
            unit_price="3.6.5",
            currency="USD",
        )


def test_parser_example_from_plan():
    text = """
    For 5000 pcs:
    Unit price USD 3.65/pc
    MOQ 3000 pcs
    FOB Shenzhen
    Laser logo USD 0.12/pc
    Custom box USD 0.18/pc
    Sample fee USD 80
    Lead time 25 days
    Payment 30% deposit, 70% before shipment
    LFGB available
    """
    result = parse_quotation_text(text, quote_id="Q-1", supplier_id="SUP-1", quantity=5000)
    quote = result.quotation
    assert result.parser_strategy == "regex_fallback"
    assert quote.unit_price == pytest.approx(3.65)
    assert quote.logo_fee_per_unit == pytest.approx(0.12)
    assert quote.packaging_fee_per_unit == pytest.approx(0.18)
    assert quote.fixed_fee == pytest.approx(80)
    assert quote.fixed_fee_description == "sample_fee"
    assert quote.incoterm == "FOB"
    assert quote.lead_time_days == 25
    assert quote.certifications_confirmed == ["LFGB"]
    assert quote.effective_unit_cost == pytest.approx(3.966)


def test_parser_email_style_and_lead_range():
    text = (
        "Price: $3.80 each; logo fee: $0.10/pc; packaging fee: $0.15/pc; "
        "setup fee: $50; lead time: 25-30 days; FOB; LFGB FDA; "
        "Payment: 30% deposit, 70% before shipment."
    )
    quote = parse_quotation_text(text, quote_id="Q-2", supplier_id="SUP-2", quantity=5000).quotation
    assert quote.currency == "USD"
    assert quote.unit_price == pytest.approx(3.8)
    assert quote.lead_time_min_days == 25
    assert quote.lead_time_max_days == 30
    assert quote.lead_time_days == 30
    assert set(quote.certifications_confirmed or []) == {"LFGB", "FDA"}


def test_parser_mixed_chinese_english():
    text = "单价 USD 3.70/pc，激光Logo费 0.10美元/个，包装费 0.20美元/个，版费 60美元，交期20-25天，FOB Shenzhen，LFGB可提供"
    quote = parse_quotation_text(text, quote_id="Q-3", supplier_id="SUP-3", quantity=5000).quotation
    assert quote.unit_price == pytest.approx(3.7)
    assert quote.logo_fee_per_unit == pytest.approx(0.1)
    assert quote.packaging_fee_per_unit == pytest.approx(0.2)
    assert quote.fixed_fee == pytest.approx(60)
    assert quote.lead_time_days == 25
    assert quote.incoterm == "FOB"


def test_missing_fee_stays_none_and_partial_cost_is_not_invented():
    text = "Unit price USD 3.65/pc, FOB Shenzhen, Lead time 25 days, LFGB available"
    result = parse_quotation_text(text, quote_id="Q-4", supplier_id="SUP-4", quantity=5000)
    quote = result.quotation
    assert quote.logo_fee_per_unit is None
    assert quote.packaging_fee_per_unit is None
    assert quote.fixed_fee is None
    assert quote.effective_unit_cost is None
    assert "partial_cost_only" in result.warnings
