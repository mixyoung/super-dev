# 2.5.0 发布记录

## 问题与现有覆盖

用户在 PR #6 合并后明确要求发布新版；此前确认版本计划为 2.5.0、GitHub-only。基线 main@7bc5079。代码整改已经完成，本批只准备版本、生成物、安装入口和可验证发布，不增加功能。

## 来源与适用条件

依据 docs/RELEASE_RUNBOOK.md、scripts/preflight.sh 和已确认的 output/release-remediation-plan.md。包发布检查与旧 completion-verification 的应用交付验收不是同一对象；范围解释见 output/release-2-5-0-scope.md，不复用/改写旧任务分数、确认或证据。
来源为当前已合并代码、方法吸纳记录与 PR #1–#6；不开展新的外部知识吸纳。skill-creator 用于保持版本更新和既有指令边界，未创建新 Skill。

## 取舍与核心影响

版本源、CLI/配置默认值和文档版本标记同步到 2.5.0；依赖锁只变 super-dev 自身版本，无第三方升级。包链接与安装命令指向本 fork，保留原作者身份/许可证。
Skill 行为模板只改版本常量；四份标准副本和两份落后的 SEEAI 副本由同一模板生成。SEEAI 的较大差异是补齐已有源模板而非本批新增规则，同步检查纳入现存两份 SEEAI 路径，不新建宿主接入面或全局安装。
维护手册增加 GitHub-only 与 Windows 等价验证说明，保留原检查种类、阈值和八项保护，不使用跳过参数冒充通过。可选插件旧包未作为独立发行制品，其已知历史清单格式限制在 release notes 披露；不扩大为本轮插件改造。

## 改动范围

- .agents/skills/super-dev-seeai/SKILL.md
- .agents/skills/super-dev/SKILL.md
- .claude/skills/super-dev/SKILL.md
- CHANGELOG.md
- README.md
- README_EN.md
- docs/HOST_USAGE_GUIDE.md
- docs/INSTALL_OPTIONS.md
- docs/QUICKSTART.md
- docs/RELEASE_RUNBOOK.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- pyproject.toml
- scripts/sync_super_dev_skills.py
- super_dev/__init__.py
- super_dev/branding.py
- super_dev/cli_governance_mixin.py
- super_dev/cli_parser_mixin.py
- super_dev/config/manager.py
- super_dev/creators/document_generator.py
- super_dev/deployers/delivery.py
- super_dev/skills/skill_template.py
- tests/unit/test_new_modules.py
- uv.lock
- .super-dev/changes/release-2-5-0/proposal.md
- .super-dev/changes/release-2-5-0/tasks.md
- docs/releases/2.5.0.md
- tests/unit/test_release_version.py
- .super-dev/changes/release-2-5-0/adoption.md

## 验证与未验证

版本/Skill/模块回归 66 passed；另一组 125 项旧状态/范围/恢复用例通过。新版本测试按 argparse 原行为捕获 SystemExit(0)，并核对真实版本输出；未修改 CLI 退出语义。两份 Codex Skill 前置格式检查通过，全部六份模板同步通过。Ruff 与发布类型门禁通过。uv.lock 对照仅 super-dev 2.4.0 -> 2.5.0。
正式放行还必须核对干净发布提交的完整 CI 矩阵、知识/安全/性能/宿主/交付 smoke、最终制品和隔离安装。本条不把待执行写成已通过；最终证据随 Release 附件与 PR 核对。旧任务验收、不在 CI 覆盖范围的宿主/Windows 端到端与冷启动限制明确单列。

安装制品检查发现既有打包配置只包含扩展 YAML，遗漏规则 YAML、设计 CSV、文档模板和 Web 静态入口。发布授权中的“所需资源验证”因此未通过，尚未公开 Release。仅补 pyproject 的包资源清单，不改资源内容或运行逻辑；必须重建并在全新非 editable 环境确认规则非空及资源存在。

完整枚举 super_dev 内已有非 Python 运行资源后，同样纳入专家角色与 playbook Markdown。新增声明覆盖回归用例，且最终仍以真实 wheel/sdist/隔离安装内容逐文件对照为准，不能只凭声明测试通过。未将根目录项目 knowledge 当成隐藏安装副作用复制到用户项目，它随完整 Git 标签源码提供。

## 决定与回退

按用户明确发布授权执行，维护者确认无需重复索取。只向 mixyoung/super-dev 正常 PR/标签/Release 写入；不部署服务、不操作 PyPI、不改其他 change。标签已存在时停止核对，不覆盖。只有实际门禁通过且制品身份/哈希确认后才公开 Release。出现新独立阻断问题单列，不扩开发范围。
