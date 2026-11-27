from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CLAUDE_DESIGN_RUNTIME_CHECKS: dict[str, str] = {
    "ui_screen_recipes": "screen_recipes",
    "ui_design_context_protocol": "design_context_protocol",
    "ui_tweak_strategy": "tweak_strategy",
    "ui_verification_handoff": "verification_handoff",
}


UI_REVIEW_EVIDENCE_GUIDANCE = (
    "- 仅对适用的 UI：宿主实际打开目标页面，完成关键交互，并保留桌面、移动端及关键状态的原始截图。\n"
    "- 将截图实际传给具备图片能力的主模型，或交给已获授权的视觉工具；对照确认的 UI/UX 检查布局、信息层级、可读性和品牌一致性；发现注明截图、可见位置和依据。\n"
    "- 源码规则、浏览器运行与交互、视觉评审分别留证。绑定工作项、当前代码版本、确认文档、页面地址、视口、状态、文件摘要以及可核对的实际图片输入与评审记录。\n"
    "- 截图存在、路径、OCR、像素统计或 `vision_used=true` 不能证明已经看图。无图片能力、传递失败、记录无法对应或范围不全时保留已完成项，必需项标为未验证、验收受阻；不得擅自切换外部服务。\n"
    "- 记录格式见 Super Dev 包内 `templates/ui-review-evidence.md`。UI review 汇总证据，不替代实际执行；标准模式下用户预览确认仍是独立门禁。\n"
)


def ui_contract_requires_claude_design_runtime(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    return any(
        bool(payload.get(field_name)) for field_name in CLAUDE_DESIGN_RUNTIME_CHECKS.values()
    )


def required_claude_design_runtime_checks(payload: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not ui_contract_requires_claude_design_runtime(payload):
        return ()
    return tuple(CLAUDE_DESIGN_RUNTIME_CHECKS.keys())


def missing_claude_design_runtime_checks(
    checks: Mapping[str, Any] | None,
    payload: Mapping[str, Any] | None,
) -> list[str]:
    if not isinstance(checks, Mapping):
        checks = {}
    return [
        check_name
        for check_name in required_claude_design_runtime_checks(payload)
        if not bool(checks.get(check_name, False))
    ]
