# Windows 贡献检查输出修复

## 问题与现有覆盖

已存在 UTF-8 文件读取与 Git 输出解码，但最终 CLI 提示使用 Windows cp1252 标准流。原检查通过却因中文输出崩溃，需要修复显示而不是修改判定。

## 来源与适用条件

原始 CI run 34022420693 / job 101457300734，基线 main@179b17a。Python TextIOWrapper.reconfigure 官方说明：https://docs.python.org/3/library/io.html#io.TextIOWrapper.reconfigure 。适用于此脚本 CLI，包括重定向管道；不修改用户全局编码或产品宿主。

## 取舍与核心影响

用户已明确要求修复。只在 CLI 入口调整本进程标准流编码，导入模块不改标准流；中文正常输出，罕见不可编码字符用可见转义保留信息。原必过项、检查规则、返回码、主线保护与流程状态不变。

## 改动范围

- scripts/check_contribution_policy.py
- tests/unit/test_contribution_policy.py
- .super-dev/changes/contribution-output-encoding/proposal.md
- .super-dev/changes/contribution-output-encoding/tasks.md
- .super-dev/changes/contribution-output-encoding/adoption.md
- .super-dev/changes/contribution-output-encoding/validation.md

## 验证与未验证

强制 cp1252、ASCII 和 UTF-8 的真实子进程检查通过、规则失败及参数错误，验证返回码及中文诊断。实际结果见 validation.md；真实 GitHub Windows/Ubuntu CI 待 PR 执行后确认，不能用本地模拟代替。

## 决定与回退

按已授权缺陷修复实施，不吸收新方法或改验收标准。回退只撤回本批输出配置与回归差异；旧 cp1252 问题会恢复，不通过移除必过项作为回退。
