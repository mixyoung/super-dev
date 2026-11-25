"""未决事项登记簿 (Parking Lot Register)

管理跨会话、跨迭代的架构妥协与挂起决策。
将暂缓/妥协项统一归口到 `.super-dev/parking-lot.json`，保持核心 PRD/架构文档只记录已冻结定论，
避免在核心文档反复打补丁而稀释 AI 注意力；解除挂起时要求先将最终定论回写核心文档。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

_logger = logging.getLogger("super_dev.parking_lot")

PARKING_LOT_FILENAME = "parking-lot.json"
PARKING_LOT_DIR = ".super-dev"
_PLACEHOLDER_VALUES = {"", "tbd", "todo", "待定", "待办", "待评估", "暂无", "none", "n/a"}
_VALID_STATUSES = {"pending", "resolved", "superseded"}
_SELF_REFERENTIAL_FILENAMES = {"parking-lot.json", "session_brief.md"}
_ALLOWED_DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}
_CORE_DOC_SUFFIXES = ("-prd.md", "-architecture.md", "-uiux.md")
_EXPLICIT_TOKEN_LEAK_RE = re.compile(r"\b(?:TBD|TBA|FIXME|TODO)\b")
_EXPLICIT_COLON_TODO_RE = re.compile(r"\btodo\s*[:：]", re.IGNORECASE)
_BRACKET_DEFERRAL_RE = re.compile(
    r"[\[【（(]\s*(?:待定|待评估|待确认|暂定|暂缓|TODO|TBD)\s*[\]】）)]"
)
_FIELD_DEFERRAL_RE = re.compile(
    r"(?:[:：|]\s*(?:待定|待评估|待确认|暂定|暂无定论|后续再说|以后再定)\s*(?:[|]|$))"
)
_PATCH_DEFERRAL_RE = re.compile(r"(?:暂缓决定|先用临时妥协方案|临时妥协方案|待后续迭代拍板)")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_anchor_token(text: str) -> str:
    cleaned = re.sub(r"[`*_~]", "", text.strip().lower())
    return re.sub(r"[\s\-_/\\.:：,，。()（）\[\]【】]+", "", cleaned)


def _extract_markdown_headings(text: str) -> list[str]:
    headings: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def _snapshot_core_doc_digests(project_dir: Path | str) -> dict[str, str]:
    project_root = Path(project_dir).resolve()
    output_dir = project_root / "output"
    if not output_dir.is_dir():
        return {}
    digests: dict[str, str] = {}
    for suffix in _CORE_DOC_SUFFIXES:
        for path in sorted(output_dir.glob(f"*{suffix}")):
            if path.is_file():
                try:
                    rel = path.relative_to(project_root).as_posix()
                    digests[rel] = _sha256_file(path)
                except OSError:
                    continue
    return digests


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
    blocks_delivery: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )
    resolved_at: str = ""
    resolution_notes: str = ""
    resolved_target: str = ""
    resolved_target_digest: str = ""
    source_doc_digests: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParkingLotItem:
        raw_digests = data.get("source_doc_digests")
        source_doc_digests = (
            {
                str(k).strip(): str(v).strip()
                for k, v in raw_digests.items()
                if str(k).strip() and str(v).strip()
            }
            if isinstance(raw_digests, dict)
            else {}
        )
        return cls(
            id=str(data.get("id", "")).strip(),
            title=str(data.get("title", "")).strip(),
            reason_for_deferral=str(data.get("reason_for_deferral", "")).strip(),
            revisit_trigger=str(data.get("revisit_trigger", "")).strip(),
            current_compromise=str(data.get("current_compromise", "")).strip(),
            status=str(data.get("status", "pending")).strip().lower() or "pending",
            affected_components=(
                [str(c).strip() for c in data.get("affected_components", []) if str(c).strip()]
                if isinstance(data.get("affected_components"), list)
                else []
            ),
            blocks_delivery=bool(data.get("blocks_delivery", False)),
            created_at=str(data.get("created_at", "")).strip(),
            resolved_at=str(data.get("resolved_at", "")).strip(),
            resolution_notes=str(data.get("resolution_notes", "")).strip(),
            resolved_target=str(data.get("resolved_target", "")).strip(),
            resolved_target_digest=str(data.get("resolved_target_digest", "")).strip(),
            source_doc_digests=source_doc_digests,
        )


class ParkingLotRegister:
    """未决事项登记簿管理器"""

    def __init__(self, items: list[ParkingLotItem] | None = None) -> None:
        self.items: list[ParkingLotItem] = items or []

    @classmethod
    def get_file_path(cls, project_dir: Path | str) -> Path:
        return Path(project_dir) / PARKING_LOT_DIR / PARKING_LOT_FILENAME

    @classmethod
    def inspect_integrity(cls, project_dir: Path | str) -> tuple[ParkingLotRegister, str | None]:
        """严格加载并校验登记簿文件结构，防止 JSON 损坏静默绕过门禁"""
        path = cls.get_file_path(project_dir)
        if not path.exists():
            return cls([]), None
        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return cls([]), f"未决事项登记簿 JSON 解析失败 ({path.name}): {e}"

        raw_items = raw_data.get("items") if isinstance(raw_data, dict) else raw_data
        if not isinstance(raw_items, list):
            return cls([]), f"未决事项登记簿结构非法 ({path.name}): items 必须为列表"

        items: list[ParkingLotItem] = []
        for idx, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                return cls([]), f"未决事项登记簿第 {idx + 1} 项不是对象"
            items.append(ParkingLotItem.from_dict(raw_item))
        return cls(items), None

    @classmethod
    def load(cls, project_dir: Path | str) -> ParkingLotRegister:
        """从项目目录加载未决事项登记簿"""
        reg, err = cls.inspect_integrity(project_dir)
        if err:
            _logger.warning("加载未决事项登记簿失败 %s: %s", cls.get_file_path(project_dir), err)
        return reg

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
            f.write("\n")
        _logger.info("未决事项登记簿已保存至 %s (%d 项)", path, len(self.items))
        return path

    def _allocate_next_id(self) -> str:
        max_num = 0
        for item in self.items:
            match = re.fullmatch(r"PARK-(\d+)", item.id.strip())
            if match:
                max_num = max(max_num, int(match.group(1)))
        return f"PARK-{max(max_num, len(self.items)) + 1:03d}"

    def add_item(
        self,
        title: str,
        reason_for_deferral: str,
        revisit_trigger: str,
        current_compromise: str,
        affected_components: list[str] | None = None,
        item_id: str = "",
        blocks_delivery: bool = False,
        project_dir: Path | str | None = None,
    ) -> ParkingLotItem:
        """添加一条未决决策或技术妥协（可选记录当时核心文档基线摘要）"""
        if not item_id:
            item_id = self._allocate_next_id()

        source_doc_digests = (
            _snapshot_core_doc_digests(project_dir) if project_dir is not None else {}
        )
        item = ParkingLotItem(
            id=item_id,
            title=title.strip(),
            reason_for_deferral=reason_for_deferral.strip(),
            revisit_trigger=revisit_trigger.strip(),
            current_compromise=current_compromise.strip(),
            affected_components=[c.strip() for c in (affected_components or []) if c.strip()],
            blocks_delivery=bool(blocks_delivery),
            source_doc_digests=source_doc_digests,
        )
        self.items.append(item)
        return item

    def get_item(self, item_id: str) -> ParkingLotItem | None:
        target = item_id.strip()
        for item in self.items:
            if item.id == target:
                return item
        return None

    def resolve_item(
        self,
        item_id: str,
        resolution_notes: str = "",
        resolved_target: str = "",
        *,
        status: str = "resolved",
        project_dir: Path | str | None = None,
    ) -> bool:
        """标记一条未决事项为已解决或已被替代，强制校验最终说明、锚点与核心文档实改回写"""
        normalized_status = status.strip().lower()
        if normalized_status not in {"resolved", "superseded"}:
            raise ValueError(f"无效的解除状态: {status}")
        item = self.get_item(item_id)
        if item is None:
            return False
        errors = self.validate_resolution_fields(
            resolution_notes,
            resolved_target,
            project_dir=project_dir,
            status=normalized_status,
            source_doc_digests=item.source_doc_digests,
        )
        if errors:
            raise ValueError("; ".join(errors))
        item.status = normalized_status
        item.resolved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        item.resolution_notes = resolution_notes.strip()
        item.resolved_target = resolved_target.strip()
        if project_dir is not None:
            resolved_path, _ = self._resolve_target_path(resolved_target, project_dir)
            if resolved_path is not None and resolved_path.is_file():
                item.resolved_target_digest = _sha256_file(resolved_path)
        return True

    def get_open_items(self) -> list[ParkingLotItem]:
        """获取所有处于生效挂起状态的未决事项"""
        return [item for item in self.items if item.status == "pending"]

    def get_blocking_open_items(self) -> list[ParkingLotItem]:
        """获取所有标记为阻塞交付的挂起事项"""
        return [item for item in self.get_open_items() if item.blocks_delivery]

    def render_markdown_table(self) -> str:
        """渲染为易于嵌入简报的 Markdown 表格"""
        open_items = self.get_open_items()
        if not open_items:
            return "当前无挂起的未决决策或技术妥协。"

        lines = [
            "| 编号 | 挂起主题 | 暂缓原因 | 重启触发条件 | 当前折衷方案 | 影响组件 | 交付门禁 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for it in open_items:
            comps = ", ".join(it.affected_components) if it.affected_components else "全局/暂未限定"
            gate_flag = "阻塞交付" if it.blocks_delivery else "非阻塞"
            lines.append(
                f"| `{it.id}` | {it.title} | {it.reason_for_deferral} | "
                f"{it.revisit_trigger} | {it.current_compromise} | {comps} | {gate_flag} |"
            )
        return "\n".join(lines)

    @staticmethod
    def validate_item_fields(
        title: str,
        reason_for_deferral: str,
        revisit_trigger: str,
        current_compromise: str,
    ) -> list[str]:
        """校验单条未决事项输入的三要素完整性"""
        errors: list[str] = []
        if not title.strip():
            errors.append("缺少挂起主题标题")
        if reason_for_deferral.strip().lower() in _PLACEHOLDER_VALUES:
            errors.append("暂缓原因不明确，禁止使用空洞占位符")
        if revisit_trigger.strip().lower() in _PLACEHOLDER_VALUES:
            errors.append("缺少明确的重启评估触发条件")
        if current_compromise.strip().lower() in _PLACEHOLDER_VALUES:
            errors.append("缺少当前阶段的临时折衷方案")
        return errors

    @staticmethod
    def _resolve_target_path(
        resolved_target: str,
        project_dir: Path | str,
    ) -> tuple[Path | None, str]:
        raw = resolved_target.strip()
        path_part = raw.split("#", 1)[0].strip()
        if not path_part:
            return None, ""
        project_root = Path(project_dir).resolve()
        win_path = PureWindowsPath(path_part)
        posix_path = Path(path_part)
        try:
            candidate = (
                posix_path.resolve(strict=False)
                if posix_path.is_absolute() or bool(win_path.drive)
                else (project_root / posix_path).resolve(strict=False)
            )
            rel = candidate.relative_to(project_root).as_posix()
        except Exception:
            return None, ""
        return candidate, rel

    @classmethod
    def validate_resolved_target(
        cls,
        resolved_target: str,
        project_dir: Path | str | None = None,
        *,
        source_doc_digests: dict[str, str] | None = None,
        recorded_target_digest: str = "",
    ) -> list[str]:
        """校验解除未决事项时的核心文档回写路径、扩展名、锚点与实改证据"""
        raw = resolved_target.strip()
        if raw.lower() in _PLACEHOLDER_VALUES:
            return [
                "必须提供已回写最终定论的核心文档路径 resolved_target（例如 output/<project>-architecture.md）"
            ]

        has_anchor = "#" in raw
        path_part, _, raw_anchor = raw.partition("#")
        path_part = path_part.strip()
        anchor = raw_anchor.strip()
        if path_part.lower() in _PLACEHOLDER_VALUES:
            return ["回写目标文件路径不能为空"]
        if has_anchor and not anchor:
            return [f"回写目标包含空锚点 '#': {resolved_target}"]

        win_path = PureWindowsPath(path_part)
        posix_path = Path(path_part)
        if ".." in win_path.parts or ".." in posix_path.parts:
            return [f"回写目标路径包含非法父级跳转: {resolved_target}"]

        normalized_lower = path_part.replace("\\", "/").lower().lstrip("./")
        if (
            posix_path.name.lower() in _SELF_REFERENTIAL_FILENAMES
            or normalized_lower.endswith(".super-dev/parking-lot.json")
            or normalized_lower.endswith(".super-dev/session_brief.md")
        ):
            return ["禁止将未决事项账本或简报本身作为定论回写目标，请先写回核心 PRD/架构/Spec 文档"]

        if posix_path.suffix.lower() not in _ALLOWED_DOC_EXTENSIONS:
            return [
                f"核心文档回写目标必须是文档文件 ({', '.join(sorted(_ALLOWED_DOC_EXTENSIONS))}): {path_part}"
            ]

        if project_dir is None:
            return []

        candidate, rel = cls._resolve_target_path(raw, project_dir)
        if candidate is None:
            return [f"回写目标路径超出项目根目录范围: {resolved_target}"]

        if not candidate.is_file():
            return [f"核心文档回写目标不存在，请先落盘定论文件: {path_part}"]

        try:
            content = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return [f"无法读取回写目标文档 ({path_part}): {exc}"]

        if not content.strip():
            return [f"核心文档回写目标内容为空: {path_part}"]

        if anchor:
            norm_anchor = _normalize_anchor_token(anchor)
            headings = _extract_markdown_headings(content)
            matched = any(
                norm_anchor
                and (
                    norm_anchor == _normalize_anchor_token(h)
                    or norm_anchor in _normalize_anchor_token(h)
                )
                for h in headings
            )
            if not matched:
                return [f"核心文档回写目标锚点不存在: #{anchor}（未在 {path_part} 找到对应标题）"]

        if source_doc_digests and rel in source_doc_digests:
            baseline_digest = source_doc_digests[rel]
            effective_digest = recorded_target_digest.strip() or _sha256_file(candidate)
            if effective_digest == baseline_digest:
                return [
                    f"核心文档 {rel} 自挂起登记后未发生内容更新，请先将最终定论回写到该文档再执行 resolve"
                ]

        return []

    @classmethod
    def validate_resolution_fields(
        cls,
        resolution_notes: str,
        resolved_target: str,
        project_dir: Path | str | None = None,
        *,
        status: str = "resolved",
        source_doc_digests: dict[str, str] | None = None,
        recorded_target_digest: str = "",
    ) -> list[str]:
        """校验未决事项解除/替代的完整闭环条件"""
        errors: list[str] = []
        if status.strip().lower() not in {"resolved", "superseded"}:
            errors.append(f"无效的解除状态: {status}")
        if resolution_notes.strip().lower() in _PLACEHOLDER_VALUES:
            errors.append("必须提供非占位符的最终决策说明 resolution_notes")
        errors.extend(
            cls.validate_resolved_target(
                resolved_target,
                project_dir=project_dir,
                source_doc_digests=source_doc_digests,
                recorded_target_digest=recorded_target_digest,
            )
        )
        return errors

    def validate_compliance(
        self,
        project_dir: Path | str | None = None,
        *,
        require_no_blocking_open: bool = False,
    ) -> list[dict[str, str]]:
        """合规性硬校验：未决三要素完整、阻塞项清零、已解除项须落盘回写核心文档"""
        violations: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for it in self.items:
            item_id = it.id or "<missing-id>"
            if not it.id:
                violations.append({"id": item_id, "error": "条目缺少唯一编号 id"})
            elif it.id in seen_ids:
                violations.append({"id": item_id, "error": "存在重复的未决事项编号"})
            else:
                seen_ids.add(it.id)

            if it.status not in _VALID_STATUSES:
                violations.append({"id": item_id, "error": f"非法条目状态: {it.status}"})
                continue

            if it.status == "pending":
                for err in self.validate_item_fields(
                    it.title,
                    it.reason_for_deferral,
                    it.revisit_trigger,
                    it.current_compromise,
                ):
                    violations.append({"id": item_id, "error": err})
                if require_no_blocking_open and it.blocks_delivery:
                    violations.append(
                        {
                            "id": item_id,
                            "error": "存在标记为阻塞交付的未决事项，须拍板并回写核心文档后解除",
                        }
                    )
            else:
                for err in self.validate_resolution_fields(
                    it.resolution_notes,
                    it.resolved_target,
                    project_dir=project_dir,
                    status=it.status,
                    source_doc_digests=it.source_doc_digests,
                    recorded_target_digest=it.resolved_target_digest,
                ):
                    violations.append({"id": item_id, "error": err})
        return violations

    def get_resolved_target_paths(self, project_dir: Path | str) -> list[Path]:
        """返回所有已解除项指向且真实存在的核心文档路径（去重保序）"""
        paths: list[Path] = []
        seen: set[Path] = set()
        for it in self.items:
            if it.status not in {"resolved", "superseded"} or not it.resolved_target.strip():
                continue
            candidate, _ = self._resolve_target_path(it.resolved_target, project_dir)
            if candidate is not None and candidate.is_file() and candidate not in seen:
                seen.add(candidate)
                paths.append(candidate)
        return paths


def scan_core_docs_for_untracked_deferrals(
    project_dir: Path | str,
    *,
    artifact_prefix: str = "",
) -> list[dict[str, Any]]:
    """扫描核心 PRD/架构文档是否残留未拆入第二账本的占位或暂缓补丁"""
    project_root = Path(project_dir).resolve()
    output_dir = project_root / "output"
    if not output_dir.is_dir():
        return []

    candidates: list[Path] = []
    if artifact_prefix.strip():
        prefix = artifact_prefix.strip()
        for suffix in ("prd.md", "architecture.md"):
            doc = output_dir / f"{prefix}-{suffix}"
            if doc.is_file():
                candidates.append(doc)
    else:
        for pattern in ("*-prd.md", "*-architecture.md"):
            candidates.extend(sorted(output_dir.glob(pattern)))

    leaks: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    for doc_path in candidates:
        resolved = doc_path.resolve()
        if resolved in seen_files or not resolved.is_file():
            continue
        seen_files.add(resolved)
        try:
            text = resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel_path = resolved.relative_to(project_root).as_posix()
        in_fence = False
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            stripped = raw_line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence or not stripped or stripped.startswith(">"):
                continue

            has_parking_ref = bool(re.search(r"(?:PARK-\d+|parking-lot\.json)", raw_line))
            cleaned = re.sub(r"`[^`]*`", "", raw_line)
            cleaned = re.sub(r"https?://\S+", "", cleaned)
            reason = ""
            if _EXPLICIT_TOKEN_LEAK_RE.search(cleaned) or _EXPLICIT_COLON_TODO_RE.search(cleaned):
                reason = "核心文档正文中存在未决策占位符 (TBD/TBA/TODO/FIXME)"
            elif not has_parking_ref:
                if _BRACKET_DEFERRAL_RE.search(cleaned):
                    reason = "核心文档存在未归口到第二账本的待定/暂缓标记"
                elif _FIELD_DEFERRAL_RE.search(cleaned):
                    reason = "核心文档字段存在待定/暂定/暂无定论占位值"
                elif _PATCH_DEFERRAL_RE.search(cleaned):
                    reason = "核心文档正文出现未归口到 .super-dev/parking-lot.json 的暂缓/妥协描述"

            if reason:
                leaks.append(
                    {
                        "file": rel_path,
                        "line": line_no,
                        "reason": reason,
                        "snippet": stripped[:120],
                    }
                )
    return leaks


def summarize_parking_lot(
    project_dir: Path | str,
    *,
    artifact_prefix: str = "",
    require_no_blocking_open: bool = False,
) -> dict[str, Any]:
    """汇总第二套账本完整健康状态（文件完整性 + 条目合规 + 核心文档反泄漏扫描）"""
    project_root = Path(project_dir).resolve()
    file_path = ParkingLotRegister.get_file_path(project_root)
    exists = file_path.exists()
    reg, integrity_error = ParkingLotRegister.inspect_integrity(project_root)
    violations = (
        [{"id": "PARKING-LOT", "error": integrity_error}]
        if integrity_error
        else reg.validate_compliance(
            project_dir=project_root,
            require_no_blocking_open=require_no_blocking_open,
        )
    )
    core_doc_leaks = scan_core_docs_for_untracked_deferrals(
        project_root,
        artifact_prefix=artifact_prefix,
    )
    open_items = reg.get_open_items()
    blocking_items = reg.get_blocking_open_items()
    resolved_count = sum(1 for it in reg.items if it.status in {"resolved", "superseded"})
    passed = integrity_error is None and not violations and not core_doc_leaks
    return {
        "exists": exists,
        "file_path": str(file_path),
        "open_count": len(open_items),
        "blocking_open_count": len(blocking_items),
        "resolved_count": resolved_count,
        "total_count": len(reg.items),
        "integrity_error": integrity_error,
        "violations": violations,
        "core_doc_leaks": core_doc_leaks,
        "passed": passed,
    }
