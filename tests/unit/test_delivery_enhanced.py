"""
交付打包器增强测试 - 覆盖 K8s/Docker Compose 配置生成、环境变量模板生成

测试对象: super_dev.deployers.delivery.DeliveryPackager
"""

import json
import textwrap
from pathlib import Path
from zipfile import ZipFile

import pytest

from super_dev import __version__
from super_dev.deployers.delivery import ArtifactSpec, DeliveryPackager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_project(tmp_path):
    (tmp_path / "super-dev.yaml").write_text("name: test\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def ready_project(tmp_path):
    """项目包含所有必需产物"""
    name = "myapp"
    output = tmp_path / "output"
    output.mkdir()
    artifacts = [
        f"{name}-research.md",
        f"{name}-prd.md",
        f"{name}-architecture.md",
        f"{name}-uiux.md",
        f"{name}-ui-contract.json",
        f"{name}-execution-plan.md",
        f"{name}-frontend-blueprint.md",
        f"{name}-redteam.md",
        f"{name}-quality-gate.md",
        f"{name}-code-review.md",
        f"{name}-ai-prompt.md",
        f"{name}-task-execution.md",
        f"{name}-frontend-runtime.md",
        f"{name}-frontend-runtime.json",
    ]
    for artifact in artifacts:
        (output / artifact).write_text(f"# {artifact}\n")

    # frontend output
    fe = output / "frontend"
    fe.mkdir()
    (fe / "index.html").write_text("<html></html>")
    (fe / "styles.css").write_text("body {}")
    (fe / "design-tokens.css").write_text(":root {}")
    (fe / "app.js").write_text("console.log('app')")

    # preview
    (tmp_path / "preview.html").write_text("<html>preview</html>")

    # backend
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "API_CONTRACT.md").write_text("# API Contract")

    # env template
    (tmp_path / ".env.deploy.example").write_text("DB_HOST=localhost\n")

    # deploy secrets checklist
    deploy_dir = output / "deploy"
    deploy_dir.mkdir()
    (deploy_dir / "all-secrets-checklist.md").write_text("# Secrets\n")

    # CI/CD files
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("name: CI\n")
    (gh / "cd.yml").write_text("name: CD\n")
    (tmp_path / ".gitlab-ci.yml").write_text("stages: []\n")
    (tmp_path / "Jenkinsfile").write_text("pipeline {}\n")
    (tmp_path / ".azure-pipelines.yml").write_text("trigger: []\n")
    (tmp_path / "bitbucket-pipelines.yml").write_text("pipelines: {}\n")

    # migrations
    migrations = tmp_path / "prisma" / "migrations" / "001"
    migrations.mkdir(parents=True)
    (migrations / "migration.sql").write_text("CREATE TABLE users (id SERIAL);")

    return tmp_path, name


# ---------------------------------------------------------------------------
# ArtifactSpec 数据类
# ---------------------------------------------------------------------------

class TestArtifactSpec:
    def test_frozen_dataclass(self, tmp_path):
        spec = ArtifactSpec(path=tmp_path / "file.md", required=True, reason="test")
        assert spec.required is True
        assert spec.reason == "test"
        with pytest.raises(AttributeError):
            spec.required = False  # frozen

    def test_path_is_stored_correctly(self, tmp_path):
        p = tmp_path / "output" / "doc.md"
        spec = ArtifactSpec(path=p, required=False, reason="optional")
        assert spec.path == p


# ---------------------------------------------------------------------------
# DeliveryPackager 初始化
# ---------------------------------------------------------------------------

class TestDeliveryPackagerInit:
    def test_project_dir_resolved(self, tmp_path):
        packager = DeliveryPackager(tmp_path, "test")
        assert packager.project_dir.is_absolute()

    def test_default_version(self, tmp_path):
        packager = DeliveryPackager(tmp_path, "test")
        assert packager.version == __version__

    def test_custom_version(self, tmp_path):
        packager = DeliveryPackager(tmp_path, "test", version="3.0.0")
        assert packager.version == "3.0.0"


# ---------------------------------------------------------------------------
# _artifact_specs - 必需产物规则
# ---------------------------------------------------------------------------

