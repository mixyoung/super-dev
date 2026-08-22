"""Unit tests for Super Dev 2.3.0 new modules."""

from __future__ import annotations

import textwrap

# =====================================================================
# 1. test_skill_template
# =====================================================================


class TestSkillTemplate:
    """SkillFrontmatter creation and render for different hosts."""

    def test_frontmatter_defaults(self):
        from super_dev.skills.skill_template import SkillFrontmatter

        fm = SkillFrontmatter()
        assert fm.name == "super-dev"
        assert fm.user_invocable is True
        assert "Read" in fm.allowed_tools

    def test_render_claude_code(self):
        from super_dev.skills.skill_template import SkillFrontmatter

        fm = SkillFrontmatter(name="test-skill")
        lines = fm.to_yaml_lines("claude-code")
        text = "\n".join(lines)
        assert "when-to-use:" in text
        assert "user-invocable: true" in text
        assert "allowed-tools:" in text

    def test_render_codex_cli(self):
        from super_dev.skills.skill_template import SkillFrontmatter

        fm = SkillFrontmatter(name="test-skill")
        lines = fm.to_yaml_lines("codex-cli")
        text = "\n".join(lines)
        assert "metadata:" in text
        assert 'version: "2.4.0"' in text
        assert "when_to_use:" not in text
        # codex-cli should NOT have allowed-tools
        assert "allowed-tools:" not in text

    def test_render_generic(self):
        from super_dev.skills.skill_template import SkillFrontmatter

        fm = SkillFrontmatter(name="test-skill")
        lines = fm.to_yaml_lines("cursor")
        text = "\n".join(lines)
        assert "allowed_tools:" in text
        assert "user_invocable: true" in text

    def test_skill_template_render(self):
        from super_dev.skills.skill_template import SkillTemplate

        tpl = SkillTemplate.for_builtin("super-dev", "claude-code")
        output = tpl.render("claude-code")
        assert output.startswith("---")
        assert "super-dev" in output
        assert "PHASE_CHAIN" in output

    def test_skill_template_codex(self):
        from super_dev.skills.skill_template import SkillTemplate

        tpl = SkillTemplate.for_builtin("super-dev", "codex-cli")
        output = tpl.render("codex-cli")
        assert "Codex CLI" in output
        assert "## 沟通与环境适配（强制）" in output
        assert "## 分层编排与工作区所有权（强制）" in output

    def test_skill_template_generic(self):
        from super_dev.skills.skill_template import SkillTemplate

        tpl = SkillTemplate.for_builtin("super-dev", "cursor")
        output = tpl.render("cursor")
        assert "Super Dev" in output


# =====================================================================
# 2. test_prompt_sections
# =====================================================================


class TestPromptSections:
    """PromptBuilder register/resolve/cache."""

    def test_register_and_resolve(self):
        from super_dev.creators.prompt_sections import PromptBuilder, PromptSection

        builder = PromptBuilder()
        builder.register(PromptSection(name="a", content_fn=lambda **ctx: "hello", priority=10))
        builder.register(PromptSection(name="b", content_fn=lambda **ctx: "world", priority=20))
        result = builder.resolve()
        assert "hello" in result
        assert "world" in result
        # a should come before b
        assert result.index("hello") < result.index("world")

    def test_resolve_skips_empty(self):
        from super_dev.creators.prompt_sections import PromptBuilder, PromptSection

        builder = PromptBuilder()
        builder.register(PromptSection(name="empty", content_fn=lambda **ctx: "", priority=10))
        builder.register(PromptSection(name="valid", content_fn=lambda **ctx: "ok", priority=20))
        result = builder.resolve()
        assert result == "ok"

    def test_cache_behavior(self):
        from super_dev.creators.prompt_sections import PromptBuilder, PromptSection

        call_count = 0

        def counting_fn(**ctx):
            nonlocal call_count
            call_count += 1
            return "cached"

        builder = PromptBuilder()
        builder.register(PromptSection(name="c", content_fn=counting_fn, cacheable=True))
        builder.resolve()
        builder.resolve()
        assert call_count == 1  # cached on second call

    def test_non_cacheable(self):
        from super_dev.creators.prompt_sections import PromptBuilder, PromptSection

        call_count = 0

        def counting_fn(**ctx):
            nonlocal call_count
            call_count += 1
            return "fresh"

        builder = PromptBuilder()
        builder.register(PromptSection(name="nc", content_fn=counting_fn, cacheable=False))
        builder.resolve()
        builder.resolve()
        assert call_count == 2

    def test_get_section(self):
        from super_dev.creators.prompt_sections import PromptBuilder, PromptSection

        builder = PromptBuilder()
        builder.register(PromptSection(name="s1", content_fn=lambda **ctx: "val1"))
        assert builder.get_section("s1") == "val1"
        assert builder.get_section("missing") is None


