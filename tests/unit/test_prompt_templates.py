"""Prompt 模板版本管理单元测试"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from super_dev.creators.prompt_templates import (
    PromptTemplate,
    PromptTemplateManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_template(**overrides) -> PromptTemplate:
    defaults = dict(
        id="tpl-test",
        name="Test Template",
        version="1.0.0",
        phase="docs",
        description="A test template",
        template="Hello {name}, welcome to {project}.",
        variables=["name", "project"],
        metadata={"author": "tester"},
    )
    defaults.update(overrides)
    return PromptTemplate(**defaults)


def _write_template_file(
    directory: Path,
    filename: str,
    *,
    tpl_id: str = "tpl-demo",
    name: str = "Demo",
    version: str = "1.0.0",
    phase: str = "docs",
    description: str = "demo",
    variables: list[str] | None = None,
    body: str = "Content with {var1}.",
) -> Path:
    """在目录中写入一个符合 front-matter 格式的模板文件。"""
    if variables is None:
        variables = ["var1"]
    front = {
        "id": tpl_id,
        "name": name,
        "version": version,
        "phase": phase,
        "description": description,
        "variables": variables,
        "author": "test-author",
    }
    text = f"---\n{yaml.dump(front, allow_unicode=True)}---\n{body}"
    filepath = directory / filename
    filepath.write_text(text, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# PromptTemplate dataclass
# ---------------------------------------------------------------------------


class TestPromptTemplate:
    def test_render_success(self):
        tpl = _make_template()
        result = tpl.render({"name": "Alice", "project": "SuperDev"})
        assert result == "Hello Alice, welcome to SuperDev."

    def test_render_missing_variable_raises(self):
        tpl = _make_template()
        with pytest.raises(KeyError, match="缺少变量"):
            tpl.render({"name": "Alice"})  # missing "project"

    def test_render_extra_variables_ignored(self):
        tpl = _make_template()
        result = tpl.render({"name": "Bob", "project": "X", "extra": "ignored"})
        assert "Bob" in result
        assert "ignored" not in result

    def test_render_no_variables(self):
        tpl = _make_template(template="static text", variables=[])
        assert tpl.render({}) == "static text"

    def test_default_metadata(self):
        tpl = PromptTemplate(
            id="t",
            name="t",
            version="0.0.1",
            phase="docs",
            description="",
            template="",
        )
        assert tpl.metadata == {}
        assert tpl.variables == []


# ---------------------------------------------------------------------------
# PromptTemplateManager — loading
# ---------------------------------------------------------------------------


class TestManagerLoading:
    def test_default_relative_dir_resolves_to_package_templates(self):
        mgr = PromptTemplateManager()
        assert mgr.templates_dir.name == "templates"
        assert mgr.templates_dir.exists()

    def test_empty_dir(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        assert len(mgr.templates) == 0

    def test_nonexistent_dir(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path / "nonexistent"))
        assert len(mgr.templates) == 0

    def test_loads_template_files(self, tmp_path: Path):
        _write_template_file(tmp_path, "prd_template_v1.md", tpl_id="prd-gen")
        mgr = PromptTemplateManager(str(tmp_path))
        assert "prd-gen" in mgr.templates

    def test_ignores_non_template_files(self, tmp_path: Path):
        # 文件名不匹配 *_template_*.md 模式
        (tmp_path / "readme.md").write_text("---\nid: bad\n---\nbody", encoding="utf-8")
        mgr = PromptTemplateManager(str(tmp_path))
        assert "bad" not in mgr.templates

    def test_skips_files_without_frontmatter(self, tmp_path: Path):
        (tmp_path / "no_template_fm.md").write_text("no front matter here", encoding="utf-8")
        mgr = PromptTemplateManager(str(tmp_path))
        assert len(mgr.templates) == 0

    def test_reload(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        assert len(mgr.templates) == 0

        _write_template_file(tmp_path, "new_template_v1.md", tpl_id="new-one")
        mgr.reload()
        assert "new-one" in mgr.templates

    def test_manifest_enriches_metadata(self, tmp_path: Path):
        _write_template_file(tmp_path, "demo_template_v1.md", tpl_id="tpl-demo")
        manifest = {
            "templates": [
                {"id": "tpl-demo", "name": "Enriched Name", "metadata": {"priority": 1}},
            ]
        }
        (tmp_path / "manifest.yaml").write_text(
            yaml.dump(manifest, allow_unicode=True),
            encoding="utf-8",
        )
        mgr = PromptTemplateManager(str(tmp_path))
        tpl = mgr.templates["tpl-demo"]
        assert tpl.name == "Enriched Name"
        assert tpl.metadata["priority"] == 1


# ---------------------------------------------------------------------------
# PromptTemplateManager — get / render
# ---------------------------------------------------------------------------


class TestManagerGetRender:
    def test_get_template_success(self, tmp_path: Path):
        _write_template_file(tmp_path, "x_template_v1.md", tpl_id="x")
        mgr = PromptTemplateManager(str(tmp_path))
        tpl = mgr.get_template("x")
        assert tpl.id == "x"

    def test_get_template_not_found(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        with pytest.raises(KeyError, match="不存在"):
            mgr.get_template("missing")

    def test_render_increments_usage(self, tmp_path: Path):
        _write_template_file(
            tmp_path,
            "r_template_v1.md",
            tpl_id="r",
            body="Hi {var1}!",
            variables=["var1"],
        )
        mgr = PromptTemplateManager(str(tmp_path))
        assert mgr.templates["r"].metadata.get("usage_count", 0) == 0

        result = mgr.render("r", {"var1": "World"})
        assert "World" in result
        assert mgr.templates["r"].metadata["usage_count"] == 1

        mgr.render("r", {"var1": "Again"})
        assert mgr.templates["r"].metadata["usage_count"] == 2

    def test_render_sets_last_used(self, tmp_path: Path):
        _write_template_file(
            tmp_path,
            "lu_template_v1.md",
            tpl_id="lu",
            body="{var1}",
            variables=["var1"],
        )
        mgr = PromptTemplateManager(str(tmp_path))
        mgr.render("lu", {"var1": "test"})
        assert "last_used" in mgr.templates["lu"].metadata

    def test_render_missing_var_raises(self, tmp_path: Path):
        _write_template_file(
            tmp_path,
            "mv_template_v1.md",
            tpl_id="mv",
            body="{a} {b}",
            variables=["a", "b"],
        )
        mgr = PromptTemplateManager(str(tmp_path))
        with pytest.raises(KeyError):
            mgr.render("mv", {"a": "only_a"})


# ---------------------------------------------------------------------------
# PromptTemplateManager — list / filter
# ---------------------------------------------------------------------------


class TestManagerListFilter:
    def test_list_all(self, tmp_path: Path):
        _write_template_file(tmp_path, "a_template_v1.md", tpl_id="a", phase="docs")
        _write_template_file(tmp_path, "b_template_v1.md", tpl_id="b", phase="spec")
        mgr = PromptTemplateManager(str(tmp_path))
        assert len(mgr.list_templates()) == 2

    def test_list_filter_by_phase(self, tmp_path: Path):
        _write_template_file(tmp_path, "c_template_v1.md", tpl_id="c", phase="docs")
        _write_template_file(tmp_path, "d_template_v1.md", tpl_id="d", phase="review")
        mgr = PromptTemplateManager(str(tmp_path))
        docs_only = mgr.list_templates(phase="docs")
        assert len(docs_only) == 1
        assert docs_only[0].id == "c"

    def test_list_filter_no_match(self, tmp_path: Path):
        _write_template_file(tmp_path, "e_template_v1.md", tpl_id="e", phase="docs")
        mgr = PromptTemplateManager(str(tmp_path))
        assert mgr.list_templates(phase="nonexistent") == []


# ---------------------------------------------------------------------------
# PromptTemplateManager — version history
# ---------------------------------------------------------------------------


class TestManagerVersionHistory:
    def test_history_recorded_on_load(self, tmp_path: Path):
        _write_template_file(tmp_path, "h_template_v1.md", tpl_id="h", version="1.2.0")
        mgr = PromptTemplateManager(str(tmp_path))
        history = mgr.get_template_history("h")
        assert len(history) == 1
        assert history[0]["version"] == "1.2.0"
        assert "date" in history[0]
        assert "author" in history[0]

    def test_history_recorded_on_register(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        tpl = _make_template(id="reg1", version="2.0.0")
        mgr.register_template(tpl)
        history = mgr.get_template_history("reg1")
        assert len(history) == 1
        assert history[0]["version"] == "2.0.0"

    def test_history_empty_for_unknown(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        assert mgr.get_template_history("unknown") == []

    def test_multiple_versions_tracked(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        tpl_v1 = _make_template(id="mv", version="1.0.0")
        tpl_v2 = _make_template(id="mv", version="2.0.0")
        mgr.register_template(tpl_v1)
        mgr.register_template(tpl_v2)
        history = mgr.get_template_history("mv")
        assert len(history) == 2
        assert history[0]["version"] == "1.0.0"
        assert history[1]["version"] == "2.0.0"


# ---------------------------------------------------------------------------
# PromptTemplateManager — register_template
# ---------------------------------------------------------------------------


class TestManagerRegister:
    def test_register_makes_template_available(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        tpl = _make_template(id="manual")
        mgr.register_template(tpl)
        assert mgr.get_template("manual") is tpl

    def test_register_overwrites_same_id(self, tmp_path: Path):
        mgr = PromptTemplateManager(str(tmp_path))
        tpl1 = _make_template(id="dup", name="First")
        tpl2 = _make_template(id="dup", name="Second")
        mgr.register_template(tpl1)
        mgr.register_template(tpl2)
        assert mgr.get_template("dup").name == "Second"