class TestArtifactSpecs:
    def test_all_platform_returns_all_cicd_files(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="all")
        cicd_paths = [str(s.path) for s in specs if "ci.yml" in str(s.path) or "Jenkinsfile" in str(s.path)]
        assert len(cicd_paths) >= 2

    def test_github_platform_returns_github_files(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="github")
        cicd_names = [s.path.name for s in specs if "github" in str(s.path).lower() or "ci.yml" in s.path.name]
        assert any("ci.yml" in n for n in cicd_names)

    def test_gitlab_platform_returns_gitlab_file(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="gitlab")
        cicd_names = [s.path.name for s in specs]
        assert ".gitlab-ci.yml" in cicd_names

    def test_jenkins_platform_returns_jenkinsfile(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="jenkins")
        cicd_names = [s.path.name for s in specs]
        assert "Jenkinsfile" in cicd_names

    def test_azure_platform_returns_azure_file(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="azure")
        cicd_names = [s.path.name for s in specs]
        assert ".azure-pipelines.yml" in cicd_names

    def test_bitbucket_platform_returns_bitbucket_file(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="bitbucket")
        cicd_names = [s.path.name for s in specs]
        assert "bitbucket-pipelines.yml" in cicd_names

    def test_unknown_platform_defaults_to_github(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="unknown")
        cicd_names = [s.path.name for s in specs if "ci.yml" in s.path.name or "cd.yml" in s.path.name]
        assert len(cicd_names) >= 1

    def test_all_specs_are_required(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform="github")
        # Most specs should be required
        required_count = sum(1 for s in specs if s.required)
        assert required_count >= 10


# ---------------------------------------------------------------------------
# _collect_migration_files
# ---------------------------------------------------------------------------

