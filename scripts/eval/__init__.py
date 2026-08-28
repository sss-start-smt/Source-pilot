# -*- coding: utf-8 -*-
"""SourcePilot 离线评测脚手架。

评测是离线工具，不属于运行时应用，因此放在 `scripts/eval/` 而非 `app/`：

    metrics.py               Recall@K / MRR / NDCG@K 纯函数与聚合

主评测入口为 `scripts/eval_sourcing.py`，覆盖 RFQ、报价、成本、供应商召回、
硬约束和决策排序；全程使用合成数据，可在 CI 中复现。
"""
