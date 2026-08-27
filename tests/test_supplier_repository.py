# -*- coding: utf-8 -*-
"""Day 2 supplier seed dataset and repository tests."""
from collections import Counter

from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository
from app.infrastructure.persistence.seed_suppliers import build_seed_suppliers


def test_seed_supplier_dataset_has_required_scale_and_categories():
    suppliers = build_seed_suppliers()
    counts = Counter(s.categories[0] for s in suppliers)
    assert len(suppliers) == 180
    assert counts == {
        "vacuum flask": 60,
        "nylon backpack": 60,
        "electronic accessories": 60,
    }
    assert all(s.source == "mvp_seed" for s in suppliers)


def test_seed_contains_intentional_constraint_failures_and_missing_data():
    suppliers = build_seed_suppliers()
    vacuum = {s.supplier_id: s for s in suppliers if s.categories == ["vacuum flask"]}
    assert vacuum["SUP-VF-001"].unit_price <= 4.0
    assert vacuum["SUP-VF-002"].moq > 5000
    assert vacuum["SUP-VF-003"].unit_price > 4.0
    assert "LFGB" not in (vacuum["SUP-VF-004"].certifications or [])
    assert vacuum["SUP-VF-005"].lead_time_days > 30
    assert "laser logo" not in (vacuum["SUP-VF-006"].customization or [])
    assert vacuum["SUP-VF-008"].unit_price is None
    assert vacuum["SUP-VF-009"].lead_time_days is None
    assert vacuum["SUP-VF-010"].certifications is None


async def test_repository_find_by_ids_preserves_requested_order():
    repo = InMemorySupplierRepository()
    suppliers = await repo.find_by_ids(["SUP-BP-001", "SUP-VF-001", "missing"])
    assert [s.supplier_id for s in suppliers] == ["SUP-BP-001", "SUP-VF-001"]


async def test_repository_list_all():
    repo = InMemorySupplierRepository()
    suppliers = await repo.list_all()
    assert len(suppliers) == 180
