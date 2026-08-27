# SourcePilot — Data

> 本目录仅放置**示例 / 标注**数据。运行时持久化（sessions/、orders/、qdrant/、*.db、*.sqlite3 等）全部不入 Git。

## 文件

- `sample_suppliers.csv` — 从 `app/infrastructure/persistence/seed_suppliers.py` 抽 30 行代表性记录（3 个 demo 品类各 10 行），方便外部审计与离线分析。

## 重新生成

```bash
python scripts/_build_sample_csv.py
```

## 字段

```text
supplier_id          # 业务 ID，例 SUP-VF-001
company_name         # 合成名（all "Northstar Drinkware NNN" 等）
business_type        # manufacturer / manufacturer+trading / trading
category             # 品类
product_text         # 检索用的拼接文本
moq                  # 最小起订量
unit_price           # 单价
currency             # ISO 4217
incoterms            # EXW|FOB|CIF ...
lead_time_days       # 交期
certifications       # LFGB|FDA ...
customization        # laser logo|custom box ...
years_in_business    # 经营年限
export_markets       # US|EU|JP ...
reliability_score    # 0-1
source               # mvp_seed
```

所有 `source=mvp_seed` 的数据是合成的，不代表任何真实平台供应商。
