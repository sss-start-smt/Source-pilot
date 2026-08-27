# -*- coding: utf-8 -*-
"""Dependency-light B2B sourcing evaluation for Day 6.

This script deliberately separates metrics that can be measured offline from
metrics that require live AgentScope/LLM infrastructure or human participants.
It never substitutes assumed values for unavailable measurements.
"""
from __future__ import annotations

import asyncio
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.quotation_parser import parse_quotation_text, normalize_structured_quotation  # noqa: E402
from app.application.rfq_parser import parse_rfq_text  # noqa: E402
from app.application.usecases.quotation_compare import QuotationCompareUseCase, SupplierQuoteInput  # noqa: E402
from app.application.usecases.supplier_search import SupplierSearchUseCase  # noqa: E402
from app.domain.procurement.rfq import RFQ  # noqa: E402
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec  # noqa: E402
from app.infrastructure.persistence.in_memory_repositories import InMemorySupplierRepository  # noqa: E402
from scripts.eval.metrics import ndcg_at_k, recall_at_k  # noqa: E402

EVAL = ROOT / "eval"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().casefold().split())
    if isinstance(value, list):
        return sorted(norm_value(x) for x in value)
    if isinstance(value, dict):
        return {k: norm_value(v) for k, v in sorted(value.items())}
    if isinstance(value, float):
        return round(value, 6)
    return value


def same(a: Any, b: Any) -> bool:
    return norm_value(a) == norm_value(b)


def safe_rate(num: int | float, den: int | float) -> float:
    return 0.0 if not den else float(num) / float(den)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def rfq_schema_valid(payload: dict[str, Any]) -> bool:
    scalar_types = {
        "product": (str, type(None)), "quantity": (int, type(None)),
        "target_price": (int, float, type(None)), "currency": (str,),
        "max_lead_time_days": (int, type(None)), "destination": (str, type(None)),
        "preferred_incoterm": (str, type(None)),
    }
    for key, types in scalar_types.items():
        if not isinstance(payload.get(key), types):
            return False
    for key in ("material", "customization", "required_certifications", "missing_required_fields", "conflict_fields"):
        if not isinstance(payload.get(key), list):
            return False
    if not isinstance(payload.get("specifications"), dict):
        return False
    if payload.get("quantity") is not None and payload["quantity"] <= 0:
        return False
    if payload.get("target_price") is not None and payload["target_price"] <= 0:
        return False
    if payload.get("max_lead_time_days") is not None and payload["max_lead_time_days"] <= 0:
        return False
    return True


def evaluate_rfq() -> dict[str, Any]:
    cases = load_jsonl(EVAL / "rfq_cases.jsonl")
    fields = [
        "product", "quantity", "target_price", "currency", "material", "specifications",
        "customization", "required_certifications", "max_lead_time_days", "destination",
        "preferred_incoterm", "missing_required_fields",
    ]
    critical = ["product", "quantity", "target_price", "required_certifications", "max_lead_time_days"]
    correct = defaultdict(int)
    total = defaultdict(int)
    critical_tp = 0
    critical_gold = 0
    schema_valid = 0
    conflict_tp = conflict_fp = conflict_fn = 0
    per_type = defaultdict(lambda: [0, 0])
    failures: list[dict[str, Any]] = []

    for case in cases:
        pred = parse_rfq_text(case["text"]).to_dict()
        gold = case["gold"]
        schema_valid += int(rfq_schema_valid(pred))
        row_all = True
        for field in fields:
            total[field] += 1
            ok = same(pred.get(field), gold.get(field))
            correct[field] += int(ok)
            row_all &= ok
        for field in critical:
            gv = gold.get(field)
            is_present = gv is not None and gv != [] and gv != ""
            if is_present:
                critical_gold += 1
                critical_tp += int(same(pred.get(field), gv))

        pred_conf = set(pred.get("conflict_fields", []))
        gold_conf = set(gold.get("conflict_fields", []))
        conflict_tp += len(pred_conf & gold_conf)
        conflict_fp += len(pred_conf - gold_conf)
        conflict_fn += len(gold_conf - pred_conf)
        per_type[case["case_type"]][0] += int(row_all)
        per_type[case["case_type"]][1] += 1
        if not row_all and len(failures) < 12:
            failures.append({"case_id": case["case_id"], "type": case["case_type"], "pred": pred, "gold": gold})

    field_accuracy = {f: round(safe_rate(correct[f], total[f]), 4) for f in fields}
    micro_field_accuracy = round(safe_rate(sum(correct.values()), sum(total.values())), 4)
    conflict_precision = safe_rate(conflict_tp, conflict_tp + conflict_fp)
    conflict_recall = safe_rate(conflict_tp, conflict_tp + conflict_fn)
    conflict_f1 = safe_rate(2 * conflict_precision * conflict_recall, conflict_precision + conflict_recall)
    return {
        "case_count": len(cases),
        "schema_valid_rate": round(schema_valid / len(cases), 4),
        "field_accuracy": field_accuracy,
        "micro_field_accuracy": micro_field_accuracy,
        "critical_constraint_recall": round(safe_rate(critical_tp, critical_gold), 4),
        "conflict_detection": {
            "precision": round(conflict_precision, 4), "recall": round(conflict_recall, 4), "f1": round(conflict_f1, 4),
        },
        "exact_case_accuracy_by_type": {k: round(safe_rate(v[0], v[1]), 4) for k, v in sorted(per_type.items())},
        "sample_failures": failures,
        "parser_strategy": "dependency-free regex fallback; production path remains LLM structured extraction + validation",
    }


