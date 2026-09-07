# 本 fork 的更新规则

`super-dev update --check`、启动更新提示与 `super-dev update` 均查询
`mixyoung/super-dev` 的 GitHub 最新正式 Release，不再查询原版 PyPI。
不接受草稿、预发布、来源不一致、缺校验文件或不兼容当前 Python 的制品。
SHA256 用于完整性校验，不是独立的发布者签名。

## 使用与边界

```text
super-dev update --check
super-dev update
super-dev update --include-user
```

默认更新当前已确认归属的隔离 pip/uv 安装，并只刷新当前项目中已存在、与旧模板一致的文本。
`--include-user` 是本次明确允许刷新既有用户级文本，不是安装新宿主的授权。
自定义内容、重复/损坏的托管区块、连接点、符号链接和安装期间改动的文件不会被覆盖。
共享规则文件只替换匹配的托管区块，外部内容保留；变化的原托管内容保存到
当前项目 `.super-dev/update-backups/`，供人工比较和恢复。

安装后启动目标安装的绝对解释器（隔离模式），确认版本并逐项校验 wheel 包文件和静态资源，
然后才由新版本刷新文本。不会继续调用旧进程的 Skill 模板，也不调用会扩大全局范围的旧 `migrate`。
不改 `super-dev.yaml`、主工作流状态、Git 或用户 JSON 设置，不补装缺失宿主，不清理旧别名。
JSON 设置、Hook 和可选插件的结构迁移不属于这次自动文本刷新，须单独处理。

源码/editable、系统 Python/用户 site-packages、来源不明或含自定义依赖组合的 uv tool 安装，
给出手工更新说明并停止，不猜测环境归属，不切换安装方式。`--method` 只能确认已有方式。
当前开发版高于正式发布时不降级。同版可核验并刷新已有文本，但不重装依赖。

## 失败与恢复

- 未通过来源、哈希或 Python 校验：不启动安装。
- 安装器失败/超时：不刷新宿主，不能假定旧环境完整；先用原解释器检查版本，再按原安装方式恢复已校验 wheel。
- 安装结束但新进程/文本刷新失败：非零退出，显示未完成项，不宣称完整升级成功。
- Windows 文件占用：不强杀宿主、不提权；关闭相关会话后在新终端重试。
- 完成前验证摘要的 `--verbose`/`--json` 仍是执行命令，再次调用会重新验证，不是复用历史结果。

旧 2.5.0 不包含这条新更新链，第一次过渡仍须由维护者提供新版本 wheel/源码安装；
仅在仓库实现新更新器不会让已经安装的旧代码自动改来源。本轮实现不等于已发布新版。

实现依据（2026-09-07 核对）：[GitHub Releases API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)、
[uv 工具升级](https://docs.astral.sh/uv/guides/tools/#upgrading-tools)。uv 原有升级尊重旧安装约束，因此本 fork 用固定且已校验的目标 wheel 替换正式版本来源。
