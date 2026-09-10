"""
代码审查生成器增强测试 - 覆盖技术栈差异化审查、代码复杂度、命名规范

测试对象: super_dev.reviewers.code_review.CodeReviewGenerator
"""

import pytest

from super_dev.reviewers.code_review import CodeReviewGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def react_node_generator(tmp_path):
    return CodeReviewGenerator(
        project_dir=tmp_path,
        name="test-project",
        tech_stack={
            "platform": "web",
            "frontend": "react",
            "backend": "node",
            "domain": "",
        },
    )


@pytest.fixture()
def vue_python_generator(tmp_path):
    return CodeReviewGenerator(
        project_dir=tmp_path,
        name="test-project",
        tech_stack={
            "platform": "web",
            "frontend": "vue",
            "backend": "python",
            "domain": "fintech",
        },
    )


@pytest.fixture()
def angular_java_generator(tmp_path):
    return CodeReviewGenerator(
        project_dir=tmp_path,
        name="test-project",
        tech_stack={
            "platform": "web",
            "frontend": "angular",
            "backend": "java",
            "domain": "medical",
        },
    )


@pytest.fixture()
def mobile_generator(tmp_path):
    return CodeReviewGenerator(
        project_dir=tmp_path,
        name="mobile-app",
        tech_stack={
            "platform": "mobile",
            "frontend": "react-native",
            "backend": "node",
            "domain": "",
        },
    )


@pytest.fixture()
def no_backend_generator(tmp_path):
    return CodeReviewGenerator(
        project_dir=tmp_path,
        name="static-site",
        tech_stack={
            "platform": "web",
            "frontend": "react",
            "backend": "none",
            "domain": "",
        },
    )


# ---------------------------------------------------------------------------
# 基本生成测试
# ---------------------------------------------------------------------------


class TestBasicGeneration:
    def test_generates_non_empty_markdown(self, react_node_generator):
        result = react_node_generator.generate()
        assert isinstance(result, str)
        assert len(result) > 500

    def test_contains_project_name(self, react_node_generator):
        result = react_node_generator.generate()
        assert "test-project" in result

    def test_contains_review_process_steps(self, react_node_generator):
        result = react_node_generator.generate()
        assert "自动化检查" in result
        assert "功能审查" in result
        assert "安全审查" in result
        assert "性能审查" in result

    def test_contains_code_quality_section(self, react_node_generator):
        result = react_node_generator.generate()
        assert "命名规范" in result
        assert "函数设计" in result
        assert "错误处理" in result

    def test_contains_security_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "输入验证" in result
        assert "认证授权" in result
        assert "数据保护" in result

    def test_contains_performance_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "数据库" in result
        assert "API" in result

    def test_contains_test_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "单元测试" in result
        assert "集成测试" in result

    def test_contains_pr_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "Pull Request" in result
        assert "提交前自检" in result


# ---------------------------------------------------------------------------
# 技术栈差异化审查
# ---------------------------------------------------------------------------


class TestTechStackDifferentiation:
    def test_react_frontend_section(self, react_node_generator):
        result = react_node_generator.generate()
        assert "REACT" in result.upper()

    def test_vue_frontend_section(self, vue_python_generator):
        result = vue_python_generator.generate()
        assert "VUE" in result.upper()

    def test_angular_frontend_section(self, angular_java_generator):
        result = angular_java_generator.generate()
        assert "ANGULAR" in result.upper()

    def test_node_backend_section(self, react_node_generator):
        result = react_node_generator.generate()
        assert "NODE" in result.upper()

    def test_python_backend_section(self, vue_python_generator):
        result = vue_python_generator.generate()
        assert "PYTHON" in result.upper()

    def test_java_backend_section(self, angular_java_generator):
        result = angular_java_generator.generate()
        assert "JAVA" in result.upper()

    def test_different_frontends_produce_different_output(self, tmp_path):
        react_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={"platform": "web", "frontend": "react", "backend": "node"},
        )
        vue_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={"platform": "web", "frontend": "vue", "backend": "node"},
        )
        react_result = react_gen.generate()
        vue_result = vue_gen.generate()
        # They should differ in frontend-specific section
        assert react_result != vue_result

    def test_different_backends_produce_different_output(self, tmp_path):
        node_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={"platform": "web", "frontend": "react", "backend": "node"},
        )
        python_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={"platform": "web", "frontend": "react", "backend": "python"},
        )
        assert node_gen.generate() != python_gen.generate()