def evaluate_quotation() -> dict[str, Any]:
    cases = load_jsonl(EVAL / "quotation_cases.jsonl")
    fields = [
        "unit_price", "currency", "incoterm", "logo_fee_per_unit", "packaging_fee_per_unit",
        "fixed_fee", "lead_time_min_days", "lead_time_max_days", "certifications_confirmed",
    ]
    correct = defaultdict(int)
    total = defaultdict(int)
    schema_valid = 0
    cost_cases = cost_correct = 0
    failures = []

    for case in cases:
        ext = parse_quotation_text(
            case["text"], quote_id=case["case_id"], supplier_id=case["supplier_id"],
            quantity=case["gold"]["quantity"],
        )
        pred = ext.quotation.to_dict()
        gold = case["gold"]
        try:
            # Domain construction already occurred; these checks ensure required container invariants.
            valid = pred["quantity"] > 0 and pred["quote_id"] and pred["supplier_id"]
        except Exception:
            valid = False
        schema_valid += int(bool(valid))
        row_all = True
        for field in fields:
            total[field] += 1
            ok = same(pred.get(field), gold.get(field))
            correct[field] += int(ok)
            row_all &= ok

        fees = [gold.get("logo_fee_per_unit"), gold.get("packaging_fee_per_unit"), gold.get("fixed_fee")]
        if gold.get("unit_price") is not None and all(v is not None for v in fees):
            cost_cases += 1
            expected = gold["unit_price"] + gold["logo_fee_per_unit"] + gold["packaging_fee_per_unit"] + gold["fixed_fee"] / gold["quantity"]
            actual = pred.get("effective_unit_cost")
            cost_correct += int(actual is not None and abs(actual - expected) <= 1e-9)
        if not row_all and len(failures) < 12:
            failures.append({"case_id": case["case_id"], "pred": {f: pred.get(f) for f in fields}, "gold": {f: gold.get(f) for f in fields}})

    return {
        "case_count": len(cases),
        "schema_valid_rate": round(schema_valid / len(cases), 4),
        "field_accuracy": {f: round(safe_rate(correct[f], total[f]), 4) for f in fields},
        "micro_field_accuracy": round(safe_rate(sum(correct.values()), sum(total.values())), 4),
        "cost_calculation_accuracy": round(safe_rate(cost_correct, cost_cases), 4),
        "cost_calculation_case_count": cost_cases,
        "sample_failures": failures,
        "parser_strategy": "conservative regex fallback for offline eval; unknown fields remain null",
    }


def independent_hard_pass(s, c: dict[str, Any]) -> bool:
    if s.moq is None or s.moq > c["quantity"]:
        return False
    if s.unit_price is None or s.currency.upper() != c["currency"].upper() or s.unit_price > c["price_max_major"]:
        return False
    certs = {x.casefold() for x in (s.certifications or [])}
    if s.certifications is None or any(x.casefold() not in certs for x in c["required_certifications"]):
        return False
    if s.lead_time_days is None or s.lead_time_days > c["max_lead_time_days"]:
        return False
    caps = {x.casefold() for x in (s.customization or [])}
    if s.customization is None or any(x.casefold() not in caps for x in c["required_customization"]):
        return False
    return True


