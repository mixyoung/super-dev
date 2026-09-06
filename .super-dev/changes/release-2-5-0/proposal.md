# 发布 Super Dev 2.5.0

用户在 PR #6 修复合并后明确要求“发布新版”。基线 main@7bc5079。按此前确认的版本计划发布 2.5.0，仅在 mixyoung/super-dev 创建 GitHub Release 和可验证 Python 制品，不向原作者 PyPI/仓库上传，不启用网站或 Kubernetes 部署。

只更新包/CLI/配置/Skill 的发布版本、当前安装说明和 release notes，经过正常 PR 与八项必过 CI 后从 main 打标签。Skill 只同步版本，不改变流程。旧 completion-verification 的用户确认、应用交付报告与当前发布分开保留。
