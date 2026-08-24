"""
Super Dev 测试配置
"""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from super_dev.config import ConfigManager, ProjectConfig
from super_dev.orchestrator import WorkflowContext, WorkflowEngine
from super_dev.user_directories import UserDirectoryContext
from tests.support.user_surface_snapshot import (
    capture_user_surfaces,
    collect_user_surface_paths,
    diff_surface_snapshots,
    has_surface_changes,
    unsafe_surface_states,
)


@pytest.fixture(scope="session", autouse=True)
def protect_real_user_surfaces(request: pytest.FixtureRequest):
    """整次测试会话前后比较真实用户级接入面。"""

    project_dir = Path(str(request.config.rootpath)).resolve()
    real_directories = UserDirectoryContext.current()
    protected_paths = collect_user_surface_paths(project_dir, real_directories)
    before = capture_user_surfaces(protected_paths)
    risks = unsafe_surface_states(before)
    assert not risks, f"真实用户级接入面包含无法安全检查的连接点或路径: {risks}"
    yield
    after = capture_user_surfaces(protected_paths)
    diff = diff_surface_snapshots(before, after)
    assert not has_surface_changes(diff), f"真实用户级接入面发生变化: {diff}"


@pytest.fixture(autouse=True)
def isolated_user_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> UserDirectoryContext:
    """让每个测试默认运行在独立用户目录，避免接触真实宿主文件。"""

    home = tmp_path / "isolated-user-home"
    home.mkdir(parents=True, exist_ok=True)
    context = UserDirectoryContext.from_home(home)
    for name, value in context.environment({}).items():
        monkeypatch.setenv(name, value)
    assert Path.home().resolve() == context.home
    assert Path("~").expanduser().resolve() == context.home
    yield context


@pytest.fixture(autouse=True)
def reset_global_config_manager():
    """重置全局配置管理器（每个测试前）"""
    from super_dev.config import manager
    manager._global_config_managers.clear()
    yield
    manager._global_config_managers.clear()


@pytest.fixture(autouse=True)
def allow_pipeline_without_host_in_tests(monkeypatch):
    """测试默认关闭宿主硬门禁，避免依赖本机宿主安装状态。"""
    monkeypatch.setenv("SUPER_DEV_ALLOW_NO_HOST", "1")


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """临时项目目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config(temp_project_dir: Path) -> ProjectConfig:
    """示例配置"""
    return ProjectConfig(
        name="test-project",
        description="Test project",
        platform="web",
        frontend="react",
        backend="node",
        domain="ecommerce"
    )


@pytest.fixture
def config_manager(temp_project_dir: Path, sample_config: ProjectConfig) -> ConfigManager:
    """配置管理器"""
    manager = ConfigManager(temp_project_dir)
    manager._config = sample_config
    return manager


@pytest.fixture
def workflow_engine(temp_project_dir: Path) -> WorkflowEngine:
    """工作流引擎"""
    return WorkflowEngine(temp_project_dir)


@pytest.fixture
def workflow_context(temp_project_dir: Path, config_manager: ConfigManager) -> WorkflowContext:
    """工作流上下文"""
    return WorkflowContext(
        project_dir=temp_project_dir,
        config=config_manager
    )
