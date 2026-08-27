from app.application.rfq_parser import parse_rfq_text


def test_complete_rfq_extracts_critical_fields():
    result = parse_rfq_text(
        "找 5000 个 750ml 304 不锈钢保温杯，要做激光 Logo，需要 LFGB，FOB 单价不超过 4 美元，30 天内出货。"
    )
    assert result.product == "vacuum flask"
    assert result.quantity == 5000
    assert result.target_price == 4.0
    assert result.required_certifications == ["LFGB"]
    assert result.max_lead_time_days == 30
    assert result.customization == ["laser logo"]


def test_missing_product_is_reported_not_invented():
    result = parse_rfq_text("Need 5000 pcs, LFGB, target price USD 4, lead time 30 days.")
    assert result.product is None
    assert result.quantity == 5000
    assert result.missing_required_fields == ["product"]


def test_conflicting_price_is_flagged():
    result = parse_rfq_text("Need 5000 pcs vacuum flask, target price USD 3.8, but ceiling USD 4.0, LFGB.")
    assert result.product == "vacuum flask"
    assert result.target_price == 3.8
    assert "target_price" in result.conflict_fields


def test_no_match_product_can_still_be_structured():
    result = parse_rfq_text("Need 3000 pcs ceramic mug, target price USD 2.5, lead time 30 days.")
    assert result.product == "ceramic mug"
    assert result.quantity == 3000
    assert not result.missing_required_fields