# =====================================================================
# 3. test_context_compact
# =====================================================================


class TestContextCompact:
    """CompactSummary creation, save/load, render markdown, build_context."""

    def test_compact_summary_creation(self):
        from super_dev.orchestrator.context_compact import CompactSummary

        s = CompactSummary(phase="discovery", primary_request="Build a todo app")
        assert s.phase == "discovery"
        assert s.primary_request == "Build a todo app"
        assert s.timestamp

    def test_to_dict_from_dict(self):
        from super_dev.orchestrator.context_compact import CompactSummary

        s = CompactSummary(
            phase="drafting",
            key_concepts=["REST API", "PostgreSQL"],
            pending_tasks=["Implement auth"],
        )
        d = s.to_dict()
        s2 = CompactSummary.from_dict(d)
        assert s2.phase == "drafting"
        assert s2.key_concepts == ["REST API", "PostgreSQL"]
        assert s2.pending_tasks == ["Implement auth"]

    def test_save_and_load(self, tmp_path):
        from super_dev.orchestrator.context_compact import CompactEngine, CompactSummary

        engine = CompactEngine(tmp_path)
        s = CompactSummary(phase="discovery", primary_request="test")
        engine.save_compact(s)

        loaded = engine.load_compact("discovery")
        assert loaded is not None
        assert loaded.phase == "discovery"
        assert loaded.primary_request == "test"

    def test_render_markdown(self, tmp_path):
        from super_dev.orchestrator.context_compact import CompactEngine, CompactSummary

        engine = CompactEngine(tmp_path)
        s = CompactSummary(
            phase="qa",
            primary_request="Check quality",
            key_concepts=["unit tests"],
            next_step="Deploy",
        )
        md = engine.render_summary_markdown(s)
        assert "# Phase Compact: qa" in md
        assert "Check quality" in md
        assert "unit tests" in md
        assert "Deploy" in md

    def test_build_context(self, tmp_path):
        from super_dev.orchestrator.context_compact import CompactEngine, CompactSummary

        engine = CompactEngine(tmp_path)
        engine.save_compact(CompactSummary(phase="discovery", primary_request="Plan it"))
        engine.save_compact(CompactSummary(phase="intelligence", primary_request="Research it"))

        ctx = engine.build_context_for_phase("drafting", ["discovery", "intelligence"])
        assert "discovery" in ctx.lower()
        assert "Plan it" in ctx
        assert "Research it" in ctx

    def test_build_context_no_data(self, tmp_path):
        from super_dev.orchestrator.context_compact import CompactEngine

        engine = CompactEngine(tmp_path)
        ctx = engine.build_context_for_phase("drafting", ["discovery"])
        assert "No compact summaries" in ctx


# =====================================================================
# 4. test_memory_store
# =====================================================================


