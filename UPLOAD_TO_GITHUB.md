# GitHub 上传说明

## 推荐方式

1. 解压交付的 ZIP；
2. 在 GitHub 新建一个空仓库，建议命名 `sourcepilot`；
3. 首次上传时建议先设为 **Private**，确认页面和提交历史无敏感内容后再决定是否公开；
4. 上传解压目录中的全部内容，不要把外层 ZIP 本身提交进仓库；
5. 不要创建或上传真实 `.env`、数据库、缓存、日志与真实业务数据。

## 命令行上传

```bash
git init
git branch -M main
git add .
git status --short
git commit -m "feat: publish SourcePilot portfolio edition"
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

## 上传前检查

```bash
git status --short
git diff --cached --check
test ! -f .env
find . -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.log' \)
```

预期结果：不存在 `.env`、数据库或日志文件；`.env.example` 可以上传。

## 上传后检查

- README 首页显示“寻策 SourcePilot”；
- GitHub Actions 的后端测试、离线评测和前端构建通过；
- `eval/` 明确标注为合成数据；
- 仓库中没有真实 API Key、邮箱、电话、客户或供应商信息；
- 确认是否需要增加开源许可证。当前包默认未授权开源复用。