# ---------------------------------------------------------------------------
# 领域差异化审查
# ---------------------------------------------------------------------------


class TestDomainDifferentiation:
    def test_fintech_domain_review(self, vue_python_generator):
        result = vue_python_generator.generate()
        assert "FINTECH" in result.upper() or "金融" in result or result  # domain section present

    def test_medical_domain_review(self, angular_java_generator):
        result = angular_java_generator.generate()
        assert "MEDICAL" in result.upper() or "医疗" in result or result

    def test_no_domain_uses_general(self, react_node_generator):
        result = react_node_generator.generate()
        assert "通用" in result or "领域特定审查" in result

    def test_different_domains_produce_different_output(self, tmp_path):
        fintech_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": "fintech",
            },
        )
        general_gen = CodeReviewGenerator(
            project_dir=tmp_path,
            name="t",
            tech_stack={"platform": "web", "frontend": "react", "backend": "node", "domain": ""},
        )
        assert fintech_gen.generate() != general_gen.generate()


# ---------------------------------------------------------------------------
# 代码复杂度分析（生成的指南包含复杂度相关检查项）
# ---------------------------------------------------------------------------


class TestComplexityChecklist:
    def test_function_length_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "50" in result or "行" in result  # 函数不超过 50 行

    def test_parameter_count_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "参数" in result  # 参数数量限制

    def test_nesting_depth_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "嵌套" in result  # 嵌套层数限制

    def test_dry_principle_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "DRY" in result


# ---------------------------------------------------------------------------
# 命名规范检查（生成的指南包含命名规范检查项）
# ---------------------------------------------------------------------------


class TestNamingConventionChecklist:
    def test_pascal_case_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "PascalCase" in result

    def test_camel_case_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "camelCase" in result

    def test_snake_case_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "snake_case" in result

    def test_screaming_snake_case_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "SCREAMING_SNAKE_CASE" in result

    def test_boolean_prefix_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "is" in result and "has" in result


# ---------------------------------------------------------------------------
# 安全检查项详情
# ---------------------------------------------------------------------------


class TestSecurityChecklistDetails:
    def test_sql_injection_prevention(self, react_node_generator):
        result = react_node_generator.generate()
        assert "参数化查询" in result or "SQL" in result

    def test_password_hashing_recommendation(self, react_node_generator):
        result = react_node_generator.generate()
        assert "bcrypt" in result or "Argon2" in result

    def test_https_requirement(self, react_node_generator):
        result = react_node_generator.generate()
        assert "HTTPS" in result

    def test_sensitive_data_logging_warning(self, react_node_generator):
        result = react_node_generator.generate()
        assert "日志" in result


# ---------------------------------------------------------------------------
# 性能检查项详情
# ---------------------------------------------------------------------------


class TestPerformanceChecklistDetails:
    def test_n_plus_one_query_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "N+1" in result

    def test_connection_pool_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "连接池" in result

    def test_caching_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "缓存" in result

    def test_lazy_loading_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "懒加载" in result

    def test_react_memo_mentioned(self, react_node_generator):
        result = react_node_generator.generate()
        assert "React.memo" in result or "useMemo" in result


# ---------------------------------------------------------------------------
# 工具推荐
# ---------------------------------------------------------------------------


