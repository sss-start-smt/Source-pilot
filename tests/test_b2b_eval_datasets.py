import json
from pathlib import Path


def _load(path: str):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def test_day6_dataset_sizes_and_declared_sources():
    rfq = _load("eval/rfq_cases.jsonl")
    quotes = _load("eval/quotation_cases.jsonl")
    search = _load("eval/supplier_recall.jsonl")
    decision = _load("eval/decision_cases.jsonl")
    assert len(rfq) == 50
    assert len(quotes) >= 30
    assert len(search) == 30
    assert len(decision) == 10
    assert sum(x["case_type"] == "complete" for x in rfq) == 20
    assert sum(x["case_type"] == "missing" for x in rfq) == 15
    assert sum(x["case_type"] == "conflict" for x in rfq) == 10
    assert sum(x["case_type"] == "no_match" for x in rfq) == 5


def test_supplier_recall_labels_are_explicitly_synthetic():
    rows = _load("eval/supplier_recall.jsonl")
    assert all("synthetic" in row["annotation_note"] for row in rows)
    assert all(row["relevant_supplier_ids"] for row in rows)
