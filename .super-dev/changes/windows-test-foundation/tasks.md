# Windows 测试基础与用户目录隔离任务表

## A. 已确认基础

- [x] A1. 记录当前分支、提交、操作系统、Python、pytest 和关键依赖版本。
- [x] A2. 区分历史 10 项定向失败、55 项较宽检查失败和其中 35 项用户目录失败。
- [x] A3. 完成调研、需求、技术方案和操作体验文档。
- [x] A4. 获得用户文档确认和 Grok Build `VERDICT=ACCEPT`。
- [x] A5. 从当前干净提交创建独立分支 `feature/windows-test-foundation`，不合并、不推送。

## B. 用户目录来源

- [x] B1. 增加纯目录说明对象，覆盖用户主目录、Codex 目录和 XDG 配置目录，不加入测试状态业务分支。
- [x] B2. 让 `SkillManager` 接受可选目录来源并替换内部 `Path.home()` / `expanduser()` 目标解析。
- [x] B3. 让 `IntegrationManager` 使用同一目录来源解析协议、命令、技能、智能体和可选用户文件。
- [x] B4. 保持两个管理器现有构造方式和默认用户行为兼容。
- [x] B5. 增加 Windows、Linux、主目录外 `CODEX_HOME` 和兼容路径解析单元测试。

## C. 公共测试隔离

- [x] C1. 在 `tests/conftest.py` 增加唯一临时用户目录条件。
- [x] C2. 一致设置 `HOME`、`USERPROFILE`、`HOMEDRIVE`、`HOMEPATH`、`CODEX_HOME` 和 XDG 目录。
- [x] C3. 断言 `Path.home()`、`expanduser()`、两个管理器和测试断言使用同一目录。
- [x] C4. 迁移 `test_skill_manager.py`，删除测试内部第二套 `fake_home`。
- [x] C5. 迁移 `test_integration_manager.py`，删除测试内部第二套 `fake_home`。
- [x] C6. 审计确认当前没有测试需要关闭自动隔离；本阶段不开放绕过标记，未来如需真实目录只读测试必须单独立项。

## D. 真实用户目录保护

- [x] D1. 从 `SkillManager` 的正式、兼容和镜像路径表生成技能保护范围。
- [x] D2. 从 `collect_managed_surface_paths(include_user_surfaces=True)` 的全部非项目路径生成宿主保护范围。
- [x] D3. 合并 `surface_path_groups()` / `readiness_surface_sets()` 的 `official_user`、`optional_user`、`compatibility`。
- [x] D4. 覆盖用户级协议、命令、技能、智能体、可选文件和主目录外自定义 `CODEX_HOME`。
- [x] D5. 实现 Windows `resolve`、路径规范化、大小写折叠和 `commonpath` 安全比较。
- [x] D6. 实现运行前后摘要、脱敏展示和完整内部比较键；不得记录凭据正文。
- [x] D7. 增加新增、删除、内容变化、大小写别名、不同盘符、符号链接和目录连接测试；无符号链接权限时保留明确跳过。

## E. 安全基线入口与登记

- [x] E1. 新增 `tests/support/run_safe_baseline.py`，只接受固定检查范围，不接受任意命令字符串。
- [x] E2. 固定隔离自检、用户目录检查、Windows 定向检查、完整单元检查和重复性检查。
- [x] E3. 显式传递完整隔离环境给 pytest 和子进程，并处理超时后的进程树。
- [x] E4. 输出环境、JUnit、测试日志、真实目录前后摘要和中文总结。
- [x] E5. 分开记录 `safety_result`、`test_result` 和 `evidence_result`。
- [x] E6. 新增失败登记表，支持 `scopes`、`windows_focused` 和 `baseline_kind`。
- [x] E7. 导入历史 55 项失败，标记 `35 ⊆ 55`，保留 10 项定向历史口径且禁止相加。

## F. Windows 持续检查

- [x] F1. 在 `.github/workflows/ci.yml` 增加独立 Windows 基线任务。
- [ ] F2. 使用 Python 3.10、3.11、3.12 矩阵运行安全基线。
- [x] F3. 始终上传报告和 JUnit 证据。
- [x] F4. 隔离失败、真实目录变化或证据缺失时失败；普通测试失败明确显示但不冒充隔离失败。
- [x] F5. 保持现有 Ubuntu 质量任务行为不变。

## G. 安全验证顺序

- [x] G1. 先运行目录解析和隔离自检，不运行高风险完整测试。
- [x] G2. 隔离自检通过后，运行两个高风险测试文件并确认真实用户目录零变化。
- [x] G3. 运行 Windows 定向检查并生成隔离后当前结果。
- [x] G4. 运行完整单元检查两次，比较收集数、失败集合、跳过集合和真实目录摘要。
- [x] G5. 对新失败完成产品问题、测试问题、环境差异或尚未确定分类。
- [x] G6. 运行 Ruff、字节码编译、相关类型检查和差异检查。
- [x] G7. 进行独立 Grok Build 只读审查，修复目录连接和分阶段停跑强制问题，最终 `VERDICT=ACCEPT`。

## H. 禁止事项

- [x] H1. 验证未修改真实用户级 Skill、宿主协议、命令或智能体文件。
- [x] H2. 验证未实现扩展平台、知识导入、新开发方法或九阶段真实控制。
- [x] H3. 验证未合并、未推送、未修改用户级 Skill。
