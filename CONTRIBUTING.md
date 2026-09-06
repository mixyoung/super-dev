# 贡献指南 | Contributing Guide

感谢你对 Super Dev 的贡献！/ Thank you for contributing to Super Dev!

## 先读项目演进准则 | Read the policy first

所有开发者及使用模型的贡献者先读 [项目演进与贡献准则](docs/CONTRIBUTION_POLICY.md)。它固定产品边界、知识吸纳六问、证据要求与审批责任；模型品牌或能力变化不构成改路线的理由。

知识、方法、生成模板或核心合同改动，在本次已经确认的 change 中填写 `adoption.md`，保留来源版本、现有重合、适用/不适用条件、改动范围、验证和回退。普通无关修订不新增吸纳作业；纯编辑说明无语义变化即可。AI 工具不自动读仓库指令时，请在任务中显式要求读取本文和上述准则。

All contributors, including AI-assisted ones, must follow the linked repository policy. Preserve the host-native product, existing gates and evidence standards. Record the rationale and scope of knowledge/method/core changes; template completeness is not maintainer approval.

## 如何贡献 | How to Contribute

1. 本项目贡献面向 [mixyoung/super-dev](https://github.com/mixyoung/super-dev)，不要误投原作者仓库
2. 在已批准的工作区安排下创建或使用功能分支，默认前缀 `ocx/`；已有分支不重复创建
3. 提交更改并推送到你的 Fork
4. 提交 Pull Request 到 `main` 分支

## 开发环境 | Development Setup

```bash
# 需要 Python 3.10+
pip install -e ".[dev]"
```

## 代码风格 | Code Style

使用 **ruff** 和 **black**，行长度 100 字符。

```bash
ruff check super_dev/        # 检查
ruff check --fix super_dev/  # 自动修复
black super_dev/             # 格式化
mypy super_dev/              # 类型检查
```

## 测试 | Testing

```bash
pytest                              # 全部测试
pytest tests/unit/test_xxx.py -v    # 单文件
pytest --cov=super_dev              # 覆盖率
```

请为新代码添加对应的单元测试。

## 提交规范 | Commit Conventions

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(scope): description    # 新功能
fix(scope): description     # 修复
docs: description           # 文档
ci: description             # CI/CD
chore: description          # 维护
```

常用 scope：`orchestrator`、`enforcement`、`cli`、`website`、`hosts`。

## PR 要求 | PR Requirements

- 清晰的 PR 描述，说明变更原因和内容
- 所有测试通过（`pytest`）
- Lint 通过（`ruff check` + `black --check`）
- 新功能需包含测试用例
- 使用仓库 PR 模板，明确范围、证据、未验证项与吸纳记录（不适用时说明）
- 运行 `python scripts/check_contribution_policy.py --base <本轮基线>` 与 `python scripts/sync_super_dev_skills.py`
- 核心方向或验收基准变更需维护者单独审查，不能自行填写“批准”代替真实决定
- CI 通过不自动授权合并/发布；远端保护是否生效以实际仓库设置为准

## 报告问题 | Reporting Issues

请在本项目的 [GitHub Issues](https://github.com/mixyoung/super-dev/issues) 提交 Bug 或功能建议，包含复现步骤和环境信息。
