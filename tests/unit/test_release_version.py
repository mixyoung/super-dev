"""Published runtime/version surfaces must agree with the package metadata."""

from pathlib import Path

import pytest
import yaml

from super_dev import __version__
from super_dev.branding import VERSION
from super_dev.config.manager import ProjectConfig
from super_dev.skills.skill_template import SUPER_DEV_VERSION


def test_runtime_version_surfaces_agree_with_pyproject(capsys):
    from super_dev.cli import SuperDevCLI

    root = Path(__file__).resolve().parents[2]
    version_line = next(
        line
        for line in (root / "pyproject.toml").read_text(encoding="utf-8").splitlines()
        if line.startswith("version = ")
    )
    assert version_line.split('"')[1] == __version__ == VERSION == SUPER_DEV_VERSION
    assert ProjectConfig(name="release-test").version == __version__
    with pytest.raises(SystemExit) as result:
        SuperDevCLI().run(["--version"])
    assert result.value.code == 0
    assert f"super-dev {__version__}" in capsys.readouterr().out


def test_generated_skill_versions_match_runtime():
    root = Path(__file__).resolve().parents[2]
    for name in ("super-dev", "super-dev-seeai"):
        text = (root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        assert frontmatter["metadata"]["version"] == __version__