class TestMemoryStore:
    """MemoryEntry save/load/list/delete, update_index, find_duplicate."""

    def test_save_and_load(self, tmp_path):
        from super_dev.memory.store import MemoryEntry, MemoryStore

        store = MemoryStore(tmp_path / "memory")
        entry = MemoryEntry(
            name="Test Memory",
            description="A test",
            type="project",
            filename="test_mem.md",
            content="Hello world",
        )
        store.save(entry)
        loaded = store.load("test_mem.md")
        assert loaded is not None
        assert loaded.name == "Test Memory"
        assert loaded.content == "Hello world"

    def test_list_all(self, tmp_path):
        from super_dev.memory.store import MemoryEntry, MemoryStore

        store = MemoryStore(tmp_path / "memory")
        for i in range(3):
            store.save(
                MemoryEntry(
                    name=f"Mem {i}",
                    description=f"desc {i}",
                    type="project",
                    filename=f"mem_{i}.md",
                    content=f"content {i}",
                )
            )
        entries = store.list_all()
        assert len(entries) == 3

    def test_delete(self, tmp_path):
        from super_dev.memory.store import MemoryEntry, MemoryStore

        store = MemoryStore(tmp_path / "memory")
        store.save(
            MemoryEntry(
                name="To Delete",
                description="bye",
                type="feedback",
                filename="delete_me.md",
                content="gone",
            )
        )
        assert store.delete("delete_me.md") is True
        assert store.load("delete_me.md") is None
        assert store.delete("nonexistent.md") is False

    def test_update_index(self, tmp_path):
        from super_dev.memory.store import MemoryEntry, MemoryStore

        store = MemoryStore(tmp_path / "memory")
        store.save(
            MemoryEntry(
                name="Indexed",
                description="in index",
                type="user",
                filename="indexed.md",
                content="data",
            )
        )
        index_path = tmp_path / "memory" / "MEMORY.md"
        assert index_path.exists()
        text = index_path.read_text(encoding="utf-8")
        assert "Indexed" in text

    def test_find_duplicate(self, tmp_path):
        from super_dev.memory.store import MemoryEntry, MemoryStore

        store = MemoryStore(tmp_path / "memory")
        store.save(
            MemoryEntry(
                name="Dup",
                description="first",
                type="project",
                filename="dup1.md",
                content="content1",
            )
        )
        dup = store.find_duplicate("Dup", "project")
        assert dup is not None
        assert dup.filename == "dup1.md"
        assert store.find_duplicate("Dup", "feedback") is None
        assert store.find_duplicate("NoExist", "project") is None


# =====================================================================
# 5. test_memory_extractor
# =====================================================================


class TestMemoryExtractor:
    """extract_from_phase for different phases, should_extract."""

    def test_should_extract_discovery(self, tmp_path):
        from super_dev.memory.extractor import MemoryExtractor
        from super_dev.memory.store import MemoryStore

        store = MemoryStore(tmp_path / "memory")
        extractor = MemoryExtractor(store)
        context = {"user_input": {"description": "Build app", "tech_stack": "react"}}
        assert extractor.should_extract("discovery", context) is True

    def test_should_not_extract_unknown_phase(self, tmp_path):
        from super_dev.memory.extractor import MemoryExtractor
        from super_dev.memory.store import MemoryStore

        store = MemoryStore(tmp_path / "memory")
        extractor = MemoryExtractor(store)
        assert extractor.should_extract("unknown_phase", {"user_input": {"x": "y"}}) is False

    def test_should_not_extract_empty_context(self, tmp_path):
        from super_dev.memory.extractor import MemoryExtractor
        from super_dev.memory.store import MemoryStore

        store = MemoryStore(tmp_path / "memory")
        extractor = MemoryExtractor(store)
        assert extractor.should_extract("discovery", {}) is False

    def test_extract_from_discovery(self, tmp_path):
        from super_dev.memory.extractor import MemoryExtractor
        from super_dev.memory.store import MemoryStore

        store = MemoryStore(tmp_path / "memory")
        extractor = MemoryExtractor(store)
        context = {
            "user_input": {"description": "Build a todo app"},
            "metadata": {"tech_stack": {"frontend": "react", "backend": "node"}},
        }
        entries = extractor.extract_from_phase("discovery", context)
        assert len(entries) >= 1
        names = [e.name for e in entries]
        assert any("Tech Stack" in n or "Requirements" in n for n in names)

    def test_extract_from_intelligence(self, tmp_path):
        from super_dev.memory.extractor import MemoryExtractor
        from super_dev.memory.store import MemoryStore

        store = MemoryStore(tmp_path / "memory")
        extractor = MemoryExtractor(store)
        context = {
            "research_data": {
                "competitors": [
                    {"name": "Todoist", "url": "https://todoist.com"},
                ],
            },
        }
        entries = extractor.extract_from_phase("intelligence", context)
        assert len(entries) >= 1