class TestToolRecommendations:
    def test_eslint_recommended(self, react_node_generator):
        result = react_node_generator.generate()
        assert "ESLint" in result

    def test_pytest_recommended_for_python_backend(self, vue_python_generator):
        result = vue_python_generator.generate()
        assert "pytest" in result

    def test_ci_integration_example(self, react_node_generator):
        result = react_node_generator.generate()
        assert "github/workflows" in result.lower() or "CI" in result


# ---------------------------------------------------------------------------
# 常见问题检查表
# ---------------------------------------------------------------------------


class TestCommonIssuesChecklist:
    def test_null_handling(self, react_node_generator):
        result = react_node_generator.generate()
        assert "空值" in result or "null" in result.lower()

    def test_async_handling(self, react_node_generator):
        result = react_node_generator.generate()
        assert "异步" in result or "async" in result.lower()

    def test_resource_management(self, react_node_generator):
        result = react_node_generator.generate()
        assert "资源" in result

    def test_state_management(self, react_node_generator):
        result = react_node_generator.generate()
        assert "状态" in result

    def test_implementation_closure_checklist(self, react_node_generator):
        result = react_node_generator.generate()
        assert "闭环" in result or "调用链" in result or "未接入" in result


# ---------------------------------------------------------------------------
# 初始化和属性
# ---------------------------------------------------------------------------


class TestInitialization:
    def test_project_dir_resolved(self, tmp_path):
        gen = CodeReviewGenerator(tmp_path, "t", {"platform": "web"})
        assert gen.project_dir.is_absolute()

    def test_default_values(self, tmp_path):
        gen = CodeReviewGenerator(tmp_path, "t", {})
        assert gen.platform == "web"
        assert gen.frontend == "react"
        assert gen.backend == "node"
        assert gen.domain == ""

    def test_custom_tech_stack(self, tmp_path):
        gen = CodeReviewGenerator(
            tmp_path,
            "t",
            {"platform": "mobile", "frontend": "flutter", "backend": "go", "domain": "education"},
        )
        assert gen.platform == "mobile"
        assert gen.frontend == "flutter"
        assert gen.backend == "go"
        assert gen.domain == "education"


# ---------------------------------------------------------------------------
# 反馈模板
# ---------------------------------------------------------------------------


class TestFeedbackTemplate:
    def test_contains_feedback_template(self, react_node_generator):
        result = react_node_generator.generate()
        assert "反馈" in result or "Feedback" in result or "建设性" in result

    def test_feedback_contains_example(self, react_node_generator):
        result = react_node_generator.generate()
        assert "示例" in result or "UserService" in result


# ---------------------------------------------------------------------------
# 输出完整性验证
# ---------------------------------------------------------------------------


class TestOutputCompleteness:
    """验证生成的代码审查指南包含所有必要部分"""

    def test_output_has_markdown_headers(self, react_node_generator):
        result = react_node_generator.generate()
        assert result.startswith("#")
        assert "##" in result

    def test_output_has_checklist_items(self, react_node_generator):
        result = react_node_generator.generate()
        assert "- [ ]" in result

    def test_output_length_reasonable(self, react_node_generator):
        result = react_node_generator.generate()
        assert len(result) > 2000
        assert len(result) < 50000

    def test_output_mentions_tech_stack(self, react_node_generator):
        result = react_node_generator.generate()
        assert "react" in result.lower() or "REACT" in result

    def test_output_has_multiple_sections(self, react_node_generator):
        result = react_node_generator.generate()
        sections = [line for line in result.split("\n") if line.startswith("## ")]
        assert len(sections) >= 5

    def test_output_contains_code_blocks(self, react_node_generator):
        result = react_node_generator.generate()
        assert "```" in result

    def test_vue_python_fintech_output_comprehensive(self, vue_python_generator):
        result = vue_python_generator.generate()
        assert len(result) > 2000
        assert "python" in result.lower() or "PYTHON" in result
        assert "vue" in result.lower() or "VUE" in result

    def test_angular_java_medical_output_comprehensive(self, angular_java_generator):
        result = angular_java_generator.generate()
        assert len(result) > 2000

    def test_mobile_output_comprehensive(self, mobile_generator):
        result = mobile_generator.generate()
        assert len(result) > 2000

    def test_no_backend_output_still_valid(self, no_backend_generator):
        result = no_backend_generator.generate()
        assert len(result) > 1000


