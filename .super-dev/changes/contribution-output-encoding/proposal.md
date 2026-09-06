# 修复贡献检查的 Windows 输出编码

2026-09-06 用户要求修复 Windows 必过贡献检查。原始失败：CI run 34022420693 / job 101457300734 在打印中文通过提示时，由 cp1252 编码触发 UnicodeEncodeError；检查逻辑未失败。

范围仅为 `scripts/check_contribution_policy.py` 的 CLI 输出配置、对应回归和本批记录。使用 Python 标准库在 CLI 入口设置 UTF-8，不改操作系统、用户环境或 CI 必过项，不降低判定，不碰其他 change 的状态与证据。保留导入时无标准流副作用及返回码。

验证：先用强制 cp1252/ASCII 的真实子进程复现，再检查通过=0、规则失败=1、参数错误=2，中文路径可读；回归当前脚本、静态检查和原使用路径。分支 `ocx/fix-contribution-output-encoding`，通过 PR 验证真实 Windows/Ubuntu CI，不绕过主线保护。
