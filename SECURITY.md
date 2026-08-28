# Security Policy

## Public repository rules

本仓库只允许提交：源码、无密钥配置模板、合成示例数据、离线评测和公开文档。

严禁提交：

- `.env`、API Key、Access Token、Cookie、私钥或内部网关地址；
- 数据库文件、Redis/Qdrant 数据目录、会话快照、日志和 Trace；
- 真实供应商、客户、报价、合同、邮箱、电话或个人信息；
- 未脱敏的截图、导出文件与生产评测样本。

## Before every push

```bash
git status --short
git diff --check
rg -n --hidden -g '!uv.lock' -g '!package-lock.json' \
  '(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|-----BEGIN .*PRIVATE KEY-----|api[_-]?key\s*[:=]\s*[^$<{[:space:]]+)'
```

如扫描命中，请先确认是否仅为 `.env.example` 的占位符；任何真实值必须立即撤销并从 Git 历史中清理，仅删除当前文件不足以消除泄露。

## Runtime safety boundary

- LLM 不直接裁决 MOQ、价格、认证、交期和定制能力；
- Hard Constraint、成本计算和排序由确定性代码执行；
- `unknown` 不等于满足约束；
- 自动询价、议价、定标、合同、付款与下单不属于当前产品能力；
- 涉及外部动作时必须保留人工确认。

## Reporting

公开仓库不应接收包含真实敏感数据的 Issue。发现安全问题时，请通过仓库所有者提供的私有渠道报告，并仅提供复现所需的最小信息。
