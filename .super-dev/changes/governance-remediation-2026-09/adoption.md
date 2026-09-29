# 批 A 吸纳记录：安装指引统一为 GitHub-only 口径 + 修复机器本地链接

## 问题与现有覆盖

README.md:31 已明确本 fork 只在 GitHub 发布、未上传 PyPI，且 README/README_EN/INSTALL_OPTIONS/QUICKSTART 均已使用固定 Tag 安装命令；但 docs/WORKFLOW_GUIDE.md:207 与 docs/RELEASE_RUNBOOK.md:102 仍给出 `uv tool install super-dev` / `uv tool install super-dev==<version>`（PyPI 式）命令，install.sh:428-429 的报错提示指向 PyPI 安装，官网 super-dev-website 全部活跃指引组件（Hero、Bottom CTA、Code Demo、Showcase、Docs、终端模拟常量）展示同一失效命令。另有 6 个文档共 12 处链接指向维护者个人机器绝对路径 `/Users/weiyou/Documents/kaifa/super-dev/...`。此前 completion-verification 批只对齐了 README 与 INSTALL_OPTIONS 的发布检查口径，未覆盖上述其余用户入口。

## 来源与适用条件

来源：2026-09-29 维护者会话中的全项目只读审查结论 + 本轮全库 grep 复核（含初次扫描因 head 截断漏掉、复扫补提的 DocsPageContent.tsx:686/689 与 lib/constants.ts:83/105）。适用条件：所有仍在指导当前安装的用户入口（docs、install.sh、官网源文本）。不适用：历史记录（docs/releases/2.4.0.md、官网 Changelog 2.2.0 条目、旧 change 的 adoption 记录按"保留原语义"不改）、行为代码（super_dev/release_readiness.py:831 的兼容分支）、测试中的合成字符串。

## 取舍与核心影响

统一为 README 已确立的 GitHub-only 固定 Tag 命令（`uv tool install --force --from "git+https://github.com/mixyoung/super-dev.git@v2.6.0" super-dev`），消除"未上 PyPI"与失效安装命令的公开矛盾；绝对路径链接改为仓库相对链接。JSX 属性中的命令改用单引号包裹以容纳内嵌双引号。不改变任何产品行为、质量门槛或验收语义；不包含官网构建与部署。发现但不在本批处理（超出授权范围，已在 proposal.md 列出待维护者决定）：RELEASE_RUNBOOK 的 `--repository pypi` 发布链路残留、官网指向 `shangyankeji/super-dev` 的仓库身份问题、官网模拟终端中的 2.4.0 版本号陈旧。批准依据：维护者 2026-09-29 会话明确授权批 A 范围（安装指引与链接，不含官网部署）。

## 改动范围

- docs/WORKFLOW_GUIDE.md
- docs/WORKFLOW_GUIDE_EN.md
- docs/QUICKSTART.md
- docs/INSTALL_OPTIONS.md
- docs/INTEGRATION_GUIDE.md
- docs/RELEASE_RUNBOOK.md
- install.sh
- super-dev-website/components/sections/HeroSection.tsx
- super-dev-website/components/sections/BottomCta.tsx
- super-dev-website/components/sections/CodeDemoSection.tsx
- super-dev-website/components/pages/ShowcasePageContent.tsx
- super-dev-website/components/pages/DocsPageContent.tsx
- super-dev-website/lib/constants.ts

## 验证与未验证

- 复扫（grep 全库 md/sh/ts/tsx）：裸 `uv tool install super-dev` 在活跃指引中清零；剩余 3 处均为有意保留的历史记录（docs/releases/2.4.0.md 两处、completion-verification 旧 adoption 一处）。`weiyou` 在 docs/ 与 README/README_EN 中清零（super_dev/experts/playbooks/code_playbook.md 中的 `TODO(weiyou)` 是示例人名非路径，不属链接问题）。
- 相关单测：`.venv/Scripts/python.exe -m pytest tests/unit/test_release_readiness.py tests/unit/test_product_audit.py tests/unit/test_fork_update.py -q` → 80 passed（198.65s）。发布检查的 `documented_uv_install` 兼容固定 Tag 形式，README/INSTALL_OPTIONS 未受本批影响。
- 贡献政策检查：`python scripts/check_contribution_policy.py --base 75ece3262880334ae0e06ffc113dd633f2755767` 通过（本批无受控路径改动，本记录为按政策自愿保留的短记录）。
- 未验证：super-dev-website 无 node_modules，未运行 tsc/build（改动均为字符串字面量替换，JSX 属性引号已人工核对）；官网未部署（超出本批范围）。install.sh 为 bash 脚本，本机未执行冒烟。

## 决定与回退

采用。授权：维护者 2026-09-29 会话（批 A 范围）。回退：`git revert` 本批提交即可；无数据迁移、无工作流状态变更、无产品行为影响。
