# 真实候选 1 运行记录

## 预登记

- 候选编号：`completion-verification-candidate-001`；
- 候选名称：Super Dev 完成前验证实现候选 1；
- 分支：`feature/completion-verification`；
- 基础提交：`32e84385e0b400fad0fdbf7deb37329485ac8941`；
- 范围：完成前验证、扩展证据、发布就绪唯一入口、指标与 Windows 隔离；
- 独立验收人：用户；
- 登记时间：2026-08-25T09:31:13.615913+00:00；
- 登记发生在正式运行之前。

## 本次运行

- 运行编号（`run_id`）：`4db2f3d3e9f945c49e77592df703075f`；
- 验证状态：`FAIL`；
- 测试总数：148；
- 实际执行：147；
- 失败：2；
- 错误：0；
- 跳过：1；
- 验证耗时：191165.27 毫秒；
- 候选运行前后一致；
- 进程树清理完成；
- JUnit 摘要：`sha256:1dd607abd3b3bbd95844b675f73c1ddd924ed9c32317b52d5e08cf9a4fc05e42`；
- 结果路径：`.super-dev/extensions/runs/4db2f3d3e9f945c49e77592df703075f/result.json`；
- 最终验收标签：误阻断（`false_block`）；
- 验收人：用户；
- 用户已于 2026-08-25 明确确认该标签。

## 两项失败

1. `tests/extensions/test_fresh_verification_service.py::test_service_blocks_when_test_changes_candidate`；
2. `tests/extensions/test_service.py::test_changed_candidate_records_evidence_invalidation`。

## 归因证据

- 完成前验证按已确认设计把 pytest 临时目录放在 `.super-dev/extensions/runs/<run_id>/pytest-temp`；
- 上述两项测试会在 pytest 的 `tmp_path` 中创建临时项目；
- 因为 `tmp_path` 位于真实仓库内部，临时项目执行 Git 命令时会向上发现真实父仓库；
- 临时测试文件位于真实仓库已忽略的 `.super-dev/extensions/**` 下，所以 Git 候选摘要看不到测试中的临时文件变化；
- 同一批扩展与安全启动器测试在正常外部临时目录环境中为 93 项通过、1 项跳过；
- 因此现有证据表明，失败由试点执行环境改变测试语义引起，不是候选本身存在对应产品缺陷。

## 建议验收

用户已确认标记为误阻断（`false_block`）。该标签只评价本次完成前验证阻断是否正确，不改变原始测试结果和运行证据。

## 建议修复

保持临时目录仍位于受控运行目录，同时给 pytest 子进程设置 Git 上探边界（`GIT_CEILING_DIRECTORIES`）为本次 `pytest-temp`。这样：

- 从真实项目根目录运行的测试仍能读取当前仓库；
- 在 `pytest-temp` 下创建的临时项目不会错误继承父仓库；
- 不需要把临时目录移到证据允许范围之外；
- 修复后必须创建新的运行编号，不能改写本次失败结果。

## 修复与第二次运行

- 用户已授权增加 Git 上探边界（`GIT_CEILING_DIRECTORIES`）；
- Core 把边界固定为本次 `pytest-temp`；
- 回归测试确认真实项目根目录仍能识别当前 Git，临时项目不再继承父仓库；
- 新运行编号（`run_id`）：`b7b5bf4f2ca74a72ba9a66dc6deb9eeb`；
- 状态：`PASS`；
- 测试总数：149；
- 实际执行：148；
- 失败：0；
- 错误：0；
- 跳过：1；
- 候选运行前后一致；
- 进程树清理完成；
- JUnit 摘要：`sha256:fd81f8f6d78f1b36edc97633f3a7a7c906dea0c0294039d4747c1a9cdef7a66a`；
- 结果路径：`.super-dev/extensions/runs/b7b5bf4f2ca74a72ba9a66dc6deb9eeb/result.json`；
- 最终验收标签：正确通过（`correct_pass`）；
- 验收人：用户；
- 用户已于 2026-08-25 明确确认该标签。

整个发布就绪报告仍被旧的文档覆盖、运行边界、基线确认、合规和交付证据缺口阻断；这些不属于完成前验证本身。本次完成前验证关键检查已经通过。

真实候选 1 现已完成：第一次运行记录为误阻断（`false_block`），修复后第二次运行记录为正确通过（`correct_pass`）。两次运行使用不同运行编号，原始失败证据未被覆盖。
