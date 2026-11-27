# UI 验收取证：宿主记录格式 v1

源码规则、浏览器运行与交互、视觉评审是三份独立结果。只为适用的 UI 工作取证。以下是格式说明，不是已完成的证据；不得复制示例冒充实际执行。

## 运行之前

用本项目已安装的 Super Dev Python 包，在当前项目中创建 `UIReviewEvidence(project_dir, current_prefix)`，从 `capture_binding()` 取得工作项、当前代码版本和 UI/UX、UI 契约摘要。将这次快照传给实际浏览器和看图步骤；查看旧截图时不刷新这组字段。范围由当前 `*-ui-contract.json` 的 `screen_recipes` 给定，使用各配方 `id` 和 `required_states`，分别覆盖桌面、移动端及默认态。范围不明确时向用户说明，不能让执行者自行缩小。

在宿主用获准的工具运行真实页面，按目标状态执行导航、交互，记录实际页面 URL、视口、错误及原图。项目原始记录与截图放在 `output/ui-review/<实际运行编号>/`。去除地址和日志里的凭据、个人信息；没有授权不要发送到其他服务。

## 浏览器记录

从宿主实际执行记录整理 `format: super-dev-browser-run/v1` 的 JSON。字段：

- `binding`：运行前的快照；`run_id`：实际浏览器运行编号；`observed_at`：含时区的 ISO 时间。
- `producer`：`kind: browser`、`host`、`id`（实际工具标识）；若关联已有 Web 工作流，另填实际 `workflow_run_id`。
- `pages`：每项含唯一 `id`、契约 `screen`、`state`、实际 `url`、`observed_at`、可对照的宿主 `event_id`、`viewport: {device, width, height}`。`device` 为 `desktop` 或 `mobile`。`file` 指向本次原始 PNG/JPEG，`loaded_files` 列出与浏览器实际加载内容可核对的项目内源文件或构建文件。所有文件引用均为 `{path, sha256}`，以项目相对正斜线路径和实际字节十六进制摘要记录；不要用当前文件摘要硬贴到未知远端页面上。
- `steps`：每页附实际 `navigation` 和 `interaction`，每步含 `kind`、`action`、`expected`、`observed` 和 `status`（`PASS` 或 `FAIL`）。实际失败可在未取得截图时单独记录；跳过的步骤不是失败，不得填作通过。

将已有记录路径交给 `UIReviewEvidence.record_host_result(RUNTIME, record_path)`。它写入 `output/<prefix>-frontend-runtime.json`，不操作浏览器。旧 `frontend-runtime` 布尔值及 `frontend-source-checks` 只能说明静态探测。

## 视觉评审记录

有视觉能力的宿主主模型实际接收图片时，生产者类型为 `host_model`；无视觉主模型可使用已获准的视觉工具，类型为 `vision_tool`。从宿主/工具只导出与此次调用相关的输入和响应记录。接收了路径、OCR 文本、像素指标而非图像时，不写成 `image`。

- 图片输入清单 `format: super-dev-host-image-input/v1`：`producer: {kind, host, id}`、`run_id`、`observed_at`、`input_event_id`（实际图片输入的事件）。`attachments` 逐图标明实际输入的 `screenshot_id`、`content_type: image`、`media_type` 和 `sha256`，并以 `event_id`、`input_event: {path, sha256}` 引用宿主实际输入事件摘录。摘录保留原事件 `tool_use_id`（或 `id`）、`type`（`tool_result`、`tool_input` 或 `image_message`）和原始 `content` 的图片块：`type: image`、`source: {type: base64, media_type, data}`。检查器比对图片块实际字节，不接受自报标记、文本编码串或只有路径的事件。仅保存相关图片块，去掉无关文本和敏感元数据。若经裁剪、遮盖或缩放，记录 `derivation` 和原图引用；当前完整视觉通过只接受可核对的原始输入。
- 视觉响应 `format: super-dev-image-review/v1`：同一执行者和 `run_id`，记录 `binding`、`observed_at`、`browser_run_id`、`input_record: {path, sha256}`、`response_record: {path, sha256}`、实际 `response_event_id` 及 `response_to`（输入事件清单中匹配的图片事件）。响应摘录须保留 `id`（或 `tool_use_id`）、`type`（`review_message`、`tool_use` 或 `tool_result`）、原 `timestamp` 和相关 `content`，不保留无关会话。`observations` 的每一项含 `screenshot_id`、`dimension`（`layout`、`hierarchy`、`readability`、`brand`）、`status`、`location`、`observation`、`requirement`；失败还须写 `impact`、`recommendation`。通过结论也写实际看见什么，不只填“已检查”。

将视觉响应路径交给 `UIReviewEvidence.record_host_result(VISUAL, record_path)`，生成 `output/<prefix>-ui-visual-review.json`。源码检查器分开写 `output/<prefix>-ui-source-review.json`；既有 UI review 入口只汇总结果。可用 Python 常量 `RUNTIME`、`VISUAL` 和类 `UIReviewEvidence` 从 `super_dev.reviewers.ui_review_evidence` 导入。

缺少可保留的真实输入、响应对应不上、页面未覆盖或宿主无图片能力时，保留其他检查并说明未验证。若仅记录本次未验证原因，可在视觉响应里填 `blocked_reason`：`no_image_capability`、`image_transfer_failed`、`tool_unavailable`、`partial_vision` 或 `input_record_unavailable`，不要填伪造的输入或观察。JSON 的结构和摘要只能核对链路一致性，不能认证宿主日志签名，也不能证明模型内部如何理解图片。截屏和程序检查不是用户预览确认，两者不相互代替。
