"""未决事项登记簿 (Parking Lot Register)

管理跨会话、跨迭代的架构妥协与挂起决策。
提供结构化 JSON 持久化、合规性断言与 Markdown 投影能力，
防止长期项目中悬而未决的技术债务在会话压缩或跨轮次开发中遗忘丢失。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.parking_lot")

PARKING_LOT_FILENAME = "parking-lot.json"
PARKING_LOT_DIR = ".super-dev"


@dataclass
class ParkingLotItem:
    """单个未决事项条目"""

    id: str
    title: str
    reason_for_deferral: str
    revisit_trigger: str
    current_compromise: str
    status: str = "pending"  # pending | resolved | superseded
    affected_components: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )
    resolved_at: str = ""
    resolution_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParkingLotItem:
        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            reason_for_deferral=str(data.get("reason_for_deferral", "")).strip(),
            revisit_trigger=str(data.get("revisit_trigger", "")).strip(),
            current_compromise=str(data.get("current_compromise", "")).strip(),
            status=str(data.get("status", "pending")).strip().lower(),
            affected_components=list(data.get("affected_components", [])),
            created_at=str(data.get("created_at", "")).strip(),
            resolved_at=str(data.get("resolved_at", "")).strip(),
            resolution_notes=str(data.get("resolution_notes", "")).strip(),
        )


class ParkingLotRegister:
    """未决事项登记簿管理器"""

    def __init__(self, items: list[ParkingLotItem] | None = None) -> None:
        self.items: list[ParkingLotItem] = items or []

    @classmethod
    def get_file_path(cls, project_dir: Path | str) -> Path:
        return Path(project_dir) / PARKING_LOT_DIR / PARKING_LOT_FILENAME

    @classmethod
    def load(cls, project_dir: Path | str) -> ParkingLotRegister:
        """从项目目录加载未决事项登记簿"""
        path = cls.get_file_path(project_dir)
        if not path.exists():
            return cls([])

        try:
            with open(path, encoding="utf-8") as f:
                raw_data = json.load(f)
            raw_items = raw_data.get("items", []) if isinstance(raw_data, dict) else raw_data
            items = [ParkingLotItem.from_dict(item) for item in raw_items if isinstance(item, dict)]
            return cls(items)
        except Exception as e:
            _logger.warning("加载未决事项登记簿失败 %s: %s", path, e)
            return cls([])

    def save(self, project_dir: Path | str) -> Path:
        """持久化保存登记簿到 .super-dev/parking-lot.json"""
        path = self.get_file_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "items": [item.to_dict() for item in self.items],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        _logger.info("未决事项登记簿已保存至 %s (%d 项)", path, len(self.items))
        return path

    def add_item(
        self,
        title: str,
        reason_for_deferral: str,
        revisit_trigger: str,
        current_compromise: str,
        affected_components: list[str] | None = None,
        item_id: str = "",
    ) -> ParkingLotItem:
        """添加一条未决决策或技术妥协"""
        if not item_id:
            next_idx = len(self.items) + 1
            item_id = f"PARK-{next_idx:03d}"

        item = ParkingLotItem(
            id=item_id,
            title=title.strip(),
            reason_for_deferral=reason_for_deferral.strip(),
            revisit_trigger=revisit_trigger.strip(),
            current_compromise=current_compromise.strip(),
            affected_components=affected_components or [],
        )
        self.items.append(item)
        return item

    def resolve_item(self, item_id: str, resolution_notes: str = "") -> bool:
        """标记一条未决事项为已解决"""
        for item in self.items:
            if item.id == item_id:
                item.status = "resolved"
                item.resolved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                item.resolution_notes = resolution_notes.strip()
                return True
        return False

    def get_open_items(self) -> list[ParkingLotItem]:
        """获取所有处于生效挂起状态的未决事项"""
        return [item for item in self.items if item.status == "pending"]

    def render_markdown_table(self) -> str:
        """渲染为易于嵌入文档或简报的 Markdown 表格"""
        open_items = self.get_open_items()
        if not open_items:
            return "当前无挂起的未决决策或技术妥协。"

        lines = [
            "| 编号 | 挂起主题 | 暂缓原因 | 重启触发条件 | 当前折衷方案 | 影响组件 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for it in open_items:
            comps = ", ".join(it.affected_components) if it.affected_components else "全局/暂未限定"
            lines.append(
                f"| `{it.id}` | {it.title} | {it.reason_for_deferral} | "
                f"{it.revisit_trigger} | {it.current_compromise} | {comps} |"
            )
        return "\n".join(lines)

    def validate_compliance(self) -> list[dict[str, str]]:
        """合规性校验：确保未决事项不是模糊推诿，必须具备理由、触发条件和折衷设计三要素"""
        violations: list[dict[str, str]] = []
        for it in self.get_open_items():
            if not it.title:
                violations.append({"id": it.id, "error": "缺少挂起主题标题"})
            if not it.reason_for_deferral or it.reason_for_deferral.lower() in {"tbd", "待定", "待办"}:
                violations.append({"id": it.id, "error": "暂缓原因不明确，禁止使用空洞占位符"})
            if not it.revisit_trigger or it.revisit_trigger.lower() in {"tbd", "待定", "待评估"}:
                violations.append({"id": it.id, "error": "缺少明确的重启评估触发条件"})
            if not it.current_compromise or it.current_compromise.lower() in {"tbd", "待定"}:
                violations.append({"id": it.id, "error": "缺少当前阶段的临时折衷方案"})
        return violations