async def evaluate_supplier_search(repo: InMemorySupplierRepository) -> dict[str, Any]:
    cases = load_jsonl(EVAL / "supplier_recall.jsonl")
    usecase = SupplierSearchUseCase(repo)
    suppliers = {s.supplier_id: s for s in await repo.list_all()}
    r10 = []
    r20 = []
    nd10 = []
    hard_total = hard_passed = 0
    surfaced_reasons_total = surfaced_reasons_exact = 0
    qualified_count_exact = 0
    latencies = []
    per_case = []

    for case in cases:
        spec = SupplierSearchSpec(
            normalized_query=case["query"], category=case["category"], quantity=case["quantity"],
            price_max_major=case["price_max_major"], required_certifications=case["required_certifications"],
            max_lead_time_days=case["max_lead_time_days"], required_customization=case["required_customization"],
            top_k=case["top_k"], currency=case["currency"],
        )
        start = time.perf_counter()
        payload = await usecase.execute(spec)
        latencies.append((time.perf_counter() - start) * 1000)
        retrieved = [x["supplier_id"] for x in payload.get("hits", [])]
        relevant = case["relevant_supplier_ids"]
        r10.append(recall_at_k(retrieved, relevant, 10))
        r20.append(recall_at_k(retrieved, relevant, 20))
        nd10.append(ndcg_at_k(retrieved, relevant, 10))
        qualified_count_exact += int(payload.get("qualified_supplier_count") == case["gold_qualified_count"])

        for hit in payload.get("hits", []):
            hard_total += 1
            s = suppliers[hit["supplier_id"]]
            hard_passed += int(independent_hard_pass(s, case))
        for rejected in payload.get("filtered_out", []):
            sid = rejected["supplier_id"]
            expected = case["expected_filtered_out"].get(sid)
            if expected is not None:
                surfaced_reasons_total += 1
                surfaced_reasons_exact += int(set(expected) == set(rejected.get("reason_codes", [])))
        per_case.append({
            "case_id": case["case_id"], "recall10": round(r10[-1], 4), "recall20": round(r20[-1], 4),
            "ndcg10": round(nd10[-1], 4), "qualified_reported": payload.get("qualified_supplier_count"),
            "qualified_gold": case["gold_qualified_count"], "recall_strategy": payload.get("recall_strategy"),
        })

    return {
        "case_count": len(cases),
        "recall_at_10": round(statistics.fmean(r10), 4),
        "recall_at_20": round(statistics.fmean(r20), 4),
        "ndcg_at_10": round(statistics.fmean(nd10), 4),
        "hard_constraint_satisfaction_rate": round(safe_rate(hard_passed, hard_total), 4),
        "qualified_count_exact_rate": round(qualified_count_exact / len(cases), 4),
        "surfaced_filter_reason_exact_rate": round(safe_rate(surfaced_reasons_exact, surfaced_reasons_total), 4),
        "latency_ms": {
            "p50": round(percentile(latencies, .5) or 0, 3), "p95": round(percentile(latencies, .95) or 0, 3),
            "mean": round(statistics.fmean(latencies), 3),
        },
        "strategy": "keyword_2gram fallback (embedding/reranker unavailable in current sandbox)",
        "annotation_note": "relevant supplier order is synthetic rubric-derived, not human supplier judgment",
        "per_case": per_case,
    }


def rfq_from_dict(d: dict[str, Any]) -> RFQ:
    return RFQ(**d)