# =====================================================================
# 6. test_memory_consolidator
# =====================================================================


class TestMemoryConsolidator:
    """should_consolidate, increment_session_count, consolidate."""

    def test_should_consolidate_initially_false(self, tmp_path):
        from super_dev.memory.consolidator import MemoryConsolidator

        mc = MemoryConsolidator(tmp_path / "memory")
        # No sessions yet, min_sessions=5 by default
        assert mc.should_consolidate() is False

    def test_increment_session_count(self, tmp_path):
        from super_dev.memory.consolidator import MemoryConsolidator

        mc = MemoryConsolidator(tmp_path / "memory")
        mc.increment_session_count()
        mc.increment_session_count()
        state = mc._load_state()
        assert state["sessions_since_consolidation"] == 2

    def test_should_consolidate_after_enough_sessions(self, tmp_path):
        from super_dev.memory.consolidator import ConsolidationConfig, MemoryConsolidator

        config = ConsolidationConfig(min_hours=0, min_sessions=2)
        mc = MemoryConsolidator(tmp_path / "memory", config=config)
        mc.increment_session_count()
        mc.increment_session_count()
        assert mc.should_consolidate() is True

    def test_consolidate_empty(self, tmp_path):
        from super_dev.memory.consolidator import ConsolidationConfig, MemoryConsolidator

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)
        config = ConsolidationConfig(min_hours=0, min_sessions=0)
        mc = MemoryConsolidator(mem_dir, config=config)
        result = mc.consolidate()
        assert result.errors == []
        assert result.phase == "prune"

    def test_consolidate_deduplicates(self, tmp_path):
        from super_dev.memory.consolidator import ConsolidationConfig, MemoryConsolidator
        from super_dev.memory.store import MemoryEntry, MemoryStore

        mem_dir = tmp_path / "memory"
        store = MemoryStore(mem_dir)
        store.save(
            MemoryEntry(
                name="Dup Item",
                description="first",
                type="project",
                filename="dup_a.md",
                content="old",
                updated_at="2026-01-01T00:00:00",
            )
        )
        store.save(
            MemoryEntry(
                name="Dup Item",
                description="second",
                type="project",
                filename="dup_b.md",
                content="new",
                updated_at="2026-03-01T00:00:00",
            )
        )

        config = ConsolidationConfig(min_hours=0, min_sessions=0)
        mc = MemoryConsolidator(mem_dir, config=config)
        result = mc.consolidate()
        assert result.files_deleted >= 1 or result.contradictions_resolved >= 1


# =====================================================================
# 7. test_expert_loader
# =====================================================================


