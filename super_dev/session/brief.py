"""
Session Brief Manager -- 10 段标准格式的会话状态管理。
10 段标准格式的会话状态管理。

管理 .super-dev/SESSION_BRIEF.md，提供加载、保存、单段更新、
模板生成和压缩摘要等能力，供 pipeline 各阶段和宿主集成使用。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

_logger = logging.getLogger("super_dev.session.brief")

# ---------------------------------------------------------------------------
# Section constants
# ---------------------------------------------------------------------------

SECTION_NAMES: list[str] = [
    "Session Title",
    "Current State",
    "Open Decisions",
    "Task Specification",
    "Files and Functions",
    "Workflow",
    "Errors & Corrections",
    "Codebase Documentation",
    "Learnings",
    "Key Results",
    "Worklog",
]

MAX_SECTION_TOKENS = 2000
MAX_TOTAL_TOKENS = 12000

BRIEF_FILENAME = "SESSION_BRIEF.md"
BRIEF_DIR = ".super-dev"

# Rough token estimator: 1 token ~ 4 chars for English, ~2 chars for CJK.
# We use a conservative 3-char-per-token average for mixed content.
_CHARS_PER_TOKEN = 3

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Rough token count based on character length."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _brief_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / BRIEF_DIR / BRIEF_FILENAME


def _section_header(name: str) -> str:
    """Return the Markdown H2 header for a section."""
    return f"## {name}"


# ---------------------------------------------------------------------------
# SessionBrief
# ---------------------------------------------------------------------------


class SessionBrief:
    """Manages a 10-section SESSION_BRIEF.md file.

    Each section is stored as a Markdown H2 block.  The class provides CRUD
    operations at the section level plus a condensed-context builder for
    injecting brief state into prompts.
    """

    # -- load ---------------------------------------------------------------

    @staticmethod
    def load(project_dir: str | Path) -> dict[str, str]:
        """Load an existing brief and return sections as a dict.

        Returns an empty dict if the file does not exist.  Unknown sections
        found in the file are preserved under their original header name.
        """
        path = _brief_path(project_dir)
        if not path.exists():
            _logger.debug("SESSION_BRIEF.md not found at %s", path)
            return {}

        raw = path.read_text(encoding="utf-8")
        return SessionBrief._parse_sections(raw)

    # -- save ---------------------------------------------------------------

    @staticmethod
    def save(project_dir: str | Path, sections: dict[str, str]) -> Path:
        """Write *sections* to SESSION_BRIEF.md, using the canonical order.

        Sections whose names are in ``SECTION_NAMES`` are written in the
        standard order; any extra keys are appended at the end.
        Returns the path of the written file.
        """
        path = _brief_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = ["# SESSION BRIEF", ""]
        # Canonical sections first
        for name in SECTION_NAMES:
            content = sections.get(name, "")
            lines.append(_section_header(name))
            lines.append("")
            if content.strip():
                lines.append(content.strip())
            else:
                lines.append("_(empty)_")
            lines.append("")

        # Extra non-standard sections
        extra_keys = [k for k in sections if k not in SECTION_NAMES]
        for name in extra_keys:
            content = sections[name]
            lines.append(_section_header(name))
            lines.append("")
            lines.append(content.strip() if content.strip() else "_(empty)_")
            lines.append("")

        text = "\n".join(lines)
        path.write_text(text, encoding="utf-8")
        _logger.info("SESSION_BRIEF.md saved to %s (%d chars)", path, len(text))
        return path

    # -- update_section -----------------------------------------------------

    @staticmethod
    def update_section(
        project_dir: str | Path,
        section_name: str,
        content: str,
    ) -> Path:
        """Update (or create) a single section, preserving the rest.

        If the brief does not exist yet a new one is created with only the
        given section populated.
        """
        sections = SessionBrief.load(project_dir)
        sections[section_name] = content
        return SessionBrief.save(project_dir, sections)

    # -- generate_template --------------------------------------------------

    @staticmethod
    def generate_template(project_name: str) -> str:
        """Return an empty 10-section template as a Markdown string.

        Useful for bootstrapping a new brief before any pipeline phase runs.
        """
        lines: list[str] = ["# SESSION BRIEF", ""]
        for name in SECTION_NAMES:
            lines.append(_section_header(name))
            lines.append("")
            if name == "Session Title":
                lines.append(f"{project_name} -- new session")
            else:
                lines.append("_(empty)_")
            lines.append("")
        return "\n".join(lines)

    # -- sync_parking_lot ---------------------------------------------------

    @staticmethod
    def sync_parking_lot(project_dir: str | Path) -> None:
        """从 .super-dev/parking-lot.json 自动同步未决事项到 SESSION_BRIEF.md 的 Open Decisions 段落。"""
        from super_dev.parking_lot import ParkingLotRegister

        project_path = Path(project_dir)
        brief_path = _brief_path(project_path)
        reg = ParkingLotRegister.load(project_path)
        table_md = reg.render_markdown_table()

        # 若 SESSION_BRIEF.md 由 StateStore 生成（含来源工作项/状态修订元数据），则仅就地刷新
        # ## Open Decisions 段落，避免破坏 StateStore.session_brief_health() 校验头。
        if brief_path.exists():
            raw = brief_path.read_text(encoding="utf-8")
            if "- 来源工作项:" in raw and "- 状态修订:" in raw:
                updated = SessionBrief._replace_section_preserving_header(
                    raw, "Open Decisions", table_md
                )
                brief_path.write_text(updated, encoding="utf-8")
                return

        SessionBrief.update_section(project_path, "Open Decisions", table_md)

    @staticmethod
    def _replace_section_preserving_header(raw: str, section_name: str, content: str) -> str:
        header_line = _section_header(section_name)
        lines = raw.splitlines()
        start_idx: int | None = None
        end_idx: int = len(lines)
        for idx, line in enumerate(lines):
            if line.strip() == header_line:
                start_idx = idx
                continue
            if start_idx is not None and re.match(r"^##\s+.+$", line):
                end_idx = idx
                break

        replacement_block = [header_line, "", content.strip() or "_(empty)_", ""]
        if start_idx is not None:
            new_lines = lines[:start_idx] + replacement_block + lines[end_idx:]
        else:
            insert_at = len(lines)
            for idx, line in enumerate(lines):
                if re.match(r"^##\s+.+$", line):
                    insert_at = idx
                    break
            new_lines = lines[:insert_at] + [""] + replacement_block + lines[insert_at:]
        return "\n".join(new_lines).rstrip() + "\n"

    # -- summarize_for_context ----------------------------------------------

    @staticmethod
    def summarize_for_context(
        project_dir: str | Path,
        max_tokens: int = MAX_TOTAL_TOKENS,
    ) -> str:
        """Build a condensed context string suitable for prompt injection.

        Sections are included in canonical order.  If the total exceeds
        *max_tokens* (estimated), later sections are truncated with a
        ``[truncated]`` marker.
        """
        sections = SessionBrief.load(project_dir)
        if not sections:
            return ""

        parts: list[str] = []
        remaining = max_tokens

        for name in SECTION_NAMES:
            content = sections.get(name, "").strip()
            if not content or content == "_(empty)_":
                continue

            header = f"### {name}"
            header_tokens = _estimate_tokens(header)

            if remaining <= header_tokens + 10:
                parts.append("... [truncated]")
                break

            remaining -= header_tokens
            content_tokens = _estimate_tokens(content)

            if content_tokens <= remaining:
                parts.append(header)
                parts.append(content)
                remaining -= content_tokens
            else:
                # Truncate content to fit
                char_budget = remaining * _CHARS_PER_TOKEN
                truncated = content[: max(0, char_budget - 20)] + " ...[truncated]"
                parts.append(header)
                parts.append(truncated)
                remaining = 0
                break

        return "\n\n".join(parts)

    # -- internal -----------------------------------------------------------

    @staticmethod
    def _parse_sections(raw: str) -> dict[str, str]:
        """Parse Markdown text into a section-name -> content dict."""
        sections: dict[str, str] = {}
        current_name: str | None = None
        buffer: list[str] = []

        for line in raw.splitlines():
            match = re.match(r"^##\s+(.+)$", line)
            if match:
                # Flush previous section
                if current_name is not None:
                    sections[current_name] = "\n".join(buffer).strip()
                current_name = match.group(1).strip()
                buffer = []
            elif current_name is not None:
                buffer.append(line)

        # Flush last section
        if current_name is not None:
            sections[current_name] = "\n".join(buffer).strip()

        return sections
