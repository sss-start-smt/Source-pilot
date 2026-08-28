# SourcePilot MVP PRD

## 1. 产品概述

**产品名：** 寻策 SourcePilot  
**产品定位：** AI Sourcing & Supplier Decision Copilot  
**版本：** MVP / Portfolio Edition  
**目标：** 将非结构化采购需求转换为结构化 RFQ，并基于可验证事实生成可比较、可追溯、可人工复核的供应商 Shortlist。

## 2. 用户与场景

### 2.1 目标用户

- 中小跨境电商团队采购专员；
- 外贸公司采购负责人；
- 多品类、小团队、依赖聊天和表格协作的采购团队。

### 2.2 核心任务

> 当采购人员收到一个非结构化采购需求时，希望快速补齐 RFQ、筛掉不满足硬条件的供应商、统一报价口径，并形成有证据的 Top-3，以便进入人工询价或评审。

## 3. 产品目标与非目标

### 3.1 产品目标

- 降低 RFQ 整理和供应商初筛时间；
- 避免 MOQ、价格、认证、交期和定制能力违规候选进入 Shortlist；
- 将多种报价转换为统一、可解释的成本口径；
- 为每个候选保留事实、过滤原因、未知项和风险说明。

### 3.2 非目标

- 不自动执行询价、议价、定标、签约、付款或下单；
- 不承诺实时覆盖外部平台供应商；
- 不对未知字段进行模型补全；
- 不使用合成评测结果宣传真实业务收益。

## 4. 核心流程

1. 采购人员输入自然语言需求；
2. 系统抽取 RFQ，并展示缺失或冲突字段；
3. 关键字段缺失时定向追问；
4. RFQ 完整后召回供应商；
5. Hard Gate 输出 qualified 与 filtered_out；
6. 用户输入或导入候选报价；
7. 系统抽取报价字段并复算有效单价；
8. 仅在合格候选中进行排序；
9. 输出 Top-3、优势、风险、未知字段和人工确认项。

## 5. 功能需求

| 编号 | 模块 | 功能 | 验收标准 | 优先级 |
|---|---|---|---|---|
| FR-01 | RFQ | 抽取 product、quantity、target price、currency、certification、lead time、customization | 未提供的数字不得猜测；必填缺失需追问 | P0 |
| FR-02 | RFQ | 冲突检测 | 数量、币种、价格等明显冲突需标记 | P0 |
| FR-03 | Retrieval | 供应商候选召回 | 返回候选、检索策略和来源 | P0 |
| FR-04 | Hard Gate | 校验 MOQ、价格、认证、交期、定制 | 失败候选不能进入 qualified；返回固定原因码 | P0 |
| FR-05 | Quote | 抽取报价、费用、贸易术语和交期区间 | 缺失字段为 null/unknown；原始数字不改写 | P0 |
| FR-06 | Cost | 复算 Effective Unit Cost | 完整 case 计算准确率 100%；口径不完整时标 Partial | P0 |
| FR-07 | Decision | 在合格候选中生成 Top-3 | 排名由确定性代码生成，解释不得改分 | P0 |
| FR-08 | Memory | 记忆白名单企业采购偏好 | 当前 RFQ 显式条件优先；支持精确撤回 | P1 |
| FR-09 | Observability | 展示 Agent、工具、过滤、报价与最终结果事件 | 按会话隔离；内部敏感信息不进入最终回复 | P1 |
| FR-10 | Safety | 输出过滤、循环检测、超时与熔断 | 故障时降级或报错，不补造数据 | P0 |

## 6. 数据与规则

### 6.1 RFQ 最小字段

- `product`：必填；
- `quantity`：必填；
- `target_price`、`currency`：可选；
- `required_certifications`：可选数组；
- `max_lead_time_days`：可选；
- `customization`：可选数组；
- `material`、`specifications`、`destination`、`preferred_incoterm`：可选。

### 6.2 Hard Gate 原因码

- `moq_too_high`；
- `price_above_target`；
- `missing_certification`；
- `lead_time_too_long`；
- `customization_unsupported`。

供应商字段缺失时状态为 `unknown`，不得默认视为通过。

### 6.3 成本口径

Effective Unit Cost 由单价、单位 Logo 费、单位包装费和分摊固定费组成。运费、关税和税费缺失时，只能展示 Estimated / Partial Cost，不得称为完整 Landed Cost。

## 7. Agent 架构与职责

- **Procurement Supervisor**：主会话、任务计划、路由、偏好注入和结果汇总；
- **Sourcing Agent**：结构化检索条件、调用供应商召回、解释 qualified/filtered；
- **Quote Agent**：抽取报价、调用成本与比较工具、解释排序。

RFQ Parser、Hard Constraint Engine、Cost Calculator、Ranking 和 Decision Explanation 为能力模块，不独立 Agent 化。

## 8. 交互要求

- 首屏突出 RFQ 输入与示例需求；
- RFQ 字段、候选供应商、过滤原因和报价比较分区展示；
- `unknown`、`filtered_out` 和 `needs_human_approval` 需要明显状态；
- 不使用“系统已联系/已定标/已采购”等越权完成态文案；
- 错误态说明失败原因和可执行的恢复动作。

## 9. 非功能需求

- 所有会话、事件和偏好按采购账号隔离；
- 密钥仅通过环境变量注入；
- 数据库、日志、缓存和真实数据不得进入公开仓库；
- 可选依赖失败时支持确定性降级；
- 核心规则具备单元测试和离线回归；
- 公开数据集必须标注 synthetic / mvp_seed。

## 10. 评测与上线门槛

MVP 基线：

- RFQ Schema 合法率：100%；
- Hard Constraint 满足率：100%；
- 完整成本 case 计算准确率：100%；
- Supplier Recall@10：不低于 95%；
- 所有安全边界测试通过；
- 前端生产构建通过；
- 密钥、PII、数据库和日志扫描无命中。

## 11. 指标

### 北极星指标

周有效采购决策数（WQSD）。

### 过程指标

- RFQ 完成率；
- TTQS；
- qualified supplier 数；
- Shortlist 接受/调整/拒绝率；
- 人工覆盖原因分布；
- 每个有效决策的模型成本。

### 护栏指标

- Hard Constraint 违规率；
- 无证据事实率；
- 未知字段错误通过率；
- 外部动作越权率。

## 12. 里程碑

| 里程碑 | 交付物 | 退出条件 |
|---|---|---|
| M0 机制验证 | Schema、Hard Gate、Cost、Ranking | 合成单测通过 |
| M1 MVP | 1+2 Agent、UI、事件流、离线评测 | P0 门槛通过 |
| M2 Pilot | 脱敏真实任务、人工反馈、TTQS | 形成可解释的接受/调整数据 |
| M3 私有接入 | 企业供应商数据、权限与审计 | 数据授权和安全评审通过 |
