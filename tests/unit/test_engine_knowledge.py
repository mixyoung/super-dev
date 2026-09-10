import asyncio
from pathlib import Path

from super_dev.orchestrator.engine import WorkflowContext, WorkflowEngine


def test_phase_discovery_prefers_cached_knowledge_bundle(
    temp_project_dir: Path, config_manager, monkeypatch
):
    engine = WorkflowEngine(temp_project_dir)
    context = WorkflowContext(project_dir=temp_project_dir, config=config_manager)
    context.user_input = {
        "name": "demo",
        "description": "构建一个跨端商业级 UI 系统",
        "domain": "saas",
        "offline": True,
    }

    called = {"augment": 0, "save": 0, "load": 0}

    def fake_load_cached_bundle(self, *, output_dir, project_name, requirement, domain):
        called["load"] += 1
        return {
            "local_knowledge": [{"title": "cached"}],
            "web_knowledge": [],
            "enriched_requirement": "缓存增强需求",
        }

    def fake_augment(self, *, requirement, domain, max_local_results=8, max_web_results=5):
        called["augment"] += 1
        return {
            "local_knowledge": [],
            "web_knowledge": [],
            "enriched_requirement": requirement,
        }

    def fake_save_bundle(self, *, bundle, output_dir, project_name, requirement, domain):
        called["save"] += 1
        return output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"

    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.load_cached_bundle",
        fake_load_cached_bundle,
    )
    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.augment",
        fake_augment,
    )
    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.save_bundle",
        fake_save_bundle,
    )

    result = asyncio.run(engine._phase_discovery(context))

    assert result["status"] == "discovery_complete"
    assert called["load"] == 1
    assert called["augment"] == 0
    assert called["save"] == 0
    assert context.user_input["enriched_description"] == "缓存增强需求"
    assert context.user_input["knowledge_enhanced"] is True


def test_phase_discovery_saves_bundle_when_cache_miss(
    temp_project_dir: Path, config_manager, monkeypatch
):
    engine = WorkflowEngine(temp_project_dir)
    context = WorkflowContext(project_dir=temp_project_dir, config=config_manager)
    context.user_input = {
        "name": "demo",
        "description": "构建一个跨端商业级 UI 系统",
        "domain": "saas",
        "offline": False,
    }

    captured = {"max_local_results": 0, "max_web_results": 0, "save": 0}

    def fake_load_cached_bundle(self, *, output_dir, project_name, requirement, domain):
        return None

    def fake_augment(self, *, requirement, domain, max_local_results=8, max_web_results=5):
        captured["max_local_results"] = max_local_results
        captured["max_web_results"] = max_web_results
        return {
            "local_knowledge": [{"title": "local"}],
            "web_knowledge": [{"title": "web"}],
            "enriched_requirement": "联网增强需求",
        }

    def fake_save_bundle(self, *, bundle, output_dir, project_name, requirement, domain):
        captured["save"] += 1
        return output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"

    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.load_cached_bundle",
        fake_load_cached_bundle,
    )
    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.augment",
        fake_augment,
    )
    monkeypatch.setattr(
        "super_dev.orchestrator.knowledge.KnowledgeAugmenter.save_bundle",
        fake_save_bundle,
    )

    result = asyncio.run(engine._phase_discovery(context))

    assert result["status"] == "discovery_complete"
    assert captured["max_local_results"] == 12
    assert captured["max_web_results"] == 8
    assert captured["save"] == 1
    assert context.user_input["enriched_description"] == "联网增强需求"
    assert context.user_input["knowledge_enhanced"] is True
    assert context.user_input["web_research"] is True
