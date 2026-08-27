# B2B Sourcing Offline Evaluation Report

> Scope: dependency-light offline benchmark over synthetic `mvp_seed` suppliers and synthetic gold cases. These are reproducible engineering/product-evaluation results, not production-user metrics.

## Executive summary

| Metric | Result | Evidence boundary |
|---|---:|---|
| RFQ schema valid rate | 100.0% | 50 offline RFQ cases |
| RFQ micro field accuracy | 98.7% | regex fallback, not live LLM extraction |
| Critical constraint recall | 96.3% | explicit product/qty/price/cert/lead labels |
| Quotation micro field accuracy | 97.5% | 35 mixed-format quote cases |
| Cost calculation accuracy | 100.0% | 19 fully specified cost cases |
| Supplier Recall@10 | 96.7% | keyword fallback in current sandbox |
| Supplier Recall@20 | 100.0% | keyword fallback in current sandbox |
| NDCG@10 | 0.716 | synthetic relevance order |
| Hard constraint satisfaction | 100.0% | independent rule recheck on returned hits |
| Top-3 membership agreement | 90.0% | independent synthetic decision rubric |
| Ranking pairwise agreement | 73.3% | independent synthetic decision rubric |
| Offline task completion | 100.0% | decision use case, not live AgentScope |

## RFQ extraction

Cases: 50; parser strategy: dependency-free regex fallback; production path remains LLM structured extraction + validation.

| Field | Accuracy |
|---|---:|
| product | 100.0% |
| quantity | 96.0% |
| target_price | 100.0% |
| currency | 100.0% |
| material | 100.0% |
| specifications | 100.0% |
| customization | 100.0% |
| required_certifications | 100.0% |
| max_lead_time_days | 88.0% |
| destination | 100.0% |
| preferred_incoterm | 100.0% |
| missing_required_fields | 100.0% |

Conflict detection: precision 100.0%, recall 70.0%, F1 82.3%.

Exact-case accuracy by case type: complete=95.0%, conflict=50.0%, missing=93.3%, no_match=80.0%.

## Quotation extraction

Cases: 35; conservative regex fallback for offline eval; unknown fields remain null.

| Field | Accuracy |
|---|---:|
| unit_price | 88.6% |
| currency | 100.0% |
| incoterm | 100.0% |
| logo_fee_per_unit | 97.1% |
| packaging_fee_per_unit | 97.1% |
| fixed_fee | 100.0% |
| lead_time_min_days | 97.1% |
| lead_time_max_days | 97.1% |
| certifications_confirmed | 100.0% |

## Supplier retrieval and hard constraints

Current runtime strategy: `keyword_2gram fallback (embedding/reranker unavailable in current sandbox)`. Retrieval latency P50=4.87 ms, P95=5.723 ms. This latency excludes network embedding/reranking because those dependencies are unavailable here.

Qualified-count exact agreement: 100.0%. Surfaced filter-reason exact agreement: 100.0%.

The hard-constraint satisfaction rate is the safety-critical metric: every returned hit is rechecked independently against MOQ, price/currency, certifications, lead time and customization.

## Error taxonomy

- **RFQ unlabeled deadline:** standalone phrases such as `30 days` without `lead time/交期/以内` are intentionally not always interpreted as delivery constraints by the conservative fallback.
- **RFQ revisions/conflicts:** phrases such as `3000 pcs; actually 5000 pcs` can change which value is selected even when a conflict is detected. Conflict recall is therefore reported separately.
- **Quote non-point prices:** ranges (`USD 3.60-3.90`) and approximate prices (`approx. $3.70`) can be over-eagerly collapsed to a point by the regex fallback.
- **Quote locale/unit normalization:** decimal comma (`3,65`), `per 100 pcs`, and week-based lead times are adversarial gaps in the fallback parser.
- **Ranking preference mismatch:** Top-3 membership is stronger than pairwise order agreement, showing that shortlist qualification is more stable than exact soft-rank ordering.

## Procurement decision

10 decision cases were compared with a deliberately different synthetic gold rubric. System Top-3 membership agreement=90.0%; pairwise order agreement=73.3%. This measures ranking behavior against a benchmark rubric, not buyer preference or production acceptance.

## Metrics not claimed

- **Live Agent Task Completion / Tool Success / Average Tool Calls / Token Cost:** not measured because AgentScope/LLM runtime dependencies are unavailable in this sandbox.
- **Manual TTQS:** not measured because no human participant has performed and timed the 10-task manual baseline. No synthetic timing is substituted.
- **Production ROI:** not measured. `docs/roi-benchmark.md` only contains scenario-based Projected ROI formulas and assumptions.

## Reproduce

```bash
python scripts/eval_sourcing.py
```

Input datasets: `eval/rfq_cases.jsonl`, `eval/quotation_cases.jsonl`, `eval/supplier_recall.jsonl`, `eval/decision_cases.jsonl`.
