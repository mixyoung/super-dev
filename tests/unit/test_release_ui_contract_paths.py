"""UI contract materialization must not treat display names as paths."""

import html
import json
from pathlib import Path

import pytest

from super_dev.creators.frontend_builder import FrontendScaffoldBuilder
from super_dev.creators.implementation_builder import ImplementationScaffoldBuilder
from super_dev.creators.task_executor import SpecTaskExecutor


@pytest.mark.parametrize("name", ["normal-app", "Mixed_Case", "中文项目", "My App", "CON"])
def test_normal_contract_path_and_content_are_preserved(tmp_path, name):
    path = tmp_path / "output" / f"{name}-ui-contract.json"
    path.parent.mkdir()
    original = '{"frozen": true, "name": "unchanged"}\n'
    path.write_text(original, encoding="utf-8")
    builder = FrontendScaffoldBuilder(tmp_path, name, "description")
    assert builder._load_ui_contract() == json.loads(original)
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "name", ["test<>app&", 'a:b"c|d?e*f', "../outside", "..\\outside", "bad\x00name"]
)
def test_invalid_display_name_materializes_one_local_contract(tmp_path, name):
    builder = FrontendScaffoldBuilder(tmp_path, name, "description")
    payload = builder._load_ui_contract()
    files = list((tmp_path / "output").glob("*-ui-contract.json"))
    assert len(files) == 1
    assert files[0].parent == tmp_path / "output"
    assert not any(char in files[0].name for char in '<>:"/\\|?*\x00')
    assert builder.name == name
    stored_payload = json.loads(json.dumps(payload))
    assert builder._load_ui_contract() == stored_payload
    assert (
        ImplementationScaffoldBuilder(tmp_path, name, "react", "node").ui_contract == stored_payload
    )
    # The task executor must consume the same frozen contract, not fall back silently.
    payload["framework_playbook"] = {"focus": "chosen-framework"}
    files[0].write_text(json.dumps(payload), encoding="utf-8")
    assert "chosen-framework" in SpecTaskExecutor(tmp_path, name)._read_framework_focus()


def test_distinct_invalid_names_do_not_share_contracts(tmp_path):
    first = FrontendScaffoldBuilder(tmp_path, "a<b", "first")
    second = FrontendScaffoldBuilder(tmp_path, "a>b", "second")
    first._load_ui_contract()
    files = list((tmp_path / "output").glob("*-ui-contract.json"))
    files[0].write_text('{"sentinel": "first"}', encoding="utf-8")
    assert second._load_ui_contract() != {"sentinel": "first"}
    assert first._load_ui_contract() == {"sentinel": "first"}
    assert len(list((tmp_path / "output").glob("*-ui-contract.json"))) == 2


def test_html_keeps_escaped_display_name(tmp_path):
    name = "test<>app&"
    builder = FrontendScaffoldBuilder(tmp_path, name, "description")
    result = builder.generate([], [], {})
    content = Path(result["html"]).read_text(encoding="utf-8")
    assert html.escape(name) in content
    assert name not in content
