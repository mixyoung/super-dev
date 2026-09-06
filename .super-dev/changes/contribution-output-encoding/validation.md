# 输出编码修复：提交前验证

2026-09-06。基线 `179b17a9c3e0756ac054c44df204e0d3a353237e`；修复分支 `ocx/fix-contribution-output-encoding`。仅修复贡献检查 CLI 输出，不改 CI 必过项或判定。

## 原因与修复

原 GitHub Windows job `101457300734` 已完成规则检查，在打印中文“通过”时触发 cp1252 UnicodeEncodeError。脚本文件读取和 Git 解码已使用 UTF-8，缺口是标准输出流。

修复在 `main()` 开始处将实际 TextIOWrapper 标准输出/错误设为 UTF-8，错误处理用可见转义而非忽略内容。仅 CLI 执行时生效；导入函数不改变宿主流，StringIO 等替代流不强制重配。依据 Python 标准库 `TextIOWrapper.reconfigure`（Python 3.7 起支持）；本项目 Python 3.10+。

## 本地测试

Windows，项目 `.venv` Python 3.13.12。

- 先新增真实子进程回归，强制 `PYTHONIOENCODING=cp1252:strict/ascii:strict/utf-8:strict`，并用单独进程确认启动编码；不是模拟 print 函数。
- 原实现：6 failed、4 passed、21 deselected。cp1252/ASCII 的通过/失败输出崩溃，参数错误中文转义；UTF-8 与导入无副作用对照正常。
- 修复后：`python -m pytest tests/unit/test_contribution_policy.py -q -p no:cacheprovider --junitxml=output/contribution-output-encoding-pytest.xml`，31 passed，0 failed/errors/skipped；终端 10.63 秒。
- 成功返回 0；缺记录返回 1 且显示中文文件名；非法参数返回 2 且显示中文参数。导入保持原 cp1252 流。
- Ruff、Black、检查脚本 Mypy、贡献范围检查和 Skill 同步检查通过。

## 远端验证与边界

本记录是提交前检查快照；真实 Windows/Ubuntu CI 和合并状态以该修复 PR 的 checks/合并记录为准。原始失败来源：[Windows CI](https://github.com/mixyoung/super-dev/actions/runs/34022420693/job/101457300734)。PR 必须通过全部五项已配置检查，不移除 Windows 项、不使用管理员绕过。

没有改系统/用户编码配置、产品 Skill、阶段状态、原行为基准、质量阈值或既有 CI。没有扩展到其他 CLI 的兼容改造；不将此局部结果声称为所有平台/所有输出场景的证明。