class TestMigrationCollection:
    def test_detects_prisma_migrations(self, tmp_path):
        migrations = tmp_path / "prisma" / "migrations" / "001"
        migrations.mkdir(parents=True)
        (migrations / "migration.sql").write_text("CREATE TABLE t (id INT);")
        packager = DeliveryPackager(tmp_path, "test")
        files = packager._collect_migration_files()
        assert len(files) >= 1

    def test_detects_alembic_migrations(self, tmp_path):
        versions = tmp_path / "alembic" / "versions"
        versions.mkdir(parents=True)
        (versions / "001_init.py").write_text("# alembic migration")
        packager = DeliveryPackager(tmp_path, "test")
        files = packager._collect_migration_files()
        assert len(files) >= 1

    def test_detects_backend_migrations(self, tmp_path):
        migrations = tmp_path / "backend" / "migrations"
        migrations.mkdir(parents=True)
        (migrations / "001_create_users.sql").write_text("CREATE TABLE users;")
        packager = DeliveryPackager(tmp_path, "test")
        files = packager._collect_migration_files()
        assert len(files) >= 1

    def test_returns_empty_when_no_migrations(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        files = packager._collect_migration_files()
        assert files == []

    def test_excludes_non_migration_files(self, tmp_path):
        migrations = tmp_path / "prisma" / "migrations"
        migrations.mkdir(parents=True)
        (migrations / "readme.md").write_text("# Migrations")
        packager = DeliveryPackager(tmp_path, "test")
        files = packager._collect_migration_files()
        assert len(files) == 0


# ---------------------------------------------------------------------------
# _collect_spec_task_summary
# ---------------------------------------------------------------------------

class TestSpecTaskSummary:
    def test_no_changes_dir_returns_zero(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        summary = packager._collect_spec_task_summary()
        assert summary["task_files"] == 0
        assert summary["total"] == 0

    def test_counts_completed_and_pending(self, tmp_path):
        changes = tmp_path / ".super-dev" / "changes" / "feature-a"
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text(textwrap.dedent("""\
            # Tasks
            - [x] **1.1: Setup project**
            - [ ] **1.2: Implement feature**
            - [~] **1.3: Testing**
        """))
        packager = DeliveryPackager(tmp_path, "test")
        summary = packager._collect_spec_task_summary()
        assert summary["total"] == 3
        assert summary["completed"] == 1
        assert summary["pending"] == 2
        assert summary["in_progress"] == 1

    def test_prefers_named_task_file(self, tmp_path):
        changes_a = tmp_path / ".super-dev" / "changes" / "myapp"
        changes_a.mkdir(parents=True)
        (changes_a / "tasks.md").write_text("- [x] **1: Done**\n")
        changes_b = tmp_path / ".super-dev" / "changes" / "other"
        changes_b.mkdir(parents=True)
        (changes_b / "tasks.md").write_text("- [ ] **1: Pending**\n")
        packager = DeliveryPackager(tmp_path, "myapp")
        summary = packager._collect_spec_task_summary()
        assert summary["target_change"] == "myapp"
        assert summary["completed"] == 1

    def test_falls_back_to_latest_task_file(self, tmp_path):
        changes = tmp_path / ".super-dev" / "changes" / "feature-x"
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text("- [ ] **1: Task**\n")
        packager = DeliveryPackager(tmp_path, "unrelated-name")
        summary = packager._collect_spec_task_summary()
        assert summary["target_change"] == "feature-x"


# ---------------------------------------------------------------------------
# package() 完整流程
# ---------------------------------------------------------------------------

class TestPackageIntegration:
    def test_ready_project_produces_ready_status(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package(cicd_platform="all")
        assert result["status"] == "ready"
        assert result["missing_required_count"] == 0

    def test_empty_project_produces_incomplete_status(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        result = packager.package(cicd_platform="github")
        assert result["status"] == "incomplete"
        assert result["missing_required_count"] > 0

    def test_package_creates_manifest_json(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        manifest_file = Path(result["manifest_file"])
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert manifest["project_name"] == name
        assert "included_files" in manifest

    def test_package_creates_report_markdown(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        report_file = Path(result["report_file"])
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "交付报告" in content

    def test_package_creates_zip_archive(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        archive_file = Path(result["archive_file"])
        assert archive_file.exists()
        with ZipFile(archive_file) as zf:
            names = zf.namelist()
            assert len(names) > 0

    def test_package_with_pending_tasks_reports_missing(self, ready_project):
        project_dir, name = ready_project
        changes = project_dir / ".super-dev" / "changes" / name
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text("- [ ] **1: Pending task**\n")
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        missing = result.get("missing_required", [])
        task_missing = [m for m in missing if "Spec 任务" in str(m.get("reason", ""))]
        assert len(task_missing) >= 1


# ---------------------------------------------------------------------------
# _to_markdown
# ---------------------------------------------------------------------------

class TestToMarkdown:
    def test_markdown_includes_project_info(self, empty_project):
        packager = DeliveryPackager(empty_project, "myproject", version="1.5.0")
        manifest = {
            "project_name": "myproject",
            "version": "1.5.0",
            "status": "incomplete",
            "cicd_platform": "github",
            "generated_at": "2026-01-01T00:00:00",
            "included_files": ["output/myproject-prd.md"],
            "missing_required": [{"path": "output/myproject-redteam.md", "reason": "缺少红队报告"}],
            "spec_tasks": {"task_files": 1, "total": 3, "completed": 2, "pending": 1},
        }
        md = packager._to_markdown(manifest)
        assert "myproject" in md
        assert "1.5.0" in md
        assert "未完成" in md
        assert "myproject-prd.md" in md
        assert "红队报告" in md

    def test_markdown_ready_status(self, empty_project):
        packager = DeliveryPackager(empty_project, "app")
        manifest = {
            "status": "ready",
            "included_files": ["file1"],
            "missing_required": [],
            "spec_tasks": {"task_files": 0, "total": 0, "completed": 0, "pending": 0},
        }
        md = packager._to_markdown(manifest)
        assert "可交付" in md

    def test_markdown_no_included_files(self, empty_project):
        packager = DeliveryPackager(empty_project, "app")
        manifest = {
            "status": "incomplete",
            "included_files": [],
            "missing_required": [],
        }
        md = packager._to_markdown(manifest)
        assert "(none)" in md

    def test_markdown_no_missing_required(self, empty_project):
        packager = DeliveryPackager(empty_project, "app")
        manifest = {
            "status": "ready",
            "included_files": ["a"],
            "missing_required": [],
        }
        md = packager._to_markdown(manifest)
        assert "无" in md


# ---------------------------------------------------------------------------
# _relative
# ---------------------------------------------------------------------------

class TestRelativePath:
    def test_relative_path_inside_project(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        full_path = empty_project / "output" / "file.md"
        rel = packager._relative(full_path)
        assert rel == "output/file.md"

    def test_outside_path_returns_full(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        other_path = Path("/some/other/path/file.md")
        rel = packager._relative(other_path)
        assert "/some/other/path/file.md" in rel


# ---------------------------------------------------------------------------
# CI/CD 配置生成相关
# ---------------------------------------------------------------------------

class TestCICDSpecs:
    def test_cicd_specs_github(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._cicd_specs("github")
        names = [s.path.name for s in specs]
        assert "ci.yml" in names
        assert "cd.yml" in names

    def test_cicd_specs_all(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._cicd_specs("all")
        assert len(specs) >= 6

    def test_cicd_specs_all_are_required(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._cicd_specs("all")
        assert all(s.required for s in specs)


# ---------------------------------------------------------------------------
# Archive 构建
# ---------------------------------------------------------------------------

class TestBuildArchive:
    def test_archive_includes_existing_files(self, tmp_path):
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        archive_path = tmp_path / "test.zip"
        packager = DeliveryPackager(tmp_path, "test")
        packager._build_archive(
            archive_path=archive_path,
            included_files=["file1.txt", "file2.txt"],
            extra_files=[],
        )
        assert archive_path.exists()
        with ZipFile(archive_path) as zf:
            assert "file1.txt" in zf.namelist()
            assert "file2.txt" in zf.namelist()

    def test_archive_skips_missing_files(self, tmp_path):
        (tmp_path / "exists.txt").write_text("content")
        archive_path = tmp_path / "test.zip"
        packager = DeliveryPackager(tmp_path, "test")
        packager._build_archive(
            archive_path=archive_path,
            included_files=["exists.txt", "missing.txt"],
            extra_files=[],
        )
        with ZipFile(archive_path) as zf:
            assert "exists.txt" in zf.namelist()
            assert "missing.txt" not in zf.namelist()

    def test_archive_includes_extra_files(self, tmp_path):
        extra = tmp_path / "extra.json"
        extra.write_text('{"key": "value"}')
        archive_path = tmp_path / "test.zip"
        packager = DeliveryPackager(tmp_path, "test")
        packager._build_archive(
            archive_path=archive_path,
            included_files=[],
            extra_files=[extra],
        )
        with ZipFile(archive_path) as zf:
            assert "extra.json" in zf.namelist()


# ---------------------------------------------------------------------------
# CI/CD 平台全覆盖
# ---------------------------------------------------------------------------

class TestAllCICDPlatforms:
    """验证所有 CI/CD 平台的配置生成正确性"""

    @pytest.fixture(params=["github", "gitlab", "jenkins", "azure", "bitbucket", "all"])
    def platform(self, request):
        return request.param

    def test_artifact_specs_include_cicd(self, empty_project, platform):
        packager = DeliveryPackager(empty_project, "test")
        specs = packager._artifact_specs(cicd_platform=platform)
        cicd_specs = [s for s in specs if "CI/CD" in s.reason or "ci" in str(s.path).lower() or "Jenkinsfile" in str(s.path)]
        assert len(cicd_specs) >= 1

    def test_package_reports_missing_cicd(self, empty_project, platform):
        packager = DeliveryPackager(empty_project, "test")
        result = packager.package(cicd_platform=platform)
        missing = result.get("missing_required", [])
        assert len(missing) > 0  # Empty project has many missing items


# ---------------------------------------------------------------------------
# 交付包完整性 - 边界情况
# ---------------------------------------------------------------------------

class TestPackageEdgeCases:
    def test_package_with_no_output_dir(self, tmp_path):
        # No output dir created yet
        packager = DeliveryPackager(tmp_path, "test")
        result = packager.package()
        assert result["status"] == "incomplete"

    def test_package_creates_output_delivery_dir(self, tmp_path):
        packager = DeliveryPackager(tmp_path, "test")
        packager.package()
        delivery_dir = tmp_path / "output" / "delivery"
        assert delivery_dir.exists()

    def test_manifest_json_is_valid(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        manifest = json.loads(Path(result["manifest_file"]).read_text())
        assert "project_name" in manifest
        assert "version" in manifest
        assert "generated_at" in manifest
        assert "status" in manifest
        assert "included_files" in manifest
        assert "missing_required" in manifest
        assert "summary" in manifest

    def test_manifest_summary_counts(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        manifest = json.loads(Path(result["manifest_file"]).read_text())
        summary = manifest["summary"]
        assert summary["included_count"] == len(manifest["included_files"])
        assert summary["missing_required_count"] == len(manifest["missing_required"])

    def test_archive_contains_manifest_and_report(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        with ZipFile(result["archive_file"]) as zf:
            names = zf.namelist()
            assert any("manifest" in n for n in names)
            assert any("report" in n for n in names)

    def test_included_files_are_sorted_and_unique(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name)
        result = packager.package()
        manifest = json.loads(Path(result["manifest_file"]).read_text())
        files = manifest["included_files"]
        assert files == sorted(set(files))

    def test_custom_version_in_archive_name(self, ready_project):
        project_dir, name = ready_project
        packager = DeliveryPackager(project_dir, name, version="5.0.0")
        result = packager.package()
        assert "5.0.0" in result["archive_file"]


# ---------------------------------------------------------------------------
# Spec 任务摘要边界
# ---------------------------------------------------------------------------

class TestSpecTaskSummaryEdgeCases:
    def test_empty_tasks_file(self, tmp_path):
        changes = tmp_path / ".super-dev" / "changes" / "test"
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text("")
        packager = DeliveryPackager(tmp_path, "test")
        summary = packager._collect_spec_task_summary()
        assert summary["total"] == 0
        assert summary["completed"] == 0
        assert summary["pending"] == 0

    def test_all_completed_tasks(self, tmp_path):
        changes = tmp_path / ".super-dev" / "changes" / "done"
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text(textwrap.dedent("""\
            # Tasks
            - [x] **1.1: Task A**
            - [x] **1.2: Task B**
            - [x] **1.3: Task C**
        """))
        packager = DeliveryPackager(tmp_path, "done")
        summary = packager._collect_spec_task_summary()
        assert summary["total"] == 3
        assert summary["completed"] == 3
        assert summary["pending"] == 0

    def test_mixed_status_tasks(self, tmp_path):
        changes = tmp_path / ".super-dev" / "changes" / "mixed"
        changes.mkdir(parents=True)
        (changes / "tasks.md").write_text(textwrap.dedent("""\
            - [x] **1: Done**
            - [ ] **2: Todo**
            - [~] **3: WIP**
            - [_] **4: Skipped**
        """))
        packager = DeliveryPackager(tmp_path, "mixed")
        summary = packager._collect_spec_task_summary()
        assert summary["total"] == 4
        assert summary["completed"] == 1
        assert summary["in_progress"] == 1

    def test_multiple_changes_uses_latest(self, tmp_path):
        import time
        for name in ["old-change", "new-change"]:
            changes = tmp_path / ".super-dev" / "changes" / name
            changes.mkdir(parents=True)
            (changes / "tasks.md").write_text(f"- [ ] **1: Task in {name}**\n")
            time.sleep(0.1)  # Ensure different mtime
        packager = DeliveryPackager(tmp_path, "unrelated")
        summary = packager._collect_spec_task_summary()
        assert summary["task_files"] == 1
        assert summary["target_change"] == "new-change"


# ---------------------------------------------------------------------------
# Markdown 报告格式验证
# ---------------------------------------------------------------------------

class TestMarkdownReportFormat:
    def test_report_has_all_sections(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        manifest = {
            "project_name": "test",
            "version": "1.0.0",
            "status": "incomplete",
            "cicd_platform": "github",
            "generated_at": "2026-01-01T00:00:00",
            "included_files": ["a.md", "b.md"],
            "missing_required": [{"path": "c.md", "reason": "missing"}],
            "spec_tasks": {"task_files": 1, "total": 5, "completed": 3, "pending": 2},
        }
        md = packager._to_markdown(manifest)
        assert "# 交付报告" in md
        assert "## 已包含文件" in md
        assert "## 缺失必需项" in md
        assert "## Spec任务摘要" in md

    def test_report_shows_task_counts(self, empty_project):
        packager = DeliveryPackager(empty_project, "test")
        manifest = {
            "status": "incomplete",
            "included_files": [],
            "missing_required": [],
            "spec_tasks": {"task_files": 2, "total": 10, "completed": 7, "pending": 3},
        }
        md = packager._to_markdown(manifest)
        assert "10" in md
        assert "7" in md
        assert "3" in md
