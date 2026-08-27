# SourcePilot — Architecture (DDD 洋葱 + Multi-Agent)

> 本文档是 README 引用的 `architecture.md`。详细产品 brief 见 [b2b-product-brief.md](b2b-product-brief.md)，
> 数据 schema 见 [b2b-schemas.md](b2b-schemas.md)，执行节奏见 [B2B_Sourcing_Agent_7Day_Execution_Plan.md](B2B_Sourcing_Agent_7Day_Execution_Plan.md)。

## 1. 分层

```text
                ┌──────────────────────────┐
                │  presentation (FastAPI)  │
                └────────────┬─────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │            application (用例/工具/Agent) │
        │  usecases · tools · agents · prompts     │
        │  harness (assertions / loop / drift)     │
        └────────────────────┬────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │              domain (纯领域模型)         │
        │  procurement · supplier · quotation     │
        │  catalog · order · buyer · session ...   │
        └────────────────────┬────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │     infrastructure (外部世界 / 副作用)   │
        │  LLM · Qdrant · Redis · Persistence     │
        │  Reranker · Tracing · Resilience        │
        └────────────────────────────────────────┘
```

依赖方向：**外 → 内**。Domain 不知道 LLM / DB；Application 只通过 Port 与 Infrastructure 交互。

## 2. Agent 拓扑

```text
ProcurementConcierge (Supervisor)
├── supplier_search_tool            # 简单单品类直接调
├── remember / forget preference    # 长期偏好写路径
└── task_dispatch (按需)
    ├── SourcingAgent
    └── QuoteAgent
```

Multi-Agent 是**按条件启用**的：一次简单寻源直接调 supplier_search_tool；多个独立品类 / 大段报价 / 长上下文时才 dispatch 子 Agent。

## 3. Hard Gate vs Soft Rank

```text
LLM / Agent
├── 理解 NL 采购需求
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

**Hard Gate 在 Soft Rank 之前执行**。语义高相关度不能把硬约束失败的供应商重新带回 Qualified Shortlist。

## 4. 顶层 facade（app/agents, app/tools, app/models, app/config）

为了对外暴露稳定的入口（README / 外部脚本 / 集成测试 / OpenAPI 生成器），
仓库在 `app/` 根下提供 4 个**薄门面**目录：

| 门面目录 | 对应实现 |
|---|---|
| `app/agents/` | `app.application.agents.*` |
| `app/tools/` | `app.application.usecases.*` / `app.application.tools.*` |
| `app/models/schemas.py` | `app.domain.*` 全部数据模型 |
| `app/config/settings.py` | `app.infrastructure.settings` |

DDD 内部分层（domain / application / infrastructure / presentation）保持不变。

## 5. 数据流（单次寻源）

```text
user message
   │
   ▼
MainAgentOrchestrator
   │
   ▼
supplier_search_tool (FunctionTool)
   │
   ▼
SupplierSearchUseCase
   ├── Retrieval: Embedding → Qdrant → HTTP Reranker
   │      (fallback) keyword_2gram
   ├── Hard Gate: MOQ / Price / Cert / Lead / Customization
   └── Soft Rank: requirement_match 35% / effective_cost 25% /
                  lead_time 15% / reliability 15% / moq_flex 10%
   │
   ▼
Supplier Cards → 事件流 (token.delta / plan.update / final.result)
```

## 6. 可选外部依赖（全部按"空即降级"设计）

- LLM: OpenAI-compatible（qwen3-max / 其它）
- Embedding: OpenAI-compatible（text-embedding-v4 / 其它）
- Vector DB: Qdrant（缺省本地嵌入模式）
- Reranker: HTTP Reranker
- Cache / Queue / Backplane: Redis Stream
- Persistence: SQLite / JSON 文件
- Tracing: OTLP

## 7. 护栏（Harness）

- 循环检测（LoopDetector）
- 漂移检测（DriftDetector, 默认关）
- 单步断言（SequencingTracker）
- L3 内容过滤 + 输出 Guard
- Circuit Breaker + Tool Timeout
- Token 预算 + 网关限流
