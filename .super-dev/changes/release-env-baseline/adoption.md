# 发布检查环境补齐

## 问题与现有覆盖

原发布预检缺少 types-requests、bandit、twine；build 的模块检测命中了仓库同名目录，实际没有发行包。需要补齐工具，不能把环境诊断都当业务缺陷。

## 来源与适用条件

用户确认的 output/release-remediation-plan.md 及其三文档。基线 e66444b，Python 3.13.12 / Mypy 1.20.1；只影响开发/发布环境。原类型报告 output/release-readiness-2026-09-06.json 保留不覆盖。

## 取舍与核心影响

安装 types-requests 2.33.0.20260906、bandit 1.9.4、build 1.6.0、twine 7.0.0；锁文件为目标 Python 范围解析必要传递依赖。核对原锁定 72 个包名的版本全部不变，运行依赖声明不变；不利用升级检查器减少诊断，不使用忽略配置。

## 改动范围

- pyproject.toml
- uv.lock
- .super-dev/changes/release-env-baseline/proposal.md
- .super-dev/changes/release-env-baseline/tasks.md
- .super-dev/changes/release-env-baseline/adoption.md

## 验证与未验证

先 dry-run 确认只新增工具，再在项目 .venv 安装并核对各工具 --version；Mypy 仍为 1.20.1。原 check_type_gates 返回 63 项/9 文件，Webhook 两项消失，其他诊断仍在。新报告 output/release-after-env-type-gate.json。还未运行安全扫描或完整发布检查；后续按计划执行，PR 通过不代表发布就绪。

## 决定与回退

按已确认 A 批实施；回退本批 dev 声明和锁文件即可，不动产品代码/状态。以正常 PR 及原五项必过检查合并，无管理员绕过。