class TestExpertLoader:
    """parse_frontmatter, parse_expert_from_markdown, load_expert_definitions."""

    def test_parse_frontmatter_basic(self):
        from super_dev.experts.loader import parse_frontmatter

        text = textwrap.dedent(
            """\
            ---
            name: PM
            role: PM
            title: Product Manager
            goal: Deliver great products
            ---
            # Body content
            Some text here.
        """
        )
        fm, body = parse_frontmatter(text)
        assert fm["name"] == "PM"
        assert fm["role"] == "PM"
        assert fm["goal"] == "Deliver great products"
        assert "Body content" in body

    def test_parse_frontmatter_no_frontmatter(self):
        from super_dev.experts.loader import parse_frontmatter

        text = "Just plain text"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_parse_frontmatter_with_list(self):
        from super_dev.experts.loader import parse_frontmatter

        text = textwrap.dedent(
            """\
            ---
            name: ARCH
            focus_areas:
            - system design
            - api contracts
            ---
            Body
        """
        )
        fm, body = parse_frontmatter(text)
        assert isinstance(fm["focus_areas"], list)
        assert "system design" in fm["focus_areas"]

    def test_parse_expert_from_markdown(self, tmp_path):
        from super_dev.experts.loader import parse_expert_from_markdown

        md_file = tmp_path / "pm.md"
        md_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: PM
                role: PM
                title: Product Manager
                description: Requirements analysis
                goal: Convert fuzzy needs into clear specs
                ---
                # Backstory
                Expert PM with 10 years experience.
            """
            ),
            encoding="utf-8",
        )
        defn = parse_expert_from_markdown(md_file, source="project")
        assert defn is not None
        assert defn.name == "PM"
        assert defn.source == "project"
        assert defn.goal == "Convert fuzzy needs into clear specs"

    def test_parse_expert_missing_goal(self, tmp_path):
        from super_dev.experts.loader import parse_expert_from_markdown

        md_file = tmp_path / "bad.md"
        md_file.write_text(
            textwrap.dedent(
                """\
                ---
                name: BAD
                role: BAD
                ---
                No goal field.
            """
            ),
            encoding="utf-8",
        )
        defn = parse_expert_from_markdown(md_file)
        assert defn is None

    def test_load_expert_definitions_project_dir(self, tmp_path):
        from super_dev.experts.loader import load_expert_definitions

        experts_dir = tmp_path / ".super-dev" / "experts"
        experts_dir.mkdir(parents=True)
        (experts_dir / "custom.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: CUSTOM
                role: CODE
                title: Custom Expert
                description: Custom role
                goal: Do custom things
                ---
                Custom body.
            """
            ),
            encoding="utf-8",
        )
        defs = load_expert_definitions(project_dir=tmp_path)
        assert "CUSTOM" in defs
        assert defs["CUSTOM"].source == "project"


# =====================================================================
# 8. test_behavioral_prompts
# =====================================================================


class TestBehavioralPrompts:
    """ALL_BEHAVIORAL_PROMPTS contains 6 entries, each is non-empty string."""

    def test_all_behavioral_prompts_count(self):
        from super_dev.experts.behavioral_prompts import ALL_BEHAVIORAL_PROMPTS

        assert len(ALL_BEHAVIORAL_PROMPTS) == 6

    def test_all_entries_non_empty(self):
        from super_dev.experts.behavioral_prompts import ALL_BEHAVIORAL_PROMPTS

        for key, value in ALL_BEHAVIORAL_PROMPTS.items():
            assert value, f"Behavioral prompt '{key}' is empty"
            if isinstance(value, str):
                assert len(value) > 10, f"Behavioral prompt '{key}' is too short"
            elif isinstance(value, dict):
                assert len(value) > 0, f"Behavioral prompt dict '{key}' is empty"

    def test_individual_constants(self):
        from super_dev.experts.behavioral_prompts import (
            ADVERSARIAL_MINDSET,
            CODE_STYLE_DONTS,
            FALSE_CLAIMS_DEFENSE,
            NUMERIC_ANCHORS,
            STRUCTURED_OUTPUT_FORMAT,
            SYNTHESIS_RULES,
        )

        assert "Don't" in CODE_STYLE_DONTS or "Don't" in CODE_STYLE_DONTS
        assert "NEVER" in FALSE_CLAIMS_DEFENSE
        assert isinstance(NUMERIC_ANCHORS, dict)
        assert "code" in NUMERIC_ANCHORS
        assert "Synthesis" in SYNTHESIS_RULES
        assert "Adversarial" in ADVERSARIAL_MINDSET
        assert "MUST" in STRUCTURED_OUTPUT_FORMAT


