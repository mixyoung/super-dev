# Tasks

工作项：`super-dev-dsh-desktop`。任务状态、需求引用和依赖沿用本地记录；运行记录在本分支只保留脱敏结论。

## 1. 规格与治理准备

- [x] **1.1: 绑定真实文档确认并创建当前 change**
  - Refs: super-dev-dsh-desktop::DSH-05

- [x] **1.2: 完成规格、计划、任务和吸纳范围并校验**
  - Refs: super-dev-dsh-desktop::DSH-08
  - Depends on: 1.1

- [x] **1.3: 核对无 UI 适用路径并交接单一生产写入者**
  - Refs: super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-08
  - Depends on: 1.2

## 3. 正式接入与装卸修复

- [x] **3.1: 接通 DSH 身份、能力、选择及全部真实消费者**
  - Refs: super-dev-dsh-desktop::DSH-01, super-dev-dsh-desktop::DSH-07
  - Depends on: 1.3

- [x] **3.2: 唯一模板渲染双技能和 DSH 限定规则**
  - Refs: super-dev-dsh-desktop::DSH-02, super-dev-dsh-desktop::DSH-04
  - Depends on: 1.3

- [x] **3.3: 修复实际装卸链的幂等、归属及字节保护**
  - Refs: super-dev-dsh-desktop::DSH-03
  - Depends on: 3.2

- [x] **3.4: 实现注入用户目录及部分失败恢复**
  - Refs: super-dev-dsh-desktop::DSH-03, super-dev-dsh-desktop::DSH-07
  - Depends on: 3.1, 3.3

- [x] **3.5: 补齐旧消费者、Core 合同与新增宿主回归**
  - Refs: super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-08
  - Depends on: 3.1, 3.2, 3.3, 3.4

## 4. 回归与质量

- [x] **4.1: 模板同步、贡献范围和能力覆盖检查**
  - Refs: super-dev-dsh-desktop::DSH-02, super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 3.5

- [x] **4.2: 执行适用测试、构建、lint 和类型检查**
  - Refs: super-dev-dsh-desktop::DSH-08
  - Depends on: 3.5

- [~] **4.3: 独立只读审查并修复确认问题**
  - Refs: super-dev-dsh-desktop::DSH-03, super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-08
  - Depends on: 4.1, 4.2

## 5. 真实桌面验收

- [~] **5.1: 建立本轮隔离夹具与原生解析/发现证据**
  - Refs: super-dev-dsh-desktop::DSH-01, super-dev-dsh-desktop::DSH-02, super-dev-dsh-desktop::DSH-07
  - Depends on: 4.1, 4.2

- [ ] **5.2: 测标准/SEEAI、工作模式、只读和文档门**
  - Refs: super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 5.1

- [ ] **5.3: 测标准 UI 样例的预览门**
  - Refs: super-dev-dsh-desktop::DSH-05
  - Depends on: 5.1

- [ ] **5.4: 缺失、损坏及真实卸载三种回退动态验证**
  - Refs: super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-07
  - Depends on: 5.1

## 7. 已确认的无模型隔离原型

- [x] **7.1: 完成原型规格、版本与单写入者准入**
  - Refs: super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 1.2, 4.2

- [x] **7.2: 在真实原生入口验证项目专属来源拒绝**
  - Refs: super-dev-dsh-desktop::DSH-02, super-dev-dsh-desktop::DSH-04
  - Depends on: 7.1

- [x] **7.3: 验证规则不足与旧历史的确定拒绝**
  - Refs: super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-06
  - Depends on: 7.2

- [~] **7.4: 实现并验证父子与重试共享请求预算**
  - Refs: super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-07
  - Depends on: 7.1

- [~] **7.5: 原型联调、停止与资源归属检查**
  - Refs: super-dev-dsh-desktop::DSH-03, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-08
  - Depends on: 7.3, 7.4

- [~] **7.6: 固定原型差异的复核与阶段性报告**
  - Refs: super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 7.5

## 8. 当前不使用虚拟机的同版准备

- [x] **8.1: 绑定新确认与当前限制并刷新原规格**
  - Refs: super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-08
  - Depends on: 7.1

- [x] **8.2: 建立显式选择的冻结rc.3同版副本**
  - Refs: super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-07
  - Depends on: 8.1

- [x] **8.3: 运行同版原生矩阵并复核旧消费者**
  - Refs: super-dev-dsh-desktop::DSH-04, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-08
  - Depends on: 8.2

- [x] **8.4: 记录非虚拟机当前准入与后续API条件**
  - Refs: super-dev-dsh-desktop::DSH-03, super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 8.3

## 9. 非虚拟机桌面资源与启动准备

- [x] **9.1: 物化并校验完整公开桌面资源副本**
  - Refs: super-dev-dsh-desktop::DSH-03, super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 8.4

- [x] **9.2: 固定完整桌面的启动输入和副作用边界**
  - Refs: super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-07
  - Depends on: 9.1

- [x] **9.3: 验证资源装配与运行准入，保留真实待决定项**
  - Refs: super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 9.2

## 10. 可选 DSH 伴生插件

- [x] **10.1: 实现并验证可选的只读接入增强**
  - Refs: super-dev-dsh-desktop::DSH-01, super-dev-dsh-desktop::DSH-06, super-dev-dsh-desktop::DSH-07
  - Depends on: 3.5

## 11. DSH 主开发插件

- [x] **11.1: 接通原生命令、现有 Core 与执行门禁**
  - Refs: super-dev-dsh-desktop::DSH-01, super-dev-dsh-desktop::DSH-05, super-dev-dsh-desktop::DSH-06
  - Depends on: 10.1

- [x] **11.2: 原生回归与本地制品交付**
  - Refs: super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 11.1

## 6. 本地交付

- [ ] **6.1: 汇总十四项验收、阻断项与资源归属**
  - Refs: super-dev-dsh-desktop::DSH-07, super-dev-dsh-desktop::DSH-08
  - Depends on: 4.3, 5.2, 5.3, 5.4

## 验收摘要

- 在官方未修改的 rc.3 Windows 桌面版上，隔离环境中的安装、卸载及双原生命令显示/消失对照已通过（`PASS`）。曾以离线适配器验证 Core 文档与确认门，140 项 Core 回归和八份旧宿主渲染对照通过（`PASS`）；不等同正式开发验收。
- 绑定的标准合成样例已通过原生命令进入调研（`research`）。后续真实请求曾到达上游并收到 HTTP 200，但回复未通过本地协议检查，没有写成核心文档，也没有到达文档确认门。后续候选仅经本地检查，未在原版桌面复跑；实机验收已停止。
- 原版的共享技能回退对照 A12 仍失败（`FAIL`）；隔离修复对照不替代原版。标准样例的后续确认、预览、后端、质量与交付，以及独立 SEEAI 全流程，尚未完成。原始回执、运行环境配置、模型请求和制品均不随公开分支分发。
