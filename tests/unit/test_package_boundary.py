from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from setuptools import find_packages


def test_published_package_excludes_comparison_fixtures_and_tools() -> None:
    project_dir = Path(__file__).resolve().parents[2]
    published = set(find_packages(where=str(project_dir), include=["super_dev*"]))

    assert "super_dev" in published
    assert "tools" not in published
    assert not any(name == "tests" or name.startswith("tests.") for name in published)


def test_removed_shadow_validation_module_is_not_importable() -> None:
    assert importlib.util.find_spec("super_dev.shadow_validation") is None


def test_production_modules_do_not_import_test_or_tool_packages() -> None:
    project_dir = Path(__file__).resolve().parents[2]
    source_files = sorted((project_dir / "super_dev").rglob("*.py"))

    offenders: list[str] = []
    for path in source_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_roots: set[str] = set()
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            if imported_roots & {"tests", "tools"}:
                offenders.append(path.relative_to(project_dir).as_posix())
                break

    assert offenders == []
