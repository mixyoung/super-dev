# Validation: Super Dev 2.6 可靠性收敛

## 已通过

- 2.6 核心状态、迁移、证据、发布与质量定向回归：`163 passed, 1 skipped`。
- 其余 unit/extensions/e2e/integration 分区回归：`2986 passed, 6 skipped`。
- Web API 集成回归：`107 passed`。
- CLI 集成功能用例：`227 passed`。
- Ruff 全仓、Black 本轮 Python 文件、22 项类型门、5 个核心模块定向 Mypy、compileall、`git diff --check`通过。
- Skill 同步检查与贡献范围检查通过。
- `scripts/release.sh` Bash 语法检查通过。
- 2.6.0 wheel/sdist 构建成功并通过 Twine；wheel 内含 `state_store.py`、`evidence_contract.py`、`release_observation.py`。
- Fresh Verification 稳定性修复后，正式计划完整运行 `392 collected, 390 executed, 2 skipped, 0 failed`，用时约 14 分钟，候选前后一致，进程树清理已确认。
- 修复实现后执行器回归 `10 passed, 1 skipped`，Fresh Verification 服务/CLI 回归 `44 passed`，完整扩展回归 `165 passed, 2 skipped`。

## 制品

- wheel: `output/release/2.6.0-stable/super_dev-2.6.0-py3-none-any.whl`
- wheel SHA256: `A3D5DA902733FF4258A5270F03CA55B46F7C322156100609CBF404439D71B3A2`
- sdist: `output/release/2.6.0-stable/super_dev-2.6.0.tar.gz`
- sdist SHA256: `F0B432FB254A0F1AE05BAF414B7B3BCBB4B4ACA93D49D9920720FF8FA3113877`

## 当前阻断与未完成

- 早期 Quality Gate 阻断由 Fresh Verification 超时引起；本轮已在不缩小测试范围、不降低阈值的前提下修复执行稳定性。当前源码与记录冻结后需再做一次最终候选复验。
- CLI 全量用例本身 227/227 通过，但 pytest 会话结束时发现 `C:\Users\admin\.gemini\settings.json` 被外部 Orca 钩子流程重写，因此用户目录隔离门禁正确地返回失败。Super Dev 未覆盖或回退该用户文件。
- 独立子代理/外部复审未授权，本轮不声称已完成独立复审。

## 交付边界

本轮未提交、未推送、未合并、未发布、未部署。