# =====================================================================
# 9. test_hooks
# =====================================================================


class TestHooks:
    """HookConfig.from_dict, HookManager.execute with log hook, has_blocking_result."""

    def test_hook_config_from_dict_none(self):
        from super_dev.hooks.models import HookConfig

        config = HookConfig.from_dict(None)
        assert config.hooks == {}

    def test_hook_config_from_dict(self):
        from super_dev.hooks.models import HookConfig

        data = {
            "PostPhase": [
                {"matcher": "*", "type": "log", "description": "Phase done"},
            ],
        }
        config = HookConfig.from_dict(data)
        defs = config.get_definitions("PostPhase")
        assert len(defs) == 1
        assert defs[0].description == "Phase done"

    def test_hook_manager_execute_log(self, tmp_path):
        from super_dev.hooks.manager import HookManager
        from super_dev.hooks.models import HookConfig

        config = HookConfig.from_dict(
            {
                "PostPhase": [
                    {"matcher": "*", "type": "log", "description": "Logged event"},
                ],
            }
        )
        manager = HookManager(config=config, project_dir=tmp_path)
        results = manager.execute("PostPhase", phase="drafting")
        assert len(results) == 1
        assert results[0].success is True
        assert "Logged event" in results[0].output

    def test_has_blocking_result(self):
        from super_dev.hooks.manager import HookManager
        from super_dev.hooks.models import HookConfig, HookResult

        manager = HookManager(config=HookConfig())
        non_blocking = [
            HookResult(hook_name="a", event="e", success=True, blocked=False),
        ]
        assert manager.has_blocking_result(non_blocking) is False

        blocking = [
            HookResult(hook_name="b", event="e", success=False, blocked=True),
        ]
        assert manager.has_blocking_result(blocking) is True

    def test_hook_manager_callback(self, tmp_path):
        from super_dev.hooks.manager import HookEvent, HookManager
        from super_dev.hooks.models import HookConfig

        manager = HookManager(config=HookConfig(), project_dir=tmp_path)

        def my_callback(ctx):
            return "callback_ran"

        manager.register_callback(HookEvent.SESSION_START, my_callback)
        results = manager.execute(HookEvent.SESSION_START)
        assert len(results) == 1
        assert results[0].success is True

    def test_hook_matcher_filtering(self, tmp_path):
        from super_dev.hooks.manager import HookManager
        from super_dev.hooks.models import HookConfig

        config = HookConfig.from_dict(
            {
                "PrePhase": [
                    {"matcher": "drafting", "type": "log", "description": "Only drafting"},
                ],
            }
        )
        manager = HookManager(config=config, project_dir=tmp_path)
        # Should match drafting
        results = manager.execute("PrePhase", phase="drafting")
        assert len(results) == 1
        # Should not match discovery
        results = manager.execute("PrePhase", phase="discovery")
        assert len(results) == 0


# =====================================================================
# 10. test_review_agents
# =====================================================================