async def evaluate_decision(repo: InMemorySupplierRepository) -> dict[str, Any]:
    cases = load_jsonl(EVAL / "decision_cases.jsonl")
    membership = []
    ranking = []
    completion = 0
    latencies = []
    per_case = []
    for case in cases:
        rfq = rfq_from_dict(case["rfq"])
        ids = [x["supplier_id"] for x in case["candidates"]]
        by_id = {s.supplier_id: s for s in await repo.find_by_ids(ids)}
        items = []
        for candidate in case["candidates"]:
            q = candidate["quote"]
            ext = normalize_structured_quotation(
                quote_id=candidate["quote_id"], supplier_id=candidate["supplier_id"],
                quantity=q["quantity"], unit_price=q["unit_price"], currency=q["currency"],
                incoterm=q["incoterm"], logo_fee_per_unit=q["logo_fee_per_unit"],
                packaging_fee_per_unit=q["packaging_fee_per_unit"], fixed_fee=q["fixed_fee"],
                lead_time_days=q["lead_time_days"], certifications_confirmed=q["certifications_confirmed"],
            )
            items.append(SupplierQuoteInput(by_id[candidate["supplier_id"]], ext.quotation))
        start = time.perf_counter()
        result = QuotationCompareUseCase().execute(rfq, items, top_k=3)
        latencies.append((time.perf_counter() - start) * 1000)
        pred = [x["supplier_id"] for x in result["shortlist"]]
        gold = case["gold_top3"]
        mem = len(set(pred) & set(gold)) / 3
        membership.append(mem)
        # Pairwise order agreement across the three gold pairs; missing predicted member counts as disagreement.
        pairs = [(gold[0], gold[1]), (gold[0], gold[2]), (gold[1], gold[2])]
        ppos = {sid: i for i, sid in enumerate(pred)}
        agreed = 0
        for a, b in pairs:
            if a in ppos and b in ppos and ppos[a] < ppos[b]:
                agreed += 1
        rank_agree = agreed / len(pairs)
        ranking.append(rank_agree)
        ok = len(pred) == 3 and all(x["hard_constraints_passed"] for x in result["shortlist"])
        completion += int(ok)
        per_case.append({"case_id": case["case_id"], "predicted_top3": pred, "gold_top3": gold, "membership": round(mem, 4), "ranking_agreement": round(rank_agree, 4)})
    return {
        "case_count": len(cases),
        "top3_membership_agreement": round(statistics.fmean(membership), 4),
        "ranking_pairwise_agreement": round(statistics.fmean(ranking), 4),
        "offline_task_completion_rate": round(completion / len(cases), 4),
        "latency_ms": {"p50": round(percentile(latencies,.5) or 0,3), "p95": round(percentile(latencies,.95) or 0,3)},
        "annotation_note": "gold is an independent synthetic rubric (45% cost/30% reliability/20% lead/5% MOQ), not human procurement labels",
        "per_case": per_case,
    }


def render_report(report: dict[str, Any]) -> str:
    r=report["rfq"]; q=report["quotation"]; s=report["supplier_search"]; d=report["decision"]
    lines=[
        "# B2B Sourcing Offline Evaluation Report", "",
        "> Scope: dependency-light offline benchmark over synthetic `mvp_seed` suppliers and synthetic gold cases. "
        "These are reproducible engineering/product-evaluation results, not production-user metrics.", "",
        "## Executive summary", "",
        "| Metric | Result | Evidence boundary |", "|---|---:|---|",
        f"| RFQ schema valid rate | {r['schema_valid_rate']:.1%} | 50 offline RFQ cases |",
        f"| RFQ micro field accuracy | {r['micro_field_accuracy']:.1%} | regex fallback, not live LLM extraction |",
        f"| Critical constraint recall | {r['critical_constraint_recall']:.1%} | explicit product/qty/price/cert/lead labels |",
        f"| Quotation micro field accuracy | {q['micro_field_accuracy']:.1%} | {q['case_count']} mixed-format quote cases |",
        f"| Cost calculation accuracy | {q['cost_calculation_accuracy']:.1%} | {q['cost_calculation_case_count']} fully specified cost cases |",
        f"| Supplier Recall@10 | {s['recall_at_10']:.1%} | keyword fallback in current sandbox |",
        f"| Supplier Recall@20 | {s['recall_at_20']:.1%} | keyword fallback in current sandbox |",
        f"| NDCG@10 | {s['ndcg_at_10']:.3f} | synthetic relevance order |",
        f"| Hard constraint satisfaction | {s['hard_constraint_satisfaction_rate']:.1%} | independent rule recheck on returned hits |",
        f"| Top-3 membership agreement | {d['top3_membership_agreement']:.1%} | independent synthetic decision rubric |",
        f"| Ranking pairwise agreement | {d['ranking_pairwise_agreement']:.1%} | independent synthetic decision rubric |",
        f"| Offline task completion | {d['offline_task_completion_rate']:.1%} | decision use case, not live AgentScope |",
        "", "## RFQ extraction", "",
        f"Cases: {r['case_count']}; parser strategy: {r['parser_strategy']}.", "",
        "| Field | Accuracy |", "|---|---:|",
    ]
    for field,val in r['field_accuracy'].items(): lines.append(f"| {field} | {val:.1%} |")
    lines += ["", f"Conflict detection: precision {r['conflict_detection']['precision']:.1%}, recall {r['conflict_detection']['recall']:.1%}, F1 {r['conflict_detection']['f1']:.1%}.", "",
              "Exact-case accuracy by case type: " + ", ".join(f"{k}={v:.1%}" for k,v in r['exact_case_accuracy_by_type'].items()) + ".", "",
              "## Quotation extraction", "", f"Cases: {q['case_count']}; {q['parser_strategy']}.", "", "| Field | Accuracy |", "|---|---:|"]
    for field,val in q['field_accuracy'].items(): lines.append(f"| {field} | {val:.1%} |")
    lines += ["", "## Supplier retrieval and hard constraints", "",
              f"Current runtime strategy: `{s['strategy']}`. Retrieval latency P50={s['latency_ms']['p50']} ms, P95={s['latency_ms']['p95']} ms. "
              "This latency excludes network embedding/reranking because those dependencies are unavailable here.", "",
              f"Qualified-count exact agreement: {s['qualified_count_exact_rate']:.1%}. Surfaced filter-reason exact agreement: {s['surfaced_filter_reason_exact_rate']:.1%}.", "",
              "The hard-constraint satisfaction rate is the safety-critical metric: every returned hit is rechecked independently against MOQ, price/currency, certifications, lead time and customization.", "",
              "## Error taxonomy", "",
              "- **RFQ unlabeled deadline:** standalone phrases such as `30 days` without `lead time/交期/以内` are intentionally not always interpreted as delivery constraints by the conservative fallback.",
              "- **RFQ revisions/conflicts:** phrases such as `3000 pcs; actually 5000 pcs` can change which value is selected even when a conflict is detected. Conflict recall is therefore reported separately.",
              "- **Quote non-point prices:** ranges (`USD 3.60-3.90`) and approximate prices (`approx. $3.70`) can be over-eagerly collapsed to a point by the regex fallback.",
              "- **Quote locale/unit normalization:** decimal comma (`3,65`), `per 100 pcs`, and week-based lead times are adversarial gaps in the fallback parser.",
              "- **Ranking preference mismatch:** Top-3 membership is stronger than pairwise order agreement, showing that shortlist qualification is more stable than exact soft-rank ordering.", "",
              "## Procurement decision", "",
              f"10 decision cases were compared with a deliberately different synthetic gold rubric. System Top-3 membership agreement={d['top3_membership_agreement']:.1%}; pairwise order agreement={d['ranking_pairwise_agreement']:.1%}. "
              "This measures ranking behavior against a benchmark rubric, not buyer preference or production acceptance.", "",
              "## Metrics not claimed", "",
              "- **Live Agent Task Completion / Tool Success / Average Tool Calls / Token Cost:** not measured because AgentScope/LLM runtime dependencies are unavailable in this sandbox.",
              "- **Manual TTQS:** not measured because no human participant has performed and timed the 10-task manual baseline. No synthetic timing is substituted.",
              "- **Production ROI:** not measured. `docs/roi-benchmark.md` only contains scenario-based Projected ROI formulas and assumptions.", "",
              "## Reproduce", "", "```bash", "python scripts/eval_sourcing.py", "```", "",
              "Input datasets: `eval/rfq_cases.jsonl`, `eval/quotation_cases.jsonl`, `eval/supplier_recall.jsonl`, `eval/decision_cases.jsonl`.", ""]
    return "\n".join(lines)


