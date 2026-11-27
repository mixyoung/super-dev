# Tasks

## 3. 源码与证据

- [x] **3.1: 退出 Pillow 和像素审美评分**
  - 删除生产调用、自动截图及两个开发依赖声明，检查锁只删无用 Pillow 项；固定合法 PNG 保留下载测试。
  - 已用无 Pillow 的最终 wheel 复验实际入口。
  - Refs: ui-review-evidence-boundary#review-boundary
- [x] **3.2: 独立写入源码、浏览器运行、视觉评审结果**
  - 沿用现有证据信封和工作项/当前代码版本绑定；运行与视觉使用宿主实际记录，不由源码推断。
  - 已用原图输入及响应核对真实正反例。
  - Refs: ui-review-evidence-boundary#review-boundary
- [x] **3.3: 统一质量、就绪、证据包和 Web 读路径**
  - 缺失、过期、执行失败和不适用分别处理；保持 GET 只读、现有质量阈值与用户预览门。
  - 相关正反例回归已通过；不代表本工作树的项目级质量门禁或发布就绪已通过。
  - Depends on: 3.2
  - Refs: ui-review-evidence-boundary#shared-consumption

## 4. 宿主指导与验证

- [x] **4.1: 同步默认提示、Skill 与宿主规则**
  - 复用宿主浏览器和图片输入；明确能力不足或记录无法对应时不得放行。
  - 四份仓库生成副本已通过一致性检查，未改用户全局 Skill。
  - Refs: ui-review-evidence-boundary#review-boundary
- [x] **4.2: 运行行为测试与干净发行复验**
  - 受影响范围四组回归 288 项通过。最终 wheel 不装 Pillow 完成五次实际 CLI 调用，并重新校验正常、缺陷及视觉未验证的宿主记录。
  - 逐条验收、合成与实测的区别，以及剩余未验证项见 `output/ui-review-evidence-boundary-delivery.md`；未运行全仓测试。
  - Depends on: 3.1, 3.2, 3.3, 4.1
  - Refs: ui-review-evidence-boundary#shared-consumption
