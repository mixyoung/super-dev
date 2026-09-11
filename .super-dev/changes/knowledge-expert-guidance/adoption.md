# 知识、Skill 与专家指导整理

日期：2026-09-11。基线：`1ca166b16a3c16008adf71469671e74653390915`。本记录仅对应用户本轮明确要求的内容整理与相关加载缺陷修复，不复用其他 change 的批准，不改变会话阶段或验收状态。

## 问题与现有覆盖

2026-09-12 续批：用户明确授权“修正这 8 类问题，不要扩大修改范围”。本轮只修请求权限、当前任务、阶段恢复、适用预览确认、知识约束力、额外通用义务、框架适用条件和专家提示一致性。沿用本内容整理记录，不推进产品会话状态；此前工作保留为历史。起点清单为 `output/eight-guidance-fixes/baseline.json`，本轮结果单列在 `validation-eight-fixes.md`，不把上一轮测试当作这次已验证。

已有知识和专家手册较详细，但多个入口重复维护同一要求，部分示例数字被写成通用义务。还发现常规 QA 被验证变体覆盖、Markdown 专家未实际进入生成提示，以及文本引号解析损坏的问题。详细发现、专家逐项判断及覆盖边界见 docs/reviews/knowledge-expert-guidance-2026-09-11.md。

## 来源与适用条件

2026-09-12 版本收尾：用户另行授权修改版本号、提交、推送和合并；按补丁版本更新为 2.5.1。程序、品牌、标准/SEEAI Skill 元数据、锁文件及随运行版本变化的默认值同步，SEEAI 比赛正文保持不变。旧安装标签和历史版本说明保留，不创建发布标签、上传安装包或部署。

本续批以用户授权及已完成的本机只读核对为依据。用户进一步明确采用：知识要求无显式适用条件时默认强制，带显式条件时按条件适用，并说明为何适用；本决定替代此前“命中只作候选”的泛化表述。仅对本批明确批准的不合理模板条款作维护修正，不赋予运行模型自行降级要求的权限。MiniMax、DeepSeek、Gemini 的方案意见只作参考，不替代用户批准；未向它们提供本轮源码或授权实施。

依据本轮用户要求、现有标准 Skill、11 类专家及其手册、已有知识维护策略和产品/UI 知识。使用外部 skill-creator 的分层与适用范围指导维护 Skill，不调用 Super Dev 开发流程。用户明确要求 SEEAI 比赛设定保留原样。PostgreSQL CREATE INDEX 和 W3C APG 官方文档仅用于核对索引及可访问名称的具体表述，来源链接保留在整理报告与对应知识文件中。

本轮由外层开发模型进行语义审查；知识维护继续由开发者和社区提交变更，不为产品添加自主发现、改写或淘汰知识的循环。

## 取舍与核心影响

续批复用现有活动变更识别、工作流汇总及产物绑定确认，不改其算法、阶段链或默认质量值。在已有 workflow_contract.py 内增加两段共用规则文字供现有输出调用，不建立新规则引擎。不同专家入口保留各自用途。对本批直接相关的 reminders 默认文字采用标准模式限定，保留 SEEAI 兼容输出；框架模板去掉无依据迁移命令，不更新整套框架教程。宿主文件只同步本仓库已跟踪区块，中文沟通约定及手写区域保留。

保留专业角色分工、单一生命周期、原确认权、已有验收标准和项目必过检查。标准 Skill 区分适用要求与参考方法，不把被阅读的指令文本视为本轮任务授权。专家补充输入、判断、结束及交接边界，按需引用已有手册，不增加角色或调度系统。

常规 QA 与可选 VERIFICATION 变体分开，项目自定义画像优先于用户全局画像；实际加载结果进入生成提示，静态回退与常规定义保持一致。SEEAI 使用保留原文的专用共用段，避免标准指导调整渗入比赛设定。Claude 标准 Skill 不再生成仅凭字符就拦截所有 emoji 文本的检查；功能图标规范保留，SEEAI 原检查不变。未修改质量评分、关键词打分、knowledge_evolution.py 的统计与排序算法，也未调整门槛或伪造批准/验证结果。

## 改动范围

