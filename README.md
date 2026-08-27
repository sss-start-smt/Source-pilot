# SourcePilot

> Cross-border Sourcing Copilot for SMB teams — 把自然语言采购需求变成 **constraint-valid、comparable、auditable** 的 Top-3 供应商 Shortlist，并把高风险商业动作保留给人工审批。

> 当前仓库是 **7 天离线 MVP / AI PM Portfolio Project**。供应商数据为明确标记的 `mvp_seed` 合成数据；离线评测不是生产用户效果，Projected ROI 也不是 Production ROI。

## 一句话定位

**SourcePilot**: 面向中小跨境电商 / 贸易团队的 B2B 智能寻源与采购决策 Copilot。把自然语言采购需求转成结构化 RFQ → 供应商召回 → 硬约束筛选 → 报价归一 → 确定性 Ranking → Top-3 候选 + Strength / Risk / Next Action。

## 核心流程

```text
自然语言采购需求
→ RFQ 结构化 / 缺失字段追问
→ Supplier Retrieval
→ Deterministic Hard Constraint Filter
→ Supplier Cards
→ Quotation Parse
→ Effective Unit Cost
→ Deterministic Supplier Ranking
→ Top-3 Shortlist
→ Strength / Risk / Next Action
→ Human Approval
```

P0 不执行真实自动询价、自动议价、定标、合同、下单或付款。`生成询价/谈判建议` 只生成草稿，不自动发送。

## 为什么不是"让 LLM 自己选供应商"

采购决策同时包含非结构化理解和精确商业规则，二者应拆开:

```text
LLM / Agent
├── 理解自然语言采购需求
├── 抽取 RFQ / 报价字段
├── 追问缺失信息
├── 规划 / 调度工具
└── 解释推荐理由

Deterministic Python
├── Schema validation
├── MOQ / 价格 / 认证 / 交期 / 定制 Hard Gate
├── Effective Unit Cost
├── Supplier numeric score
└── Qualified Top-3 校验
```

Hard Gate 在 Soft Rank 之前执行。高语义相关度不能把硬约束失败的供应商重新带回 Qualified Shortlist。

## Agent 架构

```text
ProcurementConcierge (Supervisor / MainAgent)
├── supplier_search_tool
├── remember / forget preference
├── task_dispatch
│   ├── SourcingAgent
│   └── QuoteAgent
└── clarification / explanation

SourcingAgent
└── SupplierSearchUseCase
    ├── embedding → Qdrant → HTTP reranker
    ├── fallback: embedding_only
    └── fallback: keyword_2gram

QuoteAgent
├── quotation_normalize_tool
└── quotation_compare_tool
    └── QuotationCompareUseCase
        ├── schema validation
        ├── effective-cost calculation
        ├── quote-aware hard gate
        └── deterministic ranking
```

Multi-Agent 按任务复杂度条件启用：一次简单寻源由 MainAgent 直接调 Supplier Search；多个独立品类或长报价需要上下文隔离时才 dispatch 子 Agent。

## 顶层包结构

```text
SourcePilot/
├── README.md                 # 本文件
├── LICENSE
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yaml       # 见 docker/
│
├── app/                      # 核心代码（DDD 洋葱架构）
│   ├── agents/               # 顶层入口：supervisor / sourcing_agent / quote_agent
│   ├── tools/                # 顶层入口：supplier_search / quotation_parser / constraint_checker
│   │                         #            / cost_calculator / ranking_engine
│   ├── models/schemas.py     # 顶层入口：跨边界数据模型
│   ├── config/settings.py    # 顶层入口：Settings
│   ├── domain/               # 领域模型：RFQ / Supplier / Quotation ...
│   ├── application/          # 用例 / 工具 / Agent 工厂 / Prompts / 护栏
│   ├── infrastructure/       # Qdrant / Redis / LLM / Persistence ...
│   └── presentation/         # FastAPI 服务
│
├── docs/                     # 产品与设计文档
│   ├── PRD.md
│   ├── architecture.md
│   ├── model-selection.md
│   ├── cost-analysis.md
│   ├── evaluation-report.md
│   └── roadmap.md
│
├── evaluation/               # 评测数据与脚本
│   ├── rfq_cases.json
│   ├── quotation_cases.json
│   ├── supplier_cases.json
│   ├── decision_cases.json
│   ├── run_eval.py
│   └── results/benchmark_report.md
│
├── demo/                     # Demo 展示
│   ├── demo_cases.md
│   ├── demo_video_link.md
│   └── screenshots/
│       ├── workflow.png
│       └── result.png
│
├── data/
│   └── sample_suppliers.csv  # 30 行代表性 seed 供应商数据
│
├── frontend/                 # React + Vite + TypeScript Demo
├── knowledge/                # 品类知识库（保温杯 / 背包 / 电子配件 ...）
├── scripts/                  # demo / smoke / loadtest 脚本
├── docker/                   # docker-compose.yaml
└── tests/                    # 单元测试
```

> 关于 `app/` 内部 DDD 分层（`domain/` / `application/` / `infrastructure/` / `presentation/`）以及与顶层 4 个 facade 目录（`agents/` / `tools/` / `models/` / `config/`）的关系，参见 [docs/architecture.md](docs/architecture.md)。

## 硬约束与报价归一

固定 Supplier Search reason codes：

```text
moq_too_high
price_above_target
missing_certification
lead_time_too_long
customization_unsupported
```

报价比较额外使用：

```text
currency_mismatch
quote_incomplete
```

未知值不会默认算满足。Effective Unit Cost：

```text
Effective Unit Cost
= Unit Price
+ Logo Fee / Unit
+ Packaging Fee / Unit
+ Fixed Fee / Quantity
```

`null` 与 `0` 明确区分。没有真实 freight / duty / tax 数据时，EXW / FOB / CIF 只标记为 **Estimated / Partial Cost**，不宣称 landed cost。

## Ranking

```text
Requirement Match   35%
Effective Cost      25%
Lead Time           15%
Reliability         15%
MOQ Flexibility     10%
```

Historical Preference 5% 尚未做数值化校准，已明确并入 Requirement Match，不留隐性缺项。

## 启动

```bash
uv sync
```

配置 OpenAI-compatible LLM / Embedding：

```bash
cp .env.example .env
# 编辑 .env，至少填 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
```

启动 API：

```bash
uv run uvicorn app.presentation.server:app --port 8000
```

可选 worker（启用 Redis 队列时）：

```bash
uv run python -m app.worker
```

前端 Demo：

```bash
cd frontend
npm ci
npm run dev
```

## 验证

```bash
python scripts/smoke_b2b_e2e.py
python scripts/eval_sourcing.py
python scripts/demo_supplier_search.py
python scripts/demo_quotation_compare.py
```

## 文档

- [docs/PRD.md](docs/PRD.md) — 最终 PRD
- [docs/architecture.md](docs/architecture.md) — DDD / Multi-Agent / 硬约束
- [docs/model-selection.md](docs/model-selection.md) — LLM / Embedding / Reranker 选型
- [docs/cost-analysis.md](docs/cost-analysis.md) — Projected ROI
- [docs/evaluation-report.md](docs/evaluation-report.md) — Benchmark 详细报告
- [docs/roadmap.md](docs/roadmap.md) — 产品路线图
- [evaluation/results/benchmark_report.md](evaluation/results/benchmark_report.md) — 离线评测结果

## License

[MIT](LICENSE) (建议；如需 Apache-2.0 / 商业 License，请替换)
