# -*- coding: utf-8 -*-
"""Dependency-light proof that procurement memory survives a new session boundary."""
from app.application.memory.preference_selector import PreferenceSelector, render_preference_hint
from app.domain.buyer.preference import BuyerPreference
from app.infrastructure.persistence.json_file_stores import JsonFilePreferenceStore


async def test_required_certification_persists_and_is_selected_in_new_turn(tmp_path):
    store = JsonFilePreferenceStore(tmp_path)
    await store.append(
        BuyerPreference(
            buyer_id="buyer-001",
            kind="like",
            statement="required_certification=LFGB",
        )
    )

    # Simulate a later session/turn by reading from a new store instance backed
    # by the same persistence directory instead of sharing in-memory objects.
    reopened = JsonFilePreferenceStore(tmp_path)
    persisted = await reopened.list_by_buyer("buyer-001")
    selected = await PreferenceSelector().select(
        persisted,
        query="继续找 5000 个 750ml 不锈钢保温杯",
        top_k=5,
    )

    assert [pref.statement for pref in selected] == ["required_certification=LFGB"]
    hint = render_preference_hint(selected)
    assert "required_certification=LFGB" in hint
    assert "当前 RFQ 的明确条件优先" in hint
