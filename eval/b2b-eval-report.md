# B2B 寻源离线评测报告

> 范围：基于合成 `mvp_seed` 供应商与合成 gold case 的轻依赖离线 benchmark。这些是可复现的工程 / 产品评测结果，不是生产用户指标。

## 结果摘要

| 指标 | 结果 | 证据边界 |
|---|---:|---|
| RFQ Schema 合法率 | 100.0% | 50 条离线 RFQ case |
| RFQ 微观字段准确率 | 98.7% | regex 降级方案，非 live LLM 抽取 |
| 关键约束召回率 | 96.3% | 显式 product/qty/price/cert/lead 标签 |
| 报价微观字段准确率 | 97.5% | 35 条混合格式报价 case |
| 成本计算准确率 | 100.0% | 19 条字段完整的成本 case |
| 供应商 Recall@10 | 96.7% | 当前沙箱 keyword 降级 |
| 供应商 Recall@20 | 100.0% | 当前沙箱 keyword 降级 |
| NDCG@10 | 0.716 | 合成相关性排序 |
| 硬约束满足率 | 100.0% | 对返回 hits 的独立规则复核 |
| Top-3 成员一致率 | 90.0% | 独立合成决策 rubric |
| 成对排序一致率 | 73.3% | 独立合成决策 rubric |
| 离线任务完成率 | 100.0% | 决策 use case，非 live AgentScope |

## RFQ 抽取

Case 数：50；解析器策略：无依赖 regex 降级方案；生产路径仍为 LLM 结构化抽取 + 校验。

| 字段 | 准确率 |
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

冲突检测：precision 100.0%，recall 70.0%，F1 82.3%。

按 case 类型的精确一致率：complete=95.0%，conflict=50.0%，missing=93.3%，no_match=80.0%。

## 报价抽取

Case 数：35；面向离线评测的保守 regex 降级方案；未知字段保持 null。

| 字段 | 准确率 |
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

## 供应商召回与硬约束

当前运行策略：`keyword_2gram 降级（当前沙箱无法使用 embedding/reranker）`。检索延迟 P50=4.208 ms，P95=5.209 ms。该延迟不含网络 embedding/rerank，因为这些依赖在当前环境不可用。

合格数量精确一致率：100.0%。暴露过滤原因精确一致率：100.0%。

硬约束满足率是安全关键指标：每一条返回 hit 都被独立规则按 MOQ、价格/币种、认证、交期与定制重新核验。

## 错误分类

- **RFQ 无标签交期：**保守降级方案有意不把 `30 days` 这类没有 `lead time/交期/以内` 标签的孤立短语全部解释为交期约束。
- **RFQ revision/冲突：**`3000 pcs; actually 5000 pcs` 这类措辞即使检测到冲突，也可能选中修订后的值。因此冲突召回单独上报。
- **报价非点价：**区间价（`USD 3.60-3.90`）与近似价（`approx. $3.70`）可能被 regex 降级方案过早压缩成点价。
- **报价本地化/单位归一：**小数逗号（`3,65`）、`per 100 pcs`、按周计交期是降级解析器的对抗性缺口。
- **排序偏好不匹配：**Top-3 成员一致性强于成对排序一致率，说明 shortlist 资格判断比精确软排序更稳定。

## 采购决策

10 条决策 case 与一套刻意不同的合成 gold rubric 对比。系统 Top-3 成员一致率=90.0%；成对排序一致率=73.3%。这度量的是排序行为相对 benchmark rubric 的一致性，不是买家偏好或生产接受度。

## 不宣称的指标

- **Live Agent 任务完成率 / 工具成功率 / 平均工具调用次数 / token 成本：**未测量，因为当前沙箱缺少 AgentScope/LLM 运行时依赖。
- **Manual TTQS：**未测量，因为尚无真人参与者执行并计时 10 任务人工基线。没有用合成计时值替代。
- **生产 ROI：**未测量。`docs/roi-benchmark.md` 只包含基于场景的预测性 ROI 公式与假设。

## 复现方式

```bash
python scripts/eval_sourcing.py
```

输入数据集：`eval/rfq_cases.jsonl`、`eval/quotation_cases.jsonl`、`eval/supplier_recall.jsonl`、`eval/decision_cases.jsonl`。
