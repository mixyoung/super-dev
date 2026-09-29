# 治理整改专用 change：governance-remediation-2026-09

## 背景

2026-09-29 对全项目做了一次只读需求与架构审查，核实 7 项问题（Web 接口读写边界、状态提交修订协议、确认记录统一提交、发布就绪"通过"语义、自动评分语义、新旧编排门禁一致性、安装指引文档偏差）。维护者确认按批次整改，本 change 承载全部整改批次的记录与授权状态。

## 范围与批次（顺序 A → C → B → D1/D2 → E）

- **批 A（已执行）**：安装指引统一为 GitHub-only 固定 Tag 口径 + 修复机器本地绝对路径链接。范围：docs、install.sh、super-dev-website 源文本；不含官网部署。
- **批 A2（已执行）**：官网身份切换至 GitHub Pages——SITE_URL、仓库链接、star API 全部从原维护者（shangyankeji / superdev.goder.ai）切至 mixyoung/super-dev；删除 CNAME 启用内置 `/super-dev` basePath（即 https://mixyoung.github.io/super-dev/）；Footer 的 PyPI 链接改 GitHub Releases；新增仅手动触发（workflow_dispatch）的 Pages 部署 workflow。实际部署待维护者启用 Pages 后手动执行。
- **批 C（已批准并执行，核心：权限）**：Web 接口权限边界收紧——repair/persist/verify 类写操作改鉴权 POST、project_dir 限定获准工作区、GET 评估只读零落盘。授权：维护者 2026-09-29 会话（"合并 批准继续"，按 A → C → B 既定顺序）。
- **批 B（待批准，核心：状态/确认合同）**：expected_revision 必填与运行路径保留 revision、权威状态损坏显式报阻与恢复候选、确认记录统一经 StateStore 提交、各入口确认门禁对最终阶段列表统一真阻断；先写"未确认不得推进"运行时回归测试锁定已定位的 Web 空 phases 绕过（api.py:1094 else 分支 + engine.py:565 默认分支）。治理降级（governance_gap）只记录降级，不替代确认门。
- **批 D1（有界缺陷）**：架构漂移否定句误报算法修复（SQLite 案例）。
- **批 D2（待批准，核心：证据语义）**：发布就绪三维度呈现、unknown 不折算 PASS、无宿主验收不判 PASS、spec_compliance 解析不到需求不给 100 分。
- **批 E（待排期）**：跨入口、跨宿主覆盖测试与实际验收收尾。

## 授权状态（如实记录）

- 批 A：维护者 2026-09-29 会话明确授权实施，范围限安装指引与链接、不含官网部署。
- 批 A2：维护者 2026-09-29 会话授权——原维护者官网无法修改，官网链接与内容切换到 GitHub Pages（mixyoung 仓库），未来托管在 GitHub Pages。
- 批 C：维护者 2026-09-29 会话按既定顺序（A → C → B）授权执行；批 B、批 D2 仍待分别单独批准。
- 批 C、批 B、批 D2：涉及权限、权威状态/确认合同与验收语义，属产品核心层，须维护者分别单独批准；本文件不构成对它们的授权。
- 批 D1：按维护者 2026-09-29 意见作为有界缺陷修复处理。

## 基线纪律

- 批 A 基线提交：`75ece3262880334ae0e06ffc113dd633f2755767`。贡献政策检查固定使用该提交作为 `--base`，不使用批内提交后的 HEAD。后续每批开始时另行固定各自基线提交。
- 本 change 不复用已部署的 `super-dev-2-6-reliability`；历史报告保留原有语义，不重新打分追认过去的验收。

## 本批发现但未处理（待维护者决定）

- `docs/RELEASE_RUNBOOK.md` 中 `--repository pypi` 等发布链路描述与 GitHub-only 现状的残留不一致（批 A 只修了安装验证命令一行）。
- 官网模拟终端输出中的 `Successfully installed super-dev-2.4.0` 版本号陈旧（外观问题）。
- （原列出的官网指向 `shangyankeji/super-dev` 的身份问题已由批 A2 解决，2026-09-29。）