class TestReviewAgents:
    """build_parallel_review_prompt returns 4 agents, aggregate_findings."""

    def test_build_parallel_review_prompt_returns_4(self):
        from super_dev.reviewers.review_agents import build_parallel_review_prompt

        prompts = build_parallel_review_prompt(
            change_description="Add user auth",
            files_changed=["auth.py", "routes.py"],
        )
        assert isinstance(prompts, dict)
        assert len(prompts) == 4
        assert set(prompts.keys()) == {"reuse", "quality", "efficiency", "security"}
        for key, prompt in prompts.items():
            assert len(prompt) > 50, f"Prompt for {key} is too short"

    def test_build_prompt_includes_context(self):
        from super_dev.reviewers.review_agents import build_parallel_review_prompt

        prompts = build_parallel_review_prompt(
            change_description="Fix login bug",
            files_changed=["login.py"],
            diff_content="- old_code\n+ new_code",
        )
        assert "Fix login bug" in prompts["reuse"]
        assert "login.py" in prompts["quality"]

    def test_aggregate_findings_empty(self):
        from super_dev.reviewers.review_agents import aggregate_findings

        report = aggregate_findings({})
        assert len(report.findings) == 0
        assert report.critical_count == 0
        assert report.pass_quality_gate() is True

    def test_aggregate_findings_with_data(self):
        from super_dev.reviewers.review_agents import (
            ReviewFinding,
            aggregate_findings,
        )

        findings = {
            "reuse": [
                ReviewFinding(
                    agent="reuse",
                    category="duplication",
                    severity="medium",
                    description="Duplicated helper",
                ),
            ],
            "security": [
                ReviewFinding(
                    agent="security",
                    category="injection",
                    severity="critical",
                    description="SQL injection found",
                ),
            ],
        }
        report = aggregate_findings(findings)
        assert len(report.findings) == 2
        assert report.critical_count == 1
        assert report.high_count == 0
        assert report.pass_quality_gate() is False  # 1 critical > 0 max

    def test_review_report_actionable(self):
        from super_dev.reviewers.review_agents import ReviewFinding, ReviewReport

        report = ReviewReport(
            findings=[
                ReviewFinding(
                    agent="quality",
                    category="style",
                    severity="low",
                    description="Minor style issue",
                    is_false_positive=True,
                ),
                ReviewFinding(
                    agent="quality",
                    category="bug",
                    severity="high",
                    description="Real bug",
                ),
            ]
        )
        assert len(report.actionable_findings) == 1

    def test_adversarial_prompt_exists(self):
        from super_dev.reviewers.review_agents import ADVERSARIAL_VERIFICATION_PROMPT

        assert "VERDICT" in ADVERSARIAL_VERIFICATION_PROMPT
        assert len(ADVERSARIAL_VERIFICATION_PROMPT) > 100


# =====================================================================
# 11. test_session_brief
# =====================================================================


class TestSessionBrief:
    """generate_template, save/load, update_section, summarize_for_context."""

    def test_generate_template(self):
        from super_dev.session.brief import SECTION_NAMES, SessionBrief

        template = SessionBrief.generate_template("MyProject")
        assert "# SESSION BRIEF" in template
        assert "MyProject" in template
        for name in SECTION_NAMES:
            assert f"## {name}" in template

    def test_save_and_load(self, tmp_path):
        from super_dev.session.brief import SessionBrief

        sections = {
            "Session Title": "Test Session",
            "Current State": "In progress",
            "Task Specification": "Build feature X",
        }
        SessionBrief.save(tmp_path, sections)
        loaded = SessionBrief.load(tmp_path)
        assert loaded["Session Title"] == "Test Session"
        assert loaded["Current State"] == "In progress"

    def test_update_section(self, tmp_path):
        from super_dev.session.brief import SessionBrief

        SessionBrief.save(tmp_path, {"Session Title": "Original"})
        SessionBrief.update_section(tmp_path, "Current State", "Updated state")
        loaded = SessionBrief.load(tmp_path)
        assert loaded["Current State"] == "Updated state"
        assert loaded["Session Title"] == "Original"

    def test_summarize_for_context(self, tmp_path):
        from super_dev.session.brief import SessionBrief

        sections = {
            "Session Title": "My Project",
            "Current State": "Implementing frontend",
            "Key Results": "3 pages completed",
        }
        SessionBrief.save(tmp_path, sections)
        summary = SessionBrief.summarize_for_context(tmp_path)
        assert "My Project" in summary
        assert "Implementing frontend" in summary
        assert "3 pages completed" in summary

    def test_summarize_for_context_empty(self, tmp_path):
        from super_dev.session.brief import SessionBrief

        summary = SessionBrief.summarize_for_context(tmp_path)
        assert summary == ""

    def test_load_nonexistent(self, tmp_path):
        from super_dev.session.brief import SessionBrief

        loaded = SessionBrief.load(tmp_path)
        assert loaded == {}
