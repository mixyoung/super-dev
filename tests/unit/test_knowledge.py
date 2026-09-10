"""
知识增强器测试
"""

from pathlib import Path

from super_dev.orchestrator.knowledge import KnowledgeAugmenter, KnowledgeItem


class TestKnowledgeAugmenter:
    def test_augment_with_local_knowledge(self, temp_project_dir: Path):
        docs_dir = temp_project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "auth.md").write_text(
            "# 认证设计\n\n登录功能必须支持 token 刷新与权限控制。",
            encoding="utf-8",
        )

        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment("实现登录认证流程", domain="auth")

        assert bundle["original_requirement"] == "实现登录认证流程"
        assert "generated_at" in bundle
        assert "citations" in bundle
        assert "metadata" in bundle
        assert "web_stats" in bundle["metadata"]
        assert len(bundle["local_knowledge"]) >= 1
        assert "请结合以下上下文实现" in bundle["enriched_requirement"]
        assert len(bundle["citations"]["local"]) >= 1

    def test_augment_scans_project_knowledge_directory(self, temp_project_dir: Path):
        knowledge_dir = temp_project_dir / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "payment.md").write_text(
            "# 支付风控知识\n\n支付链路必须支持设备指纹、限流策略和二次验证。",
            encoding="utf-8",
        )

        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment("实现支付风控与限流", domain="payment")

        local_items = bundle.get("local_knowledge", [])
        assert len(local_items) >= 1
        assert any(item["source"] == "knowledge/payment.md" for item in local_items)
        assert "支付风控知识" in bundle["enriched_requirement"]
        application_plan = bundle.get("knowledge_application_plan", {})
        assert "stage_guidance" in application_plan
        assert "prd" in application_plan["stage_guidance"]
        assert any("payment.md" in item for item in application_plan["stage_guidance"]["prd"])

    def test_augment_emits_framework_guidance_for_uniapp(self, temp_project_dir: Path):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment(
            "构建 uni-app 商城，覆盖微信小程序、H5 与 App 登录支付分享流程", domain="commerce"
        )

        framework_guidance = bundle.get("knowledge_application_plan", {}).get(
            "framework_guidance", {}
        )
        assert framework_guidance["framework"] == "uni-app"
        assert any(
            "provider" in item or "登录/支付/分享" in item
            for item in framework_guidance["critical_modules"]
        )
        assert any("微信小程序" in item for item in framework_guidance["validation_surfaces"])

    def test_augment_prioritizes_knowledge_over_docs_when_scores_equal(
        self, temp_project_dir: Path
    ):
        docs_dir = temp_project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "policy.md").write_text(
            "支付链路必须支持限流策略和二次验证。",
            encoding="utf-8",
        )
        knowledge_dir = temp_project_dir / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "policy.md").write_text(
            "支付链路必须支持限流策略和二次验证。",
            encoding="utf-8",
        )

        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment("实现支付限流与二次验证", domain="payment")
        local_items = bundle.get("local_knowledge", [])

        assert len(local_items) >= 2
        assert local_items[0]["source"] == "knowledge/policy.md"

    def test_augment_scans_knowledge_yaml_and_txt(self, temp_project_dir: Path):
        knowledge_dir = temp_project_dir / "knowledge" / "security"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "baseline.yaml").write_text(
            "title: 安全基线\ncontent: 密码策略应至少包含复杂度、过期与历史限制。",
            encoding="utf-8",
        )
        (knowledge_dir / "ops.txt").write_text(
            "安全运营建议：关键操作必须保留审计日志，支持追溯。",
            encoding="utf-8",
        )

        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment("实现审计日志与密码策略", domain="security")
        sources = {item["source"] for item in bundle.get("local_knowledge", [])}

        assert "knowledge/security/baseline.yaml" in sources
        assert "knowledge/security/ops.txt" in sources
        hard_constraints = bundle.get("knowledge_application_plan", {}).get("hard_constraints", [])
        assert any("baseline.yaml" in item for item in hard_constraints)

    def test_render_markdown(self, temp_project_dir: Path):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = {
            "original_requirement": "构建管理后台",
            "domain": "general",
            "keywords": ["管理", "后台"],
            "local_knowledge": [],
            "web_knowledge": [],
            "knowledge_application_plan": {
                "hard_constraints": ["安全基线必须进入质量门禁"],
                "stage_guidance": {
                    "research": ["先研究同类管理后台的信息架构"],
                    "prd": ["把权限与审计列为核心需求"],
                },
                "framework_guidance": {
                    "framework": "Desktop Web Shell",
                    "critical_modules": ["窗口布局、快捷键、托盘、本地文件与 IPC 边界先冻结"],
                    "validation_surfaces": ["窗口恢复、快捷键、文件系统与离线恢复"],
                    "delivery_evidence": ["窗口/快捷键/原生桥接清单"],
                },
            },
            "research_summary": {
                "benchmark_products": ["Product A: benchmark"],
                "feature_patterns": ["Pattern A"],
                "interaction_patterns": ["Interaction A"],
                "trust_signals": ["Trust A"],
                "differentiation_opportunities": ["Differentiation A"],
                "delivery_recommendations": ["Delivery A"],
                "evidence_distribution": {"official": 2, "industry": 1, "community": 0},
                "research_confidence": "high",
                "implementation_options": [
                    {
                        "name": "稳健商业方案",
                        "fit": "企业级交付",
                        "strategy": "质量门禁",
                        "tradeoff": "前期成本",
                    }
                ],
                "primary_sources": [("openai.com", 2)],
                "competitor_matrix": [
                    {
                        "product": "Product A",
                        "capability": "工作台/协作",
                        "pricing_signal": "已提及",
                        "trust_signal": "较强",
                        "evidence_level": "official",
                    }
                ],
            },
            "enriched_requirement": "构建管理后台。",
        }
        markdown = augmenter.to_markdown(bundle)
        assert "# 需求增强报告" in markdown
        assert "## 提取关键词" in markdown
        assert "## 本地知识应用计划" in markdown
        assert "### Research / 同类产品研究" in markdown
        assert "### 跨平台框架专项指引" in markdown
        assert "## 同类产品研究与机会洞察" in markdown
        assert "### 1. 对标产品" in markdown
        assert "### 7. 研究证据与可信度" in markdown
        assert "### 8. 实施策略对比" in markdown
        assert "### 9. 核心来源域名" in markdown
        assert "### 10. 竞品能力矩阵（自动提取）" in markdown

    def test_web_fallback_when_ddgs_unavailable(self, temp_project_dir: Path, monkeypatch):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=True)

        monkeypatch.setattr(
            augmenter,
            "_collect_web_items_ddgs",
            lambda query, max_results: [],
        )
        monkeypatch.setattr(
            augmenter,
            "_collect_web_items_duckduckgo",
            lambda query, max_results: [
                KnowledgeItem(
                    source="web",
                    title="Fallback Result",
                    snippet="DuckDuckGo fallback snippet",
                    link="https://example.com",
                    score=1.0,
                )
            ],
        )

        bundle = augmenter.augment("实现登录认证流程", domain="auth")

        assert len(bundle["web_knowledge"]) == 1
        assert "Fallback Result" in bundle["enriched_requirement"]

    def test_web_prefers_ddgs_result(self, temp_project_dir: Path, monkeypatch):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=True)
        fallback_called = {"value": False}

        monkeypatch.setattr(
            augmenter,
            "_collect_web_items_ddgs",
            lambda query, max_results: [
                KnowledgeItem(
                    source="web",
                    title="DDGS Result",
                    snippet="Primary web snippet",
                    score=2.0,
                )
            ],
        )

        def _fallback(query: str, max_results: int) -> list[KnowledgeItem]:
            fallback_called["value"] = True
            return []

        monkeypatch.setattr(augmenter, "_collect_web_items_duckduckgo", _fallback)

        bundle = augmenter.augment("实现登录认证流程", domain="auth")

        assert len(bundle["web_knowledge"]) == 1
        assert bundle["web_knowledge"][0]["title"] == "DDGS Result"
        assert "evidence_level" in bundle["web_knowledge"][0]
        assert fallback_called["value"] is False

    def test_save_bundle_cache_file(self, temp_project_dir: Path):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        bundle = augmenter.augment("实现登录认证流程", domain="auth")
        output_dir = temp_project_dir / "output"
        cache_file = augmenter.save_bundle(
            bundle=bundle,
            output_dir=output_dir,
            project_name="demo",
            requirement="实现登录认证流程",
            domain="auth",
        )
        assert cache_file.exists()
        content = cache_file.read_text(encoding="utf-8")
        assert '"original_requirement": "实现登录认证流程"' in content
        assert '"cache_signature"' in content

    def test_load_cached_bundle_hit(self, temp_project_dir: Path):
        augmenter = KnowledgeAugmenter(
            project_dir=temp_project_dir, web_enabled=False, cache_ttl_seconds=1800
        )
        bundle = augmenter.augment("实现登录认证流程", domain="auth")
        output_dir = temp_project_dir / "output"
        augmenter.save_bundle(
            bundle=bundle,
            output_dir=output_dir,
            project_name="demo",
            requirement="实现登录认证流程",
            domain="auth",
        )

        cached = augmenter.load_cached_bundle(
            output_dir=output_dir,
            project_name="demo",
            requirement="实现登录认证流程",
            domain="auth",
        )
        assert cached is not None
        assert cached.get("original_requirement") == "实现登录认证流程"

    def test_web_items_filtered_by_allowed_domains(self, temp_project_dir: Path, monkeypatch):
        augmenter = KnowledgeAugmenter(
            project_dir=temp_project_dir,
            web_enabled=True,
            allowed_web_domains=["openai.com"],
        )

        monkeypatch.setattr(
            augmenter,
            "_collect_web_items_ddgs",
            lambda query, max_results: [
                KnowledgeItem(
                    source="web",
                    title="OpenAI API",
                    snippet="official docs",
                    link="https://platform.openai.com/docs/overview",
                    score=3.0,
                ),
                KnowledgeItem(
                    source="web",
                    title="Random Blog",
                    snippet="community post",
                    link="https://example.org/blog",
                    score=2.0,
                ),
            ],
        )
        monkeypatch.setattr(
            augmenter,
            "_collect_web_items_duckduckgo",
            lambda query, max_results: [],
        )

        bundle = augmenter.augment("如何实现 agent orchestration", domain="ai")
        web_items = bundle.get("web_knowledge", [])
        web_stats = (bundle.get("metadata") or {}).get("web_stats", {})

        assert len(web_items) == 1
        assert web_items[0]["title"] == "OpenAI API"
        assert web_stats.get("filtered_out_count") == 1

    def test_extract_keywords_handles_mixed_ai_chinese_tokens(self, temp_project_dir: Path):
        augmenter = KnowledgeAugmenter(project_dir=temp_project_dir, web_enabled=False)
        keywords = augmenter._extract_keywords("AI应用上线前要检查哪些风险和门禁")
        assert "ai" in keywords
        assert any(token in keywords for token in ["应用", "风险", "门禁"])
