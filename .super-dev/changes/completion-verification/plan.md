# Plan: 完成前验证正式收口
## Context
原始范围是在唯一发布就绪入口建立默认关闭、每次重跑、绑定当前代码版本的 pytest 完成前验证。用户随后明确授权活动变更治理、CLI 根项目范围和中国大陆中文 Harness 三项伴随修复，以保证证据不串线、根 CLI 不被官网误判、用户准确理解结论，不改变原始目标。
## Scope Evolution
- 原始范围：验证合同、执行、证据、发布裁决、10 场景回放和 3 个用户验收候选。
- 伴随治理：活动变更解析、路径安全、严格前缀、确认绑定、质量新鲜度。
- 项目范围：根项目 `platform=cli`、`frontend=none`、`backend=python`，官网和示例独立。
- 沟通范围：根规则、兼容镜像、唯一 Skill 模板及生成副本同步中文合同。
- 排除：系统化排错、第三方方法、九阶段控制改造、产品功能扩展、提交和部署。
## Architecture Impact
- 完成前验证位于 `super_dev/extensions`，由 `release_readiness.py` 裁决。
- `artifact_utils.py`、`workflow_guard.py`、`workflow_state.py`、质量和证据包共享活动前缀。
- `super-dev.yaml` 与项目目录共同决定 CLI 阶段要求。
- `SkillTemplate` 是 Harness 文案单一生成源。
## Implementation Order
1. 完成受限计划、JUnit、退出码、提醒、进程树与证据。
2. 接入唯一发布入口并保持关闭兼容。
3. 建立回放合同、指标和用户验收候选。
4. 落实活动变更前缀、确认与报告新鲜度。
5. 修正根 CLI 范围和无前端判定。
6. 固化中文合同并同步受控副本。
7. 补齐正式规格与追溯，冻结后重跑回放和门禁。
## Rollback
- 关闭扩展或移除允许方法即可恢复旧发布行为，历史证据只读。
- 伴随治理可独立撤销，但不得重新允许跨变更混用或伪造确认。
- 回滚不删除用户数据、不修改用户级文件、Git 或远程系统。
## Verification Order
1. Spec 结构、质量与追溯测试。
2. 验证、指标、回放和发布就绪定向测试。
3. 活动变更、CLI 阶段与中文合同测试。
4. 当前代码版本配置的 pytest 计划。
5. 范围内 Ruff、Black、Mypy、`py_compile` 与 `git diff --check`。
6. 文档冻结后真实回放并生成完成报告。
7. 合规、质量、发布就绪与证据包；失败保持真实状态。
