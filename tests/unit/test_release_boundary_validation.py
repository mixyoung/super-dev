"""Regression coverage for the remaining release type/input boundaries."""

import json
import logging
import socket
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from super_dev.creators.document_generator import DocumentGenerator
from super_dev.creators.frontend_builder import FrontendScaffoldBuilder
from super_dev.deployers.rehearsal_runner import LaunchRehearsalRunner, RehearsalCheck
from super_dev.knowledge_evolution import KnowledgeEvolutionAnalyzer
from super_dev.knowledge_evolution import _logger as evolution_logger
from super_dev.memory.extractor import _extract_redteam_memories
from super_dev.orchestrator.knowledge_pusher import KnowledgePush, KnowledgePusher


@pytest.mark.parametrize("issues", [None, {}, "not a list", False])
def test_invalid_issues_are_reported_without_losing_valid_findings(issues, caplog):
    reports = {"invalid": {"issues": issues}, "valid": {"issues": ["genuine"]}}
    with caplog.at_level(logging.WARNING):
        entries = _extract_redteam_memories("redteam", {"quality_reports": reports})
    assert len(entries) == 1
    assert entries[0].content == "- genuine"
    assert caplog.records


@pytest.mark.parametrize("value", [None, "false", 0, {}, True, False])
def test_only_boolean_results_enter_constraint_statistics(tmp_path, monkeypatch, caplog, value):
    analyzer = KnowledgeEvolutionAnalyzer(tmp_path)
    written = []
    warning = MagicMock(wraps=evolution_logger.warning)
    monkeypatch.setattr(evolution_logger, "warning", warning)
    monkeypatch.setattr(
        analyzer.db, "record_constraint_result", lambda *args: written.append(args[2])
    )
    monkeypatch.setattr(analyzer.db, "update_effectiveness_scores", lambda: None)
    monkeypatch.setattr(analyzer, "_generate_suggestions", lambda *_: [])
    try:
        with caplog.at_level(logging.WARNING):
            result = analyzer.analyze_pipeline_run(
                "fixture",
                quality_result={
                    "violations": [
                        {"source_file": "fixture.md", "constraint": "rule", "followed": value}
                    ]
                },
            )
        expected = [value] if isinstance(value, bool) else []
        assert written == expected
        assert result["constraints_evaluated"] == len(expected)
        if not isinstance(value, bool):
            warning.assert_called_once()
        else:
            warning.assert_not_called()
    finally:
        analyzer.db.close()


def test_normal_and_layered_cache_contracts_do_not_collide(tmp_path):
    pusher = KnowledgePusher(knowledge_dir=tmp_path)
    normal = pusher.push("qa")
    layered = pusher.push_layered("qa", token_budget=4000)
    assert pusher.push("qa") is normal
    assert pusher.push_layered("qa", token_budget=4000) is layered
    assert isinstance(pusher.push("layered_qa_4000"), KnowledgePush)
    pusher.invalidate_cache("qa")
    assert pusher.push("qa") is not normal
    assert pusher.push_layered("qa", token_budget=4000) is not layered


@pytest.mark.parametrize("payload", [None, [], "invalid", 42])
def test_ui_contract_root_must_be_an_object(tmp_path: Path, payload) -> None:
    path = tmp_path / "output/example-ui-contract.json"
    path.parent.mkdir()
    text = json.dumps(payload)
    path.write_text(text, encoding="utf-8")
    builder = FrontendScaffoldBuilder(tmp_path, "example", "description")
    with pytest.raises(ValueError):
        builder._load_ui_contract()
    assert path.read_text(encoding="utf-8") == text


def test_valid_ui_contract_and_library_name_are_preserved(tmp_path, monkeypatch):
    path = tmp_path / "output/example-ui-contract.json"
    path.parent.mkdir()
    payload = {"color_palette": {"primary": "#112233"}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert FrontendScaffoldBuilder(tmp_path, "example", "desc")._load_ui_contract() == payload
    doc = DocumentGenerator("example", "desc")
    monkeypatch.setattr(
        doc, "_get_ui_intelligence", lambda: {"primary_library": {"name": "Chosen UI"}}
    )
    assert doc._get_ui_library() == "Chosen UI"
    monkeypatch.setattr(doc, "_get_ui_intelligence", lambda: {"primary_library": {"name": None}})
    with pytest.raises(ValueError):
        doc._get_ui_library()


@pytest.mark.parametrize("current", [None, SimpleNamespace()])
def test_missing_metrics_run_does_not_fabricate_results(tmp_path, monkeypatch, current):
    fake = MagicMock()
    fake.current_run = current
    monkeypatch.setattr(
        "super_dev.metrics.pipeline_metrics.PipelineMetricsCollector", lambda **_: fake
    )
    runner = LaunchRehearsalRunner(tmp_path, "fixture", "github")
    for name in dir(runner):
        if name.startswith("_check_") or name == "_estimate_capacity":
            monkeypatch.setattr(runner, name, lambda: RehearsalCheck("fixture", True, "fixture"))
    result = runner.run()
    if current is None:
        fake.finish_run.assert_not_called()
    else:
        assert current.quality_gate_score == result.score
        assert current.quality_gate_passed == result.passed
        fake.finish_run.assert_called_once()


@pytest.mark.parametrize(
    "addresses,passed", [([], False), ([(2, 1, 6, "", ("127.0.0.1", 0))], True)]
)
def test_dns_requires_an_address(tmp_path, monkeypatch, addresses, passed):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args: addresses)
    result = LaunchRehearsalRunner(tmp_path, "fixture", "github")._check_dns_reachability(
        "service.test"
    )
    assert result.passed is passed


@pytest.mark.parametrize(
    "expiry,passed",
    [(None, False), ((), False), ("invalid", False), ("Sep 06 09:00:00 2030 GMT", True)],
)
def test_ssl_expiry_input_is_validated(tmp_path, monkeypatch, expiry, passed):
    context = MagicMock()
    context.wrap_socket.return_value.__enter__.return_value.getpeercert.return_value = {
        "notAfter": expiry
    }
    monkeypatch.setattr("ssl.create_default_context", lambda: context)
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: MagicMock())
    result = LaunchRehearsalRunner(tmp_path, "fixture", "github")._check_ssl_certificate(
        "service.test"
    )
    assert result.passed is passed
