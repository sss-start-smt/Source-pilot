# 评测设计

## 原则

- 将端到端链路拆成 RFQ、报价、召回、决策四层；
- Hard Constraint 与事实正确性优先于文案质量；
- 同时覆盖完整、缺失、冲突、无匹配和对抗格式；
- 合成离线指标与真实用户指标分开报告。

## 数据集

| 数据集 | Case 数 | 核心指标 |
|---|---:|---|
| `rfq_cases.jsonl` | 50 | Schema 合法率、字段准确率、约束召回、冲突检测 |
| `quotation_cases.jsonl` | 35 | 字段准确率、成本计算准确率 |
| `supplier_recall.jsonl` | 30 | Recall@K、NDCG@10、Hard Constraint 满足率 |
| `decision_cases.jsonl` | 10 | Top-3 成员一致率、成对排序一致率 |

全部数据均为合成样例，不能代表生产供应商质量或真实用户接受度。

## 复现

```bash
uv run python scripts/eval_sourcing.py
```

输出：

- `eval/b2b-eval-results.json`
- `eval/b2b-eval-report.md`

## 当前缺口

- Live Agent 任务完成率尚未测量；
- 真人 TTQS 与人工基线尚未测量；
- Token 成本和生产 ROI 尚未测量；
- 成对排序一致率提示软权重需要真实采购偏好校准。

后续应使用 5–10 名真实采购人员、脱敏任务和人工验收集验证产品指标，不使用合成计时替代真人数据。
