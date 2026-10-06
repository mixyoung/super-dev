# 质量扫描效率与完整性整改

## 授权与确认

用户先授权按最小建议实施，随后通过本会话计划确认了 `output/quality-scan-efficiency-2026-10-06-{prd,architecture,uiux}.md` 及研究记录中的知识适用边界。当前进入实现；本轮无 UI，预览不适用。

## Description

部分质量扫描器先展开排除子树再过滤，同次消费者重复枚举，错误又可能静默消失。实现调用内来源清单、提前剪枝、必要文档独立读取与受阻传播，保留原质量范围和评分。

## 范围

仅 reviewers/source_inventory.py、spec_compliance.py、architecture_drift.py、uiux_compliance.py、validation_rules.py、quality_gate.py 及对应测试。本轮不改 proof_pack、release_readiness、知识/提示、配置、根工作流状态或其他会话的改动。

## 非目标

无限时、监听服务、持久索引、Git-only 范围、增量放行、依赖图、新 Skill、发布部署均不纳入。

## 维护状态

独立维护工作项，不绑定根状态、不冒用旧发布确认。当前本地 spec propose 会要求并写入全局工作项绑定，因此不执行该写入路径；定向创建本工作项文件后用本地 spec 验证检查结构。
