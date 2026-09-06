# 项目演进与贡献规则：验证记录

> 2026-09-06；本地实现与定向检查通过（PASS）。未提交/推送，远端保护未启用。

## 已完成

- `docs/CONTRIBUTION_POLICY.md` v1 固定产品方向、三层决定权、六问入口、来源/范围/验证要求及远端强制条件。
- AGENTS、两份 Claude 入口、README 中英文、贡献指南和 PR 模板可发现同一准则。三个模型入口中的原生成区块与 HEAD 完全一致，未改发布用 Skill 模板。
- 现有维护策略/评审清单和路线第 9 节明确权威来源，去除按期限强行改写和重组的导向，不增加评分平台。
- `.github/CODEOWNERS` 使用只读核实的仓库所有者 @mixyoung，覆盖规则、知识、产品代码、测试、检查和 CI 自身；没有向原作者赋予本项目审批职责。
- 8 个固定行为案例保留 task/facts/expected/forbidden，明确执行者不看预期答案；这些是评估资产，不是本次已经执行的多模型行为结果。
- 只读脚本检查入口、基准结构、当前差异对应的非空吸纳记录与精确范围；支持多批独立记录，重复认领失败，不按最新时间猜 change。
- 现有 CI 增加 Ubuntu/Windows 的贡献检查 job，读取事件基线（手动触发用上一提交），完整检出历史、令牌仅只读、不保留凭据、不使用 pull_request_target 或忽略失败。

## 实际验证

Windows / 项目 `.venv` Python 3.13.12。

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_contribution_policy.py tests/unit/test_umadev_latest_soft_content.py tests/unit/test_umadev_soft_content.py tests/unit/test_method_absorption.py tests/unit/test_document_generator_enhanced.py tests/unit/test_super_dev_skill_contracts.py tests/unit/test_expert_service.py tests/unit/test_engine_knowledge.py tests/unit/test_workflow_contract.py tests/unit/test_workflow_guard_active_change.py tests/unit/test_new_modules.py::TestSkillTemplate tests/unit/test_new_modules.py::TestExpertLoader tests/unit/test_spec_manager.py tests/unit/test_spec_manager_enhanced.py -q -p no:cacheprovider --junitxml=output/contribution-policy-pytest.xml
```

结果：221 passed，0 failed/errors/skipped；终端 9.31 秒，JUnit 9.195 秒。21 项为新增贡献检查用例，其余 200 项为既有相关回归。

新增检查覆盖：无关改动不额外阻塞、缺入口、缺本批记录、旧记录不可冒充本批记录、漏列文件、重复归属、空/重复章节、越界/模糊路径、中文/空格/方括号字面路径、基准缺项/重复/空列表、无效 Git 基线、暂存/未暂存/未跟踪/已提交及改名两端、CLI 失败退出码和 CI 权限/检查接线。

首次用例暴露单独 `.` 路径未被拒绝，已补验证并复跑；没有删除失败断言。真实工作区无记录时脚本返回失败，补齐新贡献批次与前一 U7—U14 各自记录后通过。前一批补录仅为贡献元数据，未重写其实现与验证结果。

通过：Ruff、两份新 Python 的 Black 检查、检查脚本 Mypy（仅既有 unused-section 提示）、`git diff --check`、`scripts/sync_super_dev_skills.py`。本地命令 `scripts/check_contribution_policy.py --base HEAD` 返回通过，并明确不是语义批准或发布许可。

## 保护与证据

- 本轮开始时前一批已有 23 个修改/新增文件，前后逐文件 SHA256 一致。
- `completion-verification` 的工作流状态、阶段台账和 tasks SHA256 与此前一致。
- 原始 JUnit：`output/contribution-policy-pytest.xml`；本地核对快照：`output/contribution-policy-evidence.json`。output 按原忽略规则不加入版本控制。
- 2026-09-06 `gh api` 只读返回：origin 为公开的 mixyoung/super-dev，owner=mixyoung，当前账号 admin=true；main.protected=false，规则集为空。本轮没有执行设置写入。

## 仍需另行处理

仓库文件尚未提交推送，因此外部贡献者尚看不到本轮规则，GitHub CI 也尚未运行新 job。CODEOWNERS 进入目标分支后才影响后续 PR；真正拒绝绕过需启用远端 PR/状态检查/审查保护，并确定单维护者的审批或例外安排。

脚本不验证文字是否真实、更先进或已获授权，不能防止持有管理员权限者修改检查器/绕过保护；语义审查、外部仓库权限和明确维护者决定仍必要。未执行全仓发布验证、Linux/macOS 运行或跨模型行为评测，也没有新增这些方面的通过声明。