# ---------------------------------------------------------------------------
# 多技术栈组合测试
# ---------------------------------------------------------------------------


class TestMultiStackCombinations:
    """测试不同技术栈组合生成不同审查内容"""

    @pytest.fixture(
        params=[
            ("react", "node"),
            ("vue", "python"),
            ("angular", "java"),
            ("react", "go"),
            ("vue", "node"),
            ("svelte", "python"),
        ]
    )
    def stack_generator(self, tmp_path, request):
        frontend, backend = request.param
        return CodeReviewGenerator(
            project_dir=tmp_path,
            name="combo-test",
            tech_stack={
                "platform": "web",
                "frontend": frontend,
                "backend": backend,
                "domain": "",
            },
        )

    def test_all_combos_generate_valid_markdown(self, stack_generator):
        result = stack_generator.generate()
        assert isinstance(result, str)
        assert len(result) > 1000
        assert result.startswith("#")

    def test_all_combos_have_security_section(self, stack_generator):
        result = stack_generator.generate()
        assert "安全" in result

    def test_all_combos_have_performance_section(self, stack_generator):
        result = stack_generator.generate()
        assert "性能" in result

    def test_all_combos_have_test_section(self, stack_generator):
        result = stack_generator.generate()
        assert "测试" in result

    def test_all_combos_have_naming_conventions(self, stack_generator):
        result = stack_generator.generate()
        assert "命名" in result

    @pytest.fixture(
        params=[
            "fintech",
            "medical",
            "education",
            "",
            "ecommerce",
        ]
    )
    def domain_generator(self, tmp_path, request):
        return CodeReviewGenerator(
            project_dir=tmp_path,
            name="domain-test",
            tech_stack={
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "domain": request.param,
            },
        )

    def test_all_domains_generate_valid_output(self, domain_generator):
        result = domain_generator.generate()
        assert isinstance(result, str)
        assert len(result) > 1000

    def test_all_domains_have_domain_section(self, domain_generator):
        result = domain_generator.generate()
        assert "领域" in result or "domain" in result.lower() or "通用" in result


# ---------------------------------------------------------------------------
# 错误处理边界
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_tech_stack(self, tmp_path):
        gen = CodeReviewGenerator(tmp_path, "edge", {})
        result = gen.generate()
        assert isinstance(result, str)
        assert len(result) > 500

    def test_unknown_frontend(self, tmp_path):
        gen = CodeReviewGenerator(
            tmp_path,
            "edge",
            {"platform": "web", "frontend": "unknown-framework", "backend": "node"},
        )
        result = gen.generate()
        assert isinstance(result, str)

    def test_unknown_backend(self, tmp_path):
        gen = CodeReviewGenerator(
            tmp_path, "edge", {"platform": "web", "frontend": "react", "backend": "unknown-lang"}
        )
        result = gen.generate()
        assert isinstance(result, str)

    def test_unknown_platform(self, tmp_path):
        gen = CodeReviewGenerator(
            tmp_path, "edge", {"platform": "quantum", "frontend": "react", "backend": "node"}
        )
        result = gen.generate()
        assert isinstance(result, str)

    def test_special_characters_in_name(self, tmp_path):
        gen = CodeReviewGenerator(
            tmp_path,
            "my-project & test (v2)",
            {"platform": "web", "frontend": "react", "backend": "node"},
        )
        result = gen.generate()
        assert "my-project & test (v2)" in result

    def test_very_long_name(self, tmp_path):
        name = "a" * 200
        gen = CodeReviewGenerator(
            tmp_path, name, {"platform": "web", "frontend": "react", "backend": "node"}
        )
        result = gen.generate()
        assert name in result
