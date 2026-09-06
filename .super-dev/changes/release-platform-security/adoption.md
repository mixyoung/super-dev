# 发布阻碍补修记录

## 问题与现有覆盖

基线 5b0026a 的类型门禁已通过，但 Windows 原用例 test_special_chars_in_name 在保存 UI 契约时失败。七个已安装依赖存在 39 条审计记录（去重 27 个公告），不等于 39 个产品代码漏洞。CI 原 Security Scan 的 pip audit 命令错误且忽略失败，类型门禁未接入。

## 来源与适用条件

2026-09-06 用户在两个新增阻碍被单独说明后回复“继续”；沿用已确认的 release-remediation 计划 D 批。文件名修法依据本地失败与全部直接 UI 契约读写点，不新增外部方法。最低修复版本来自 pip-audit 原始报告，并核对 PyPI 版本元数据：

- https://pypi.org/pypi/click/8.3.3/json
- https://pypi.org/pypi/idna/3.15/json
- https://pypi.org/pypi/msgpack/1.2.1/json
- https://pypi.org/pypi/pillow/12.3.0/json
- https://pypi.org/pypi/pip/26.2/json
- https://pypi.org/pypi/starlette/1.3.1/json
- https://pypi.org/pypi/urllib3/2.7.0/json

上述版本支持 Python 3.10+；FastAPI 0.136.0 接受 starlette>=0.46.0，无需升级父包。msgpack、Pillow、pip 属于开发依赖面；click、idna、Starlette、urllib3 已是运行时传递依赖。

## 取舍与核心影响

UI 契约文件名仅在显示名称含跨平台非法字符时转换，统一直接读写点；使用可读片段和 SHA-256 摘要区分替换后相似名称。不更改显示名称、普通路径大小写/中文/下划线，也不更改公共 sanitize_artifact_name、change 选择或其他产物命名。这不是整个项目名验证器或历史文件迁移。七个安全下限写进现有运行/开发依赖声明，避免只有 uv 锁文件有效而 pip 安装回退；uv lock 仅定向更新这七包，Mypy 保持 1.20.1。无核心/评分变化。

## 改动范围

- super_dev/artifact_utils.py
- super_dev/cli.py
- super_dev/cli_deploy_runtime_mixin.py
- super_dev/cli_release_quality_mixin.py
- super_dev/creators/creator.py
- super_dev/creators/frontend_builder.py
- super_dev/creators/implementation_builder.py
- super_dev/creators/task_executor.py
- super_dev/deployers/delivery.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/ui_review.py
- super_dev/extensions/executor.py
- tests/extensions/test_executor.py
- tests/unit/test_release_ui_contract_paths.py
- pyproject.toml
- uv.lock
- .github/workflows/ci.yml
- .super-dev/changes/release-platform-security/proposal.md
- .super-dev/changes/release-platform-security/tasks.md
- .super-dev/changes/release-platform-security/adoption.md

## 验证与未验证

Windows Python 3.13.12：修改前新增场景加原失败为 8 failed / 5 passed；修改后新增 12 项通过，原失败在前端套件复跑中通过。新增断言按既有 JSON 序列化转换 tuple 为 list、既有 playbook.focus 读取合同修正，未更改产品数据或旧断言。原类型门禁、Ruff 全范围、pip check、Bandit 通过；同一项目环境 pip-audit 重新扫描退出 0、无已知漏洞。锁文件对照只有七个版本变化，无其他包新增/删除或父包升级。

原始证据：output/release-ui-paths-before.xml、release-ui-paths-after.xml、release-dependency-audit.json、release-dependency-audit-after.json、release-bandit-after.json。完整测试、远端 Python 3.10/3.11/3.12 CI 及其余发布验证执行后补记；未验证内容不得当通过。

关联四套回归 103 passed（output/release-platform-security-focused.xml）。知识审计/门禁、贡献检查及 Skill 同步通过。uv build 的 wheel/sdist 与 Twine check 通过；在新的非 editable 环境从 wheel 安装，离开仓库并使用 Python -I 验证 CLI 2.4.0、修复函数、内置扩展资源。依赖从声明重新解析，未修改项目开发环境的其他包。交付 smoke 只证明模拟确认的临时项目打包链路，不作为本项目质量或用户确认。

发布验证未通过项：完整 Windows pytest 仍在运行且已有失败；完整 Mypy 按原 preflight 定位为 advisory，仍有非核心诊断；当前宿主画像 claude-code 的真实兼容性 75<80，不改宿主配置；并行运行时基准 Engine Init 682.27ms>100ms，待空闲复核，脚本本身退出 0 不能覆盖其失败结果。以上均未顺带修复，也未宣称可发布。detect --json 未启用自动安装，但其现有诊断链会刷新 SESSION_BRIEF/workflow-state 派生摘要；active_change_id 仍为 completion-verification，确认台账和该 change 的任务哈希保持不变，未重新授权。

## 决定与回退

按用户明确批准的两个阻碍和原 D 批执行，不据此扩大到其他缺陷。仅通过正常 PR 和原五项必过检查合并；安全扫描也须真实通过。回退仅撤本批差异；依赖回退会重新带回已知公告，必须如实阻止发布。未改版本、标签或上传 PyPI。

追加批准：PR #5 新接入的 Linux 类型门禁暴露 executor.py 中 WinDLL/get_last_error 的四处诊断后，用户明确回复“允许，仅修这 4 处平台声明”。因此只在 Windows Job 的构造与 assign 入口补可识别的 sys.platform 防护，Windows 分支内的 API、标志、调用顺序和进程清理逻辑不变；正常 POSIX 执行仍走原进程组分支。其他性能、宿主和全量失败不在追加批准内。

同时声明原有 _kernel32: ctypes.CDLL 与 handle: int | None 字段，避免 Linux 分析时由于构造函数不可达而丢失字段类型，未引入 Any/ignore。Linux 目标检查从 4 项到 0 项，Windows 目标同样通过；执行器回归 7 passed / 1 skipped（仅既有 POSIX 专属场景在 Windows 跳过），覆盖真实超时/取消后进程树清理；Ruff 全范围与贡献检查通过。

为避免一次全量报告混用修改前后代码，第一次 Windows 全范围 pytest 在约 13% 已有失败时中止，没有宣称完成或通过；其不完整输出不能当最终验证。平台补丁后重跑类型/执行器和 CI，以新提交绑定的结果为准。