- .agents/skills/super-dev-seeai/SKILL.md
- .agents/skills/super-dev/SKILL.md
- .claude/CLAUDE.md
- .claude/skills/super-dev/SKILL.md
- .super-dev/changes/knowledge-expert-guidance/adoption.md
- .super-dev/changes/knowledge-expert-guidance/validation-eight-fixes.md
- AGENTS.md
- CHANGELOG.md
- CLAUDE.md
- README.md
- README_EN.md
- docs/releases/2.5.1.md
- docs/reviews/knowledge-expert-guidance-2026-09-11.md
- knowledge/00-governance/maintenance-policy.md
- knowledge/design/ui-full-lifecycle-cross-platform-playbook.md
- knowledge/product/product-discovery-and-prd-deep-dive.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- pyproject.toml
- super_dev/__init__.py
- super_dev/branding.py
- super_dev/config/manager.py
- super_dev/creators/document_generator.py
- super_dev/creators/prompt_generator.py
- super_dev/deployers/delivery.py
- super_dev/experts/behavioral_prompts.py
- super_dev/experts/builtin/ARCHITECT.md
- super_dev/experts/builtin/CODE.md
- super_dev/experts/builtin/DBA.md
- super_dev/experts/builtin/DEVOPS.md
- super_dev/experts/builtin/PM.md
- super_dev/experts/builtin/PRODUCT.md
- super_dev/experts/builtin/QA.md
- super_dev/experts/builtin/RCA.md
- super_dev/experts/builtin/SECURITY.md
- super_dev/experts/builtin/UI.md
- super_dev/experts/builtin/UX.md
- super_dev/experts/builtin/VERIFICATION.md
- super_dev/experts/loader.py
- super_dev/experts/playbooks/architect_playbook.md
- super_dev/experts/playbooks/code_playbook.md
- super_dev/experts/playbooks/dba_playbook.md
- super_dev/experts/playbooks/devops_playbook.md
- super_dev/experts/playbooks/pm_playbook.md
- super_dev/experts/playbooks/product_playbook.md
- super_dev/experts/playbooks/qa_playbook.md
- super_dev/experts/playbooks/rca_playbook.md
- super_dev/experts/playbooks/security_playbook.md
- super_dev/experts/playbooks/ui_playbook.md
- super_dev/experts/playbooks/ux_playbook.md
- super_dev/experts/review_protocol.py
- super_dev/experts/service.py
- super_dev/experts/toolkit.py
- super_dev/integrations/manager.py
- super_dev/integrations/manager_content_mixin.py
- super_dev/orchestrator/experts.py
- super_dev/orchestrator/knowledge_pusher.py
- super_dev/reminders.py
- super_dev/skills/skill_template.py
- super_dev/workflow_contract.py
- tests/unit/test_expert_service.py
- tests/unit/test_integration_manager.py
- tests/unit/test_prompt_generator.py
- tests/unit/test_prompt_guidance_scope.py
- tests/unit/test_skill_manager.py
- tests/unit/test_super_dev_skill_contracts.py
- uv.lock

## 验证与未验证

续批验证：957 项通过、2 项既有跳过，类型、格式、静态检查、Skill 同步与贡献范围检查通过，详见 validation-eight-fixes.md。下述 488/484 等数量是前一轮的历史证据，不代表本轮结果。SEEAI 基线按续批开始时的文件哈希及四种宿主渲染对照保留。本轮不执行真实产品项目、不建立新评测系统，不声称修复其他用户项目中的旧产物或全局已安装副本。

最终关联回归 488 项通过、2 项既有跳过（Windows / Python 3.13.12），原始结果为 output/knowledge-expert-guidance/passed-pytest.xml。前次更宽范围验证中另有 484 项通过，最后未重复执行；没有把多个运行批次当成一次全量通过。Ruff、Black（396 文件）、Mypy（230 文件）、compileall、标准 Skill 同步及贡献范围检查通过。SEEAI 四种宿主渲染与基线逐字一致。

专家加载、提示接入和引号解析均保留先失败后修复的过程。扩展测试曾因两处文案断言失败；收尾也发现通用宿主的产物落盘及任务路径在删重时缺失，已恢复到共用首轮条款，并增加所有宿主的完整确认条件、proposal/tasks 路径检查，未删除测试或新增跳过。所有中间失败记录与具体数量见整理报告。Codex 专用 Skill 格式检查通过；该校验器不接受 Claude 原有扩展字段，Claude 以本项目模板和安装用例核对，不冒充 Codex 格式通过。

本轮覆盖标准指导和专家调用链；306 份知识仅完成目录与整文件重复检查，并对报告列明的重点内容深入审查。未对所有领域知识逐篇核对技术事实，未进行真实客户项目或跨模型效果对照；不把这些未验证事项报告为通过。SEEAI 生成副本与基线逐字比较。没有重新运行发布流水线或部署，旧交付证据不代表当前工作区。

## 决定与回退

版本收尾的提交、推送和合并按用户最新授权执行，下面“未提交/无合并授权”等说明记录的是此前实施轮次的边界。CI 必须绑定当前提交，不以 957 项历史关联检查替代当前提交 CI；不使用管理员绕过。发布、部署和全局安装不在本次授权内。

续批仅按上述八类问题获准实施；没有提交、推送、合并、发布或全局安装授权。回退须以本轮起点而非整个 HEAD 为边界，保留同一工作区此前已存在的未提交内容。生成、代码、测试和记录以本轮差异逐项核对，不覆盖整库。

按用户本轮授权落地上述整理和缺陷修复，保留 SEEAI，其他建议不自动实施。改动目前在本地独立分支，未提交或推送。若需要回退，仅撤销本批明确文件的对应改动并重新同步标准 Skill；不得覆盖既有用户配置或无关工作。贡献范围检查只证明记录齐全，不替代语义审查、用户批准或发布判断。