async def main() -> None:
    repo=InMemorySupplierRepository()
    report={
        "rfq": evaluate_rfq(),
        "quotation": evaluate_quotation(),
        "supplier_search": await evaluate_supplier_search(repo),
        "decision": await evaluate_decision(repo),
        "unmeasured": {
            "live_agent_metrics": "blocked by missing AgentScope/LLM runtime in current sandbox",
            "manual_ttqs": "requires a human participant and stopwatch; intentionally not fabricated",
            "token_cost_per_task": "requires live model gateway usage records",
            "production_roi": "not applicable to offline MVP",
        },
    }
    (EVAL/'b2b-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (EVAL/'b2b-eval-report.md').write_text(render_report(report),encoding='utf-8')
    print(json.dumps({
        'rfq_schema_valid_rate':report['rfq']['schema_valid_rate'],
        'rfq_field_accuracy':report['rfq']['micro_field_accuracy'],
        'critical_constraint_recall':report['rfq']['critical_constraint_recall'],
        'quotation_field_accuracy':report['quotation']['micro_field_accuracy'],
        'cost_calculation_accuracy':report['quotation']['cost_calculation_accuracy'],
        'recall_at_10':report['supplier_search']['recall_at_10'],
        'recall_at_20':report['supplier_search']['recall_at_20'],
        'ndcg_at_10':report['supplier_search']['ndcg_at_10'],
        'hard_constraint_satisfaction_rate':report['supplier_search']['hard_constraint_satisfaction_rate'],
        'top3_membership_agreement':report['decision']['top3_membership_agreement'],
        'ranking_pairwise_agreement':report['decision']['ranking_pairwise_agreement'],
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
