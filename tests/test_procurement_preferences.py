# -*- coding: utf-8 -*-
from app.application.memory.procurement_preferences import (
    ALLOWED_PROCUREMENT_PREFERENCE_TYPES,
    parse_procurement_preference,
    validate_procurement_preference_statement,
)


def test_all_frozen_procurement_preference_types_are_supported():
    assert set(ALLOWED_PROCUREMENT_PREFERENCE_TYPES) == {
        "preferred_incoterm",
        "required_certification",
        "supplier_blacklist",
        "preferred_supplier",
        "target_market",
        "material_preference",
    }


def test_normalizes_type_value_statement():
    pref = parse_procurement_preference(" required_certification = LFGB ")
    assert pref.preference_type == "required_certification"
    assert pref.value == "LFGB"
    assert pref.statement == "required_certification=LFGB"
    assert validate_procurement_preference_statement(" target_market = US ") == "target_market=US"


def test_rejects_freeform_one_off_condition():
    try:
        validate_procurement_preference_statement("这次要军绿色")
    except ValueError as err:
        assert "type=value" in str(err)
    else:
        raise AssertionError("B2B memory must reject untyped one-off statements")


def test_rejects_unknown_type_and_empty_value():
    for statement in ("budget=4", "preferred_incoterm="):
        try:
            validate_procurement_preference_statement(statement)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected invalid procurement preference: {statement}")
