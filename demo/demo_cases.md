# SourcePilot Demo Cases

> 三个固定的离线 demo 场景。每个场景都对应 evaluation 数据集中至少一个 case，用于：
> 1. 校验硬约束筛选是否正确剔除不达标供应商；
> 2. 校验报价归一与 Ranking 是否稳定；
> 3. 在没有真实买家数据时给出一个"可重复讲故事"的脚本。

完整的 5 分钟 Demo 文案与逐句讲法见 [docs/interview-package.md](../docs/interview-package.md)。

---

## Case A — 保温杯（vacuum flask）

**采购原话**

> 找 5000 个 750ml 304 不锈钢保温杯，要做激光 Logo，需要 LFGB，FOB 单价最好不超过 4 美元，30 天内出货。

**期望 RFQ**

```json
{
  "product": "vacuum flask",
  "quantity": 5000,
  "target_price": 4.0,
  "currency": "USD",
  "material": ["304 stainless steel"],
  "specifications": {"capacity_ml": 750},
  "customization": ["laser logo"],
  "required_certifications": ["LFGB"],
  "max_lead_time_days": 30,
  "preferred_incoterm": "FOB"
}
```

**Hard Gate**

```text
moq <= 5000
unit_price <= 4.0
LFGB ∈ certifications
lead_time_days <= 30
laser logo ∈ customization
```

**离线实测（sandbox keyword_2gram fallback）**

- Qualified suppliers: 6
- Top retrieval hits include `SUP-VF-001 / SUP-VF-011 / SUP-VF-021`
- 通过完整 supplier_search_tool（embedding + reranker）后命中数会更高，且在真实买家偏好下排序会进一步收敛。

**怎么跑**

```bash
python scripts/demo_supplier_search.py
```

---

## Case B — 尼龙背包（nylon backpack）

**采购原话**

> 2000 个 nylon backpack，需要 custom logo 和 luggage strap，目标价 6.5 USD，30 天出货。

**期望 RFQ**

```json
{
  "product": "nylon backpack",
  "quantity": 2000,
  "target_price": 6.5,
  "currency": "USD",
  "customization": ["custom logo", "luggage strap"],
  "required_certifications": ["REACH"],
  "max_lead_time_days": 30,
  "preferred_incoterm": "FOB"
}
```

**Hard Gate**

```text
moq <= 2000
unit_price <= 6.5
REACH ∈ certifications
lead_time_days <= 30
custom logo ∈ customization AND luggage strap ∈ customization
```

**怎么跑**

```bash
python scripts/demo_supplier_search.py --case backpack
```

---

## Case C — 电子配件（USB-C PD / QC / 12V / 24V）

**采购原话**

> 找 3000 个 USB-C PD 3.0 / QC 4.0 控制器，12V / 24V 通用，目标价 3.0 USD，25 天出货。

**观察重点**

- 精确属性（USB-C PD 3.0 / QC 4.0 / 12V / 24V）会区分 semantic retrieval 与 exact attribute 匹配的差异；
- 当前 sandbox 走 `keyword_2gram` fallback 时，相关但非精确命中的供应商仍可能出现在候选里；
- 完整 `embedding + reranker` 路径能进一步把纯字面命中压回精确属性匹配。

**怎么跑**

```bash
python scripts/demo_supplier_search.py --case electronics
```

---

## 离线 smoke

```bash
python scripts/smoke_b2b_e2e.py
```

当前记录：3/3 Case 通过（sandbox fallback 路径；live LLM / vector / reranker 路径未在当前沙箱运行）。
