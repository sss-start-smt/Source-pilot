import json
from pathlib import Path

# Evaluation data lives under evaluation/ in the sourcepilot layout.
# Original Globex layout used eval/ with .jsonl; this loader accepts
# either path and either extension (.json or .jsonl) so the tests
# pass under both the new and the legacy file naming.
EVAL_DIR_CANDIDATES = ("evaluation", "eval")


def _load(name: str):
    last_err: Exception | None = None
    for base in EVAL_DIR_CANDIDATES:
        for ext in (".jsonl", ".json"):
            path = Path(base) / f"{name}{ext}"
            if path.exists():
                return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            last_err = FileNotFoundError(str(path))
    raise last_err or FileNotFoundError(name)


def test_day6_dataset_sizes_and_declared_sources():
    rfq = _load("rfq_cases")
    quotes = _load("quotation_cases")
    search = _load("supplier_cases")
    decision = _load("decision_cases")
    assert len(rfq) == 50
    assert len(quotes) >= 30
    assert len(search) == 30
    assert len(decision) == 10
    assert sum(x["case_type"] == "complete" for x in rfq) == 20
    assert sum(x["case_type"] == "missing" for x in rfq) == 15
    assert sum(x["case_type"] == "conflict" for x in rfq) == 10
    assert sum(x["case_type"] == "no_match" for x in rfq) == 5


def test_supplier_recall_labels_are_explicitly_synthetic():
    rows = _load("supplier_cases")
    assert all("synthetic" in row.get("annotation_note", "") for row in rows)
    assert all(row.get("relevant_supplier_ids") for row in rows)
