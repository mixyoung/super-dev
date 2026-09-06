"""Synchronize generated Super Dev Skill surfaces from one canonical template."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


TRACKED_SURFACES = {
    "codex": (
        REPO_ROOT / ".agents" / "skills" / "super-dev" / "SKILL.md",
        REPO_ROOT / "plugins" / "super-dev-codex" / "skills" / "super-dev" / "SKILL.md",
    ),
    "claude-code": (
        REPO_ROOT / ".claude" / "skills" / "super-dev" / "SKILL.md",
        REPO_ROOT / "plugins" / "super-dev-claude" / "skills" / "super-dev" / "SKILL.md",
    ),
}


SEEAI_SURFACES = (
    REPO_ROOT / ".agents" / "skills" / "super-dev-seeai" / "SKILL.md",
    REPO_ROOT / "plugins" / "super-dev-codex" / "skills" / "super-dev-seeai" / "SKILL.md",
)


def rendered_skill(host: str, skill_name: str = "super-dev") -> str:
    from super_dev.skills.skill_template import SkillTemplate

    return SkillTemplate.for_builtin(skill_name, host).render(host)


def collect_mismatches(user_codex_path: Path | None = None) -> list[Path]:
    mismatches: list[Path] = []
    for host, paths in TRACKED_SURFACES.items():
        expected = rendered_skill(host)
        mismatches.extend(
            path
            for path in paths
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        )
    expected_seeai = rendered_skill("codex", "super-dev-seeai")
    mismatches.extend(
        path
        for path in SEEAI_SURFACES
        if not path.exists() or path.read_text(encoding="utf-8") != expected_seeai
    )
    if user_codex_path is not None:
        expected = rendered_skill("codex")
        if not user_codex_path.exists() or user_codex_path.read_text(encoding="utf-8") != expected:
            mismatches.append(user_codex_path)
    return mismatches


def write_surfaces(user_codex_path: Path | None = None) -> None:
    for host, paths in TRACKED_SURFACES.items():
        expected = rendered_skill(host)
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    for path in SEEAI_SURFACES:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered_skill("codex", "super-dev-seeai"), encoding="utf-8")
    if user_codex_path is not None:
        user_codex_path.parent.mkdir(parents=True, exist_ok=True)
        user_codex_path.write_text(rendered_skill("codex"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or write all Super Dev Skill copies from skill_template.py."
    )
    parser.add_argument("--write", action="store_true", help="Write generated tracked copies.")
    parser.add_argument(
        "--user-codex-path",
        type=Path,
        help="Optional explicit installed Codex SKILL.md path to check or synchronize.",
    )
    args = parser.parse_args()

    if args.write:
        write_surfaces(args.user_codex_path)

    mismatches = collect_mismatches(args.user_codex_path)
    if mismatches:
        for path in mismatches:
            print(f"OUT_OF_SYNC={path}")
        return 1

    print("SUPER_DEV_SKILLS_IN_SYNC=yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
