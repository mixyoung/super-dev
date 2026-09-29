"""批 D1（governance-remediation-2026-09）：架构漂移否定语境回归测试。

回归案例：架构文档写明“不采用 SQLite 状态数据库”，漂移报告曾把 SQLite 列为
Declared Tech Stack 缺失（NOT FOUND）。修复后否定命中的技术名单独呈现，不再判缺失。
"""

from pathlib import Path

from super_dev.reviewers.architecture_drift import (
    DriftReport,
    _parse_architecture_doc,
)


def _write_doc(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    output.mkdir(parents=True, exist_ok=True)
    doc = output / "negation-architecture.md"
    doc.write_text(
        "# 架构\n\n"
        "> 核心决定：文件型权威状态 + 统一提交入口；不采用全量事件溯源或 SQLite 状态数据库。\n\n"
        "后端采用 FastAPI 提供本地 API。\n",
        encoding="utf-8",
    )
    return doc


def test_negated_tech_is_excluded_from_declared_stack(tmp_path: Path) -> None:
    parsed = _parse_architecture_doc(_write_doc(tmp_path))

    assert any(t.lower() == "fastapi" for t in parsed["tech_stack"])
    assert all(t.lower() != "sqlite" for t in parsed["tech_stack"])
    assert any(t.lower() == "sqlite" for t in parsed["negated_tech_stack"])


def test_negated_tech_not_marked_missing_in_markdown() -> None:
    report = DriftReport(
        project_name="negation",
        declared_tech_stack=["FastAPI"],
        negated_tech_stack=["SQLite"],
        actual_tech_stack=["FastAPI"],
    )

    markdown = report.to_markdown()

    assert "SQLite **[NOT FOUND]**" not in markdown
    assert "SQLite（架构文档明确排除，不计入缺失）" in markdown


def test_affirmative_mentions_still_declared(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir(parents=True, exist_ok=True)
    doc = output / "plain-architecture.md"
    doc.write_text(
        "# 架构\n\n数据层使用 PostgreSQL；缓存使用 Redis。\n",
        encoding="utf-8",
    )

    parsed = _parse_architecture_doc(doc)

    assert any(t.lower() == "postgresql" for t in parsed["tech_stack"])
    assert any(t.lower() == "redis" for t in parsed["tech_stack"])
    assert parsed["negated_tech_stack"] == []
