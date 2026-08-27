# -*- coding: utf-8 -*-
import pytest

from app.application.usecases.quotation_compare import (
    MVP_WEIGHTS,
    QuotationCompareUseCase,
    SupplierQuoteInput,
)
from app.domain.procurement.rfq import RFQ
from app.domain.quotation.quotation import Quotation
from app.domain.supplier.supplier import Supplier


def _rfq(**overrides):
    data = dict(
        request_id="RFQ-1",
        product="vacuum flask",
        quantity=5000,
        target_price=4.0,
        currency="USD",
        material=["304 stainless steel"],
        specifications={"capacity_ml": 750},
        customization=["laser logo"],
        required_certifications=["LFGB"],
        max_lead_time_days=30,
        destination="US",
        preferred_incoterm="FOB",
    )
    data.update(overrides)
    return RFQ(**data)


def _supplier(sid: str, **overrides):
    data = dict(
        supplier_id=sid,
        company_name=f"{sid} Manufacturing",
        business_type="manufacturer",
        categories=["vacuum flask"],
        product_text="750ml 304 stainless steel vacuum flask",
        moq=1000,
        unit_price=3.8,
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
    data.update(overrides)
    return Supplier(**data)


def _quote(sid: str, **overrides):
    data = dict(
        quote_id=f"Q-{sid}",
        supplier_id=sid,
        quantity=5000,
        unit_price=3.65,
        currency="USD",
        incoterm="FOB",
        logo_fee_per_unit=0.12,
        packaging_fee_per_unit=0.18,
        fixed_fee=80,
        lead_time_days=25,
        certifications_confirmed=["LFGB"],
    )
    data.update(overrides)
    return Quotation(**data)


def test_weights_are_explicit_and_sum_to_one():
    assert MVP_WEIGHTS == {
        "requirement_match": 0.35,
        "effective_cost": 0.25,
        "lead_time": 0.15,
        "reliability": 0.15,
        "moq_flexibility": 0.10,
    }
    assert sum(MVP_WEIGHTS.values()) == pytest.approx(1.0)


def test_fixed_fee_is_recomputed_by_usecase():
    quote = _quote("SUP-1")
    quote.effective_unit_cost = 999.0  # simulate untrusted LLM/tool payload
    result = QuotationCompareUseCase().execute(
        _rfq(), [SupplierQuoteInput(_supplier("SUP-1"), quote)],
    )
    assert result["shortlist"][0]["effective_unit_cost"] == pytest.approx(3.966)


def test_hard_gate_beats_soft_rank():
    good = SupplierQuoteInput(
        _supplier("SUP-GOOD", reliability_score=0.65),
        _quote("SUP-GOOD", unit_price=3.9),
    )
    bad = SupplierQuoteInput(
        _supplier("SUP-BAD", reliability_score=1.0),
        _quote("SUP-BAD", unit_price=4.5),
    )
    result = QuotationCompareUseCase().execute(_rfq(), [bad, good])
    assert [row["supplier_id"] for row in result["shortlist"]] == ["SUP-GOOD"]
    assert result["disqualified"][0]["supplier_id"] == "SUP-BAD"
    assert "price_above_target" in result["disqualified"][0]["reason_codes"]


def test_lead_time_range_uses_max_for_hard_gate():
    item = SupplierQuoteInput(
        _supplier("SUP-1"),
        _quote("SUP-1", lead_time_days=None, lead_time_min_days=25, lead_time_max_days=35),
    )
    result = QuotationCompareUseCase().execute(_rfq(), [item])
    assert result["shortlist"] == []
    assert "lead_time_too_long" in result["disqualified"][0]["reason_codes"]


def test_partial_cost_is_rankable_but_penalized_and_marked():
    full = SupplierQuoteInput(
        _supplier("SUP-FULL", reliability_score=0.8),
        _quote("SUP-FULL", unit_price=3.8, logo_fee_per_unit=0.0, packaging_fee_per_unit=0.0, fixed_fee=0.0),
    )
    partial = SupplierQuoteInput(
        _supplier("SUP-PART", reliability_score=0.8),
        _quote("SUP-PART", unit_price=3.8, logo_fee_per_unit=None, packaging_fee_per_unit=None, fixed_fee=None),
    )
    result = QuotationCompareUseCase().execute(_rfq(), [partial, full], top_k=2)
    assert result["shortlist"][0]["supplier_id"] == "SUP-FULL"
    partial_row = next(row for row in result["shortlist"] if row["supplier_id"] == "SUP-PART")
    assert partial_row["effective_unit_cost"] is None
    assert partial_row["cost_is_partial"] is True
    assert any("partial" in risk for risk in partial_row["risks"])



def test_missing_quoted_unit_price_cannot_fall_back_to_supplier_profile_price():
    item = SupplierQuoteInput(
        _supplier("SUP-1", unit_price=3.5),
        _quote("SUP-1", unit_price=None),
    )
    result = QuotationCompareUseCase().execute(_rfq(), [item])
    assert result["shortlist"] == []
    assert "quote_incomplete" in result["disqualified"][0]["reason_codes"]


def test_missing_quote_currency_is_incomplete_not_silently_inferred():
    item = SupplierQuoteInput(
        _supplier("SUP-1", currency="USD"),
        _quote("SUP-1", currency=None),
    )
    result = QuotationCompareUseCase().execute(_rfq(), [item])
    assert result["shortlist"] == []
    assert "quote_incomplete" in result["disqualified"][0]["reason_codes"]

def test_ranking_is_stable_under_input_order():
    items = [
        SupplierQuoteInput(_supplier("SUP-A", reliability_score=0.90), _quote("SUP-A", unit_price=3.6, lead_time_days=20)),
        SupplierQuoteInput(_supplier("SUP-B", reliability_score=0.75), _quote("SUP-B", unit_price=3.7, lead_time_days=22)),
        SupplierQuoteInput(_supplier("SUP-C", reliability_score=0.82), _quote("SUP-C", unit_price=3.8, lead_time_days=25)),
    ]
    usecase = QuotationCompareUseCase()
    first = [row["supplier_id"] for row in usecase.execute(_rfq(), items)["shortlist"]]
    second = [row["supplier_id"] for row in usecase.execute(_rfq(), list(reversed(items)))["shortlist"]]
    assert first == second


def test_final_scores_are_bounded_and_reproducible():
    item = SupplierQuoteInput(_supplier("SUP-1"), _quote("SUP-1"))
    usecase = QuotationCompareUseCase()
    first = usecase.execute(_rfq(), [item])["shortlist"][0]
    second = usecase.execute(_rfq(), [item])["shortlist"][0]
    assert 0 <= first["final_score"] <= 100
    assert first["final_score"] == second["final_score"]
    assert first["needs_human_approval"] is True
