# -*- coding: utf-8 -*-
"""Day 2 B2B domain tests: RFQ, Supplier, SupplierSearchSpec and Quotation."""
import pytest

from app.domain.procurement.rfq import RFQ
from app.domain.quotation.quotation import Quotation
from app.domain.supplier.supplier import Supplier
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec


def _supplier(**overrides) -> Supplier:
    values = dict(
        supplier_id="SUP-001",
        company_name="Example Manufacturing",
        business_type="manufacturer",
        categories=["vacuum flask"],
        product_text="750ml 304 stainless steel vacuum flask OEM ODM",
        moq=3000,
        unit_price=3.65,
        currency="USD",
        incoterms=["FOB", "CIF"],
        lead_time_days=25,
        certifications=["LFGB", "FDA"],
        customization=["laser logo", "custom box"],
        years_in_business=8,
        export_markets=["US", "EU"],
        reliability_score=0.82,
        source="mvp_seed",
    )
    values.update(overrides)
    return Supplier(**values)


class TestRFQ:
    def test_valid_rfq(self):
        rfq = RFQ(
            request_id="RFQ-001",
            product="vacuum flask",
            quantity=5000,
            target_price=4.0,
            required_certifications=["LFGB"],
            max_lead_time_days=30,
        )
        assert rfq.quantity == 5000
        assert rfq.currency == "USD"

    @pytest.mark.parametrize("quantity", [0, -1])
    def test_quantity_must_be_positive(self, quantity):
        with pytest.raises(ValueError, match="quantity"):
            RFQ(request_id="RFQ-001", product="vacuum flask", quantity=quantity)

    def test_optional_numeric_constraints_must_be_positive(self):
        with pytest.raises(ValueError, match="target_price"):
            RFQ(request_id="RFQ-001", product="vacuum flask", quantity=1, target_price=0)
        with pytest.raises(ValueError, match="max_lead_time_days"):
            RFQ(request_id="RFQ-001", product="vacuum flask", quantity=1, max_lead_time_days=-3)


class TestSupplier:
    def test_source_is_required(self):
        with pytest.raises(ValueError, match="source"):
            _supplier(source="")

    def test_searchable_text_contains_decision_signals(self):
        text = _supplier().searchable_text()
        for expected in (
            "Example Manufacturing",
            "vacuum flask",
            "LFGB",
            "laser logo",
            "US",
        ):
            assert expected in text

    def test_partial_information_is_representable(self):
        supplier = _supplier(
            unit_price=None,
            moq=None,
            lead_time_days=None,
            certifications=None,
            customization=None,
        )
        assert supplier.unit_price is None
        assert supplier.certifications is None
        assert "Example Manufacturing" in supplier.searchable_text()

    def test_reliability_score_range(self):
        with pytest.raises(ValueError, match="reliability_score"):
            _supplier(reliability_score=1.2)


class TestSupplierSearchSpec:
    def test_rejects_invalid_top_k(self):
        with pytest.raises(ValueError, match="top_k"):
            SupplierSearchSpec(normalized_query="vacuum flask", top_k=0)

    def test_rejects_invalid_constraints(self):
        with pytest.raises(ValueError, match="quantity"):
            SupplierSearchSpec(normalized_query="vacuum flask", quantity=0)
        with pytest.raises(ValueError, match="price_max_major"):
            SupplierSearchSpec(normalized_query="vacuum flask", price_max_major=0)


class TestQuotation:
    def test_effective_unit_cost(self):
        quote = Quotation(
            quote_id="Q-001",
            supplier_id="SUP-001",
            quantity=5000,
            unit_price=3.65,
            currency="USD",
            logo_fee_per_unit=0.12,
            packaging_fee_per_unit=0.18,
            fixed_fee=80.0,
        )
        assert quote.calculate_effective_unit_cost() == pytest.approx(3.966)

    def test_unknown_fee_makes_cost_noncomputable_by_default(self):
        quote = Quotation(
            quote_id="Q-001",
            supplier_id="SUP-001",
            quantity=5000,
            unit_price=3.65,
            currency="USD",
            logo_fee_per_unit=None,
            packaging_fee_per_unit=0.18,
            fixed_fee=80.0,
        )
        assert quote.missing_cost_fields() == ["logo_fee_per_unit"]
        assert quote.calculate_effective_unit_cost() is None
        assert quote.calculate_effective_unit_cost(assume_missing_fees_zero=True) == pytest.approx(3.846)

    def test_explicit_zero_fee_is_not_missing(self):
        quote = Quotation(
            quote_id="Q-001",
            supplier_id="SUP-001",
            quantity=100,
            unit_price=2.0,
            currency="USD",
            logo_fee_per_unit=0.0,
            packaging_fee_per_unit=0.0,
            fixed_fee=0.0,
        )
        assert quote.missing_cost_fields() == []
        assert quote.calculate_effective_unit_cost() == pytest.approx(2.0)
