# 发布整改 A：补齐检查环境

2026-09-06 用户确认 release-remediation 四批计划，并强调只解决当前发布阻碍。基线 main@e66444b。

本批只向两处既有 dev 声明加入 types-requests、bandit、build、twine，并更新 uv.lock；不升级既有运行依赖、不改 Mypy 配置或版本、不改业务代码。后续 B/C 处理剩余代码诊断，D 执行发布验证。
