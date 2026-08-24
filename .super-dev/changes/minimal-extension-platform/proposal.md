# 最小扩展平台变更说明

## Description

建立默认关闭、来源可锁定、权限可裁决、命令可安全执行、结果可绑定当前候选的最小扩展内核；阶段 1 只运行仓库内置合同探针，不接入真实外部方法。

## 背景

阶段 0 已经建立可重复的 Windows 测试基线和用户目录隔离。Super Dev 现有 Hook、Skill 安装和证据模块可以提供部分基础，但还不能安全、统一地接入外部工程方法：命令 Hook 仍使用 `shell=True` 字符串，Skill 来源没有提交和内容摘要锁，扩展也没有能力、所有权、写入范围和候选证据合同。

## 目标

建立默认关闭的最小扩展内核，包含：

- 严格扩展清单；
- 来源锁与内容摘要；
- 最小能力词表和所有权拒绝；
- Windows/Linux/macOS 安全执行器；
- 路径写入守卫；
- 候选身份和扩展证据；
- 现有命令 Hook 的结构化参数迁移；
- 一个只用于平台验收的内置合同探针；
- 维护者校验、检查、来源核对、合同探针和历史入口。

## 核心决定

1. Super Dev Core 继续是唯一生命周期和阶段所有者；
2. 阶段 1 只执行仓库内置适配器；项目清单只能校验，不能自动取得执行资格；
3. 不接入完成前验证或其他真实外部方法；
4. 不使用整段 Shell 命令；旧 Hook 命令字符串被阻止并获得迁移说明；
5. `.cmd`、`.bat`、`.ps1` 和任意 Shell 表达式首版不可直接执行；
6. 扩展默认关闭，运行历史与主工作流状态分开；
7. 内置适配器使用仓库内路径和内容摘要，不把包含自身的提交号写回自身文件；
8. 外部改编方法的上游提交与摘要合同只定义数据形状，本阶段不下载、不安装、不执行。

## 影响范围

预计修改：

- `super_dev/extensions/**`；
- `super_dev/extensions/builtins/*.yaml`；
- `super_dev/extensions/sources.lock.yaml`；
- `super_dev/hooks/models.py`；
- `super_dev/hooks/manager.py`；
- `super_dev/config/schema_validator.py`；
- CLI 参数与治理命令分发模块；
- `tests/extensions/**`；
- 相关 Hook、配置和 CLI 测试。

## 不在范围内

- 注册中心、解析器、自动发现和远程市场；
- 完成前验证、系统化排错、独立评审、TDD、Idea Forge、Grill；
- UmaDev 知识导入；
- 新图形界面；
- 九阶段真实控制变更；
- 用户级 Skill 或配置同步；
- 自动提交、合并、推送、PR、部署和外部写入。

## 风险

1. 旧命令 Hook 会从“继续运行”变为“阻止并迁移”，属于有意的安全行为变化；
2. Windows 作业对象实现若不完整，可能遗留子进程；
3. 路径守卫若只做字符串前缀比较，可能被大小写、目录连接、UNC 或不同盘符绕过；
4. 候选摘要若遗漏暂存或未跟踪内容，旧证据可能被错误复用；
5. 清单自报能力若被直接信任，扩展可能越权；
6. 输出或环境脱敏不完整可能泄露凭据。

## 回滚

- `extensions.enabled=false` 关闭扩展入口；
- 新扩展模块没有调用者时不影响 Core；
- 扩展运行历史保留只读，不自动删除；
- 不迁移主工作流状态；
- Hook 安全迁移如需回退，必须单独评估安全风险，不能静默恢复 `shell=True`；
- 回滚不修改用户级 Skill、用户配置或远程分支。

## 文档确认

用户已于 2026-08-25 确认以下文档：

- `output/minimal-extension-platform-research.md`；
- `output/minimal-extension-platform-prd.md`；
- `output/minimal-extension-platform-architecture.md`；
- `output/minimal-extension-platform-uiux.md`。
