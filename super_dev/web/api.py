#!/usr/bin/env python3
"""
开发：Excellent（11964948@qq.com）
功能：Super Dev Web API - FastAPI 后端
作用：提供 REST API 服务，支持项目管理和工作流执行
创建时间：2025-12-30
最后修改：2025-12-30
"""

import asyncio
import json
import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any, Literal, cast
from urllib.parse import urlencode

import uvicorn
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from super_dev import __description__, __version__
from super_dev.baseline_governance import inspect_baseline_governance
from super_dev.catalogs import (
    BACKEND_TEMPLATE_CATALOG,
    CICD_PLATFORM_CATALOG,
    CICD_PLATFORM_IDS,
    DOMAIN_CATALOG,
    HOST_TOOL_CATALOG,
    LANGUAGE_PREFERENCE_CATALOG,
    PIPELINE_FRONTEND_TEMPLATE_CATALOG,
    PLATFORM_CATALOG,
)
from super_dev.config import ConfigManager
from super_dev.experts import (
    list_experts as list_expert_catalog,
)
from super_dev.host_runtime_probe import build_host_runtime_probe
from super_dev.host_workflow_context import build_host_workflow_context
from super_dev.integrations.manager import IntegrationManager
from super_dev.orchestrator import Phase, WorkflowContext, WorkflowEngine
from super_dev.policy import PipelinePolicy, PipelinePolicyManager
from super_dev.proof_pack import ProofPackBuilder
from super_dev.release_readiness import ReleaseReadinessEvaluator
from super_dev.review_state import (
    architecture_revision_file,
    baseline_confirmation_file,
    docs_confirmation_file,
    load_architecture_revision,
    load_baseline_confirmation,
    load_docs_confirmation,
    load_preview_confirmation,
    load_quality_revision,
    load_ui_revision,
    preview_confirmation_file,
    quality_revision_file,
    save_architecture_revision,
    save_baseline_confirmation,
    save_quality_revision,
    save_ui_revision,
    ui_revision_file,
)
from super_dev.runtime_evidence import normalize_competition_evidence
from super_dev.ui_contract_governance import missing_claude_design_runtime_checks
from super_dev.web.rate_limit import RateLimitMiddleware
from super_dev.workflow_guard import (
    WorkflowGateError,
    preview_gate_status,
    require_docs_confirmation,
    require_preview_confirmation,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)
from super_dev.workflow_stage_truth import resolve_engine_phase_names

from .api_host_support import (
    _build_detected_host_decision_card,
    _build_host_compatibility_summary,
    _build_host_runtime_validation_payload,
    _build_host_tool_catalog_payload,
    _build_primary_repair_action,
    _build_runtime_evidence_record,
    _build_session_resume_card,
    _collect_host_diagnostics,
    _detect_host_targets,
    _detect_pipeline_summary,
    _explain_detection_details,
    _host_runtime_status_label,
    _public_host_targets,
    _repair_host_diagnostics,
    _serialize_host_usage_profile,
    _update_host_runtime_validation_state,
    _validate_project_dir,
)

try:
    import fcntl as _fcntl
except ImportError:
    fcntl: ModuleType | None = None
else:
    fcntl = _fcntl

_api_logger = logging.getLogger("super_dev.web.api")

# ==================== 路径安全 ====================


def _validate_run_id(run_id: str) -> str:
    """验证 run_id，防止路径遍历和注入攻击。

    run_id 只允许字母数字、连字符和下划线。
    """
    if not run_id or not re.match(r"^[a-zA-Z0-9_-]+$", run_id):
        raise HTTPException(
            status_code=400,
            detail="run_id 只允许包含字母、数字、连字符和下划线",
        )
    return run_id


# ==================== 数据模型 ====================


class ProjectInitRequest(BaseModel):
    """项目初始化请求"""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    platform: str = "web"
    frontend: str = "react"
    backend: str = "node"
    domain: str = ""
    language_preferences: list[str] = []
    quality_gate: int = Field(80, ge=0, le=100)
    host_compatibility_min_score: int = Field(80, ge=0, le=100)
    host_compatibility_min_ready_hosts: int = Field(1, ge=0, le=50)
    host_profile_targets: list[str] = []
    host_profile_enforce_selected: bool = False


class ProjectConfigResponse(BaseModel):
    """项目配置响应"""

    name: str
    description: str
    version: str
    platform: str
    frontend: str
    backend: str
    domain: str
    language_preferences: list[str]
    quality_gate: int
    host_compatibility_min_score: int
    host_compatibility_min_ready_hosts: int
    host_profile_targets: list[str]
    host_profile_enforce_selected: bool
    phases: list[str]
    experts: list[str]


class WorkflowRunRequest(BaseModel):
    """工作流运行请求"""

    phases: list[str] | None = None
    quality_gate: int | None = None
    host_compatibility_min_score: int | None = None
    host_compatibility_min_ready_hosts: int | None = None
    host_profile_targets: list[str] | None = None
    host_profile_enforce_selected: bool | None = None
    language_preferences: list[str] | None = None
    name: str | None = None
    description: str | None = None
    platform: str | None = None
    frontend: str | None = None
    backend: str | None = None
    domain: str | None = None
    cicd: str | None = None
    orm: str | None = None
    offline: bool = False


class WorkflowRunResponse(BaseModel):
    """工作流运行响应"""

    status: str
    message: str
    run_id: str | None = None


class WorkflowDocsConfirmationRequest(BaseModel):
    """文档确认状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class WorkflowBaselineConfirmationRequest(BaseModel):
    """当前项目基线确认状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class WorkflowUIRevisionRequest(BaseModel):
    """UI 改版状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class WorkflowPreviewConfirmationRequest(BaseModel):
    """前端预览确认状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class WorkflowArchitectureRevisionRequest(BaseModel):
    """架构返工状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class WorkflowQualityRevisionRequest(BaseModel):
    """质量返工状态更新请求"""

    status: Literal["pending_review", "revision_requested", "confirmed"]
    comment: str = ""
    actor: str = "user"


class HostRuntimeValidationRequest(BaseModel):
    """宿主真人验收状态更新请求"""

    host: str
    status: Literal["pending", "passed", "failed"]
    comment: str = ""
    actor: str = "user"
    competition_evidence: dict[str, Any] = Field(default_factory=dict)


class PipelinePolicyResponse(BaseModel):
    require_redteam: bool
    require_quality_gate: bool
    require_rehearsal_verify: bool
    min_quality_threshold: int
    allowed_cicd_platforms: list[str]
    require_host_profile: bool
    required_hosts: list[str]
    enforce_required_hosts_ready: bool
    min_required_host_score: int
    policy_file: str
    policy_exists: bool


class PipelinePolicyUpdateRequest(BaseModel):
    preset: str | None = None
    require_redteam: bool | None = None
    require_quality_gate: bool | None = None
    require_rehearsal_verify: bool | None = None
    min_quality_threshold: int | None = None
    allowed_cicd_platforms: list[str] | None = None
    require_host_profile: bool | None = None
    required_hosts: list[str] | None = None
    enforce_required_hosts_ready: bool | None = None
    min_required_host_score: int | None = None


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="Super Dev API", description=f"{__description__} - Web API", version=__version__
)

# CORS 配置
_CORS_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8080",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Super-Dev-Key"],
)

app.add_middleware(cast(Any, RateLimitMiddleware))

# ── API Versioning ───────────────────────────────────────
# /api/v1/ is the canonical versioned prefix.
# Legacy /api/ routes remain for backward compatibility but are deprecated.
v1_router = APIRouter(prefix="/api/v1")

# ==================== API Key 认证 ====================

API_KEY_HEADER = APIKeyHeader(name="X-Super-Dev-Key", auto_error=False)


def get_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    """验证 API Key.

    写入端点强制要求 API Key:
    - 如果设置了 SUPER_DEV_API_KEY 环境变量, 则必须提供匹配的 key
    - 如果未设置环境变量, 则生成一次性 key 并写入启动日志 (仅限开发环境)
    - 生产环境必须设置 SUPER_DEV_API_KEY
    """
    expected_key = os.environ.get("SUPER_DEV_API_KEY")
    if not expected_key:
        _generated = os.environ.get("SUPER_DEV_GENERATED_KEY", "")
        if not _generated:
            import secrets

            _generated = secrets.token_urlsafe(32)
            os.environ["SUPER_DEV_GENERATED_KEY"] = _generated
            logging.getLogger("super_dev.web").warning(
                "SUPER_DEV_API_KEY not set. Generated one-time key for this session. "
                "Set SUPER_DEV_API_KEY in production!"
            )
        expected_key = _generated
    if api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_api_key",
                "message": "Valid X-Super-Dev-Key header required. Set SUPER_DEV_API_KEY env var.",
            },
        )
    return api_key


# ==================== 工作流运行状态 ====================

_RUN_STORE: dict[str, dict[str, Any]] = {}
_RUN_STORE_LOCK = Lock()
_RUN_STORE_MAX = 1000


def _evict_run_store() -> None:
    """Evict oldest in-memory run states when store exceeds max size."""
    if len(_RUN_STORE) <= _RUN_STORE_MAX:
        return
    # Remove oldest entries (first N inserted) to stay under limit
    overflow = len(_RUN_STORE) - _RUN_STORE_MAX
    keys_to_remove = list(_RUN_STORE.keys())[:overflow]
    for key in keys_to_remove:
        _RUN_STORE.pop(key, None)


VALID_CICD_PLATFORMS: set[str] = set(CICD_PLATFORM_IDS)
SUPPORTED_BACKEND_TEMPLATES: list[dict[str, str]] = BACKEND_TEMPLATE_CATALOG
SUPPORTED_LANGUAGE_PREFERENCES: list[dict[str, str]] = LANGUAGE_PREFERENCE_CATALOG


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_state_dir(project_dir: Path) -> Path:
    return project_dir / ".super-dev" / "runs"


def _run_state_file(project_dir: Path, run_id: str) -> Path:
    return _run_state_dir(project_dir) / f"{run_id}.json"


def _persist_run_state(project_dir: Path, run_id: str, run: dict[str, Any]) -> None:
    state_dir = _run_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    target_file = _run_state_file(project_dir, run_id)
    lock_file = state_dir / ".runs.lock"
    lock_handle = lock_file.open("a+", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=state_dir,
            prefix=f".{run_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(json.dumps(run, ensure_ascii=False, indent=2))
            temp_path = Path(temp_file.name)
        os.replace(temp_path, target_file)
    finally:
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def _load_persisted_run_state(project_dir: Path, run_id: str) -> dict[str, Any] | None:
    file_path = _run_state_file(project_dir, run_id)
    if not file_path.exists():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        _api_logger.debug(f"Failed to load persisted run state for {run_id}: {e}")
        return None
    return data if isinstance(data, dict) else None


def _store_run_state(run_id: str, persist_dir: Path | None = None, **fields: Any) -> None:
    with _RUN_STORE_LOCK:
        run = _RUN_STORE.setdefault(run_id, {})
        run.update(fields)
        run["run_id"] = run_id
        run["updated_at"] = _utc_now()
        run["status_normalized"] = _normalize_run_status(run.get("status"))
        if persist_dir is not None:
            _persist_run_state(persist_dir, run_id, run)
        _evict_run_store()


def _get_run_state(run_id: str, project_dir: Path | None = None) -> dict[str, Any] | None:
    with _RUN_STORE_LOCK:
        run = _RUN_STORE.get(run_id)
        if run is not None:
            return dict(run)

    if project_dir is None:
        return None

    persisted = _load_persisted_run_state(project_dir, run_id)
    if persisted is None:
        return None

    with _RUN_STORE_LOCK:
        _RUN_STORE[run_id] = dict(persisted)

    return persisted


def _list_persisted_runs(project_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    state_dir = _run_state_dir(project_dir)
    if not state_dir.exists():
        return []

    runs: list[dict[str, Any]] = []
    files = sorted(state_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for file_path in files[:limit]:
        data: dict[str, Any] | None = None
        try:
            loaded = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception as e:
            _api_logger.debug(f"Failed to load persisted run file {file_path.name}: {e}")
            data = None
        if data is not None:
            runs.append(data)
    return runs


def _with_pipeline_summary(run: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    enriched = dict(run)
    enriched["status_normalized"] = _normalize_run_status(enriched.get("status"))
    enriched["pipeline_summary"] = _detect_pipeline_summary(project_dir, run)
    return enriched


def _is_cancel_requested(run_id: str) -> bool:
    with _RUN_STORE_LOCK:
        run = _RUN_STORE.get(run_id)
        return bool(run and run.get("cancel_requested"))


def _normalize_run_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"success", "completed"}:
        return "completed"
    if normalized in {"failed"}:
        return "failed"
    if normalized in {"cancelled"}:
        return "cancelled"
    if normalized in {
        "running",
        "cancelling",
        "waiting_confirmation",
        "waiting_preview_confirmation",
        "waiting_ui_revision",
        "waiting_architecture_revision",
        "waiting_quality_revision",
    }:
        return "running"
    if normalized in {"queued"}:
        return "queued"
    return "unknown"


def _sanitize_run_payload(value: Any, depth: int = 0) -> Any:
    """将阶段输出裁剪为可安全持久化的 JSON 结构。"""
    if depth > 4:
        return "<truncated>"

    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, str):
        return value[:500] if len(value) > 500 else value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (k, v) in enumerate(value.items()):
            if idx >= 80:
                out["__truncated__"] = True
                break
            out[str(k)] = _sanitize_run_payload(v, depth + 1)
        return out

    if isinstance(value, list | tuple | set):
        out_list = []
        for idx, item in enumerate(value):
            if idx >= 120:
                out_list.append("<truncated>")
                break
            out_list.append(_sanitize_run_payload(item, depth + 1))
        return out_list

    return str(value)


def _collect_workflow_artifact_files(project_dir_path: Path) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    def _append(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists() or not resolved.is_file():
            return
        seen.add(resolved)
        files.append(resolved)

    output_dir = project_dir_path / "output"
    if output_dir.exists():
        for pattern in (
            "**/*.md",
            "**/*.json",
            "**/*.html",
            "**/*.css",
            "**/*.js",
            "**/*.yml",
            "**/*.yaml",
            "**/*.png",
        ):
            for file_path in output_dir.glob(pattern):
                _append(file_path)

    for direct in (
        project_dir_path / ".env.deploy.example",
        project_dir_path / ".gitlab-ci.yml",
        project_dir_path / ".azure-pipelines.yml",
        project_dir_path / "Jenkinsfile",
        project_dir_path / "bitbucket-pipelines.yml",
        project_dir_path / "Dockerfile",
        project_dir_path / "docker-compose.yml",
        project_dir_path / ".dockerignore",
    ):
        _append(direct)

    github_dir = project_dir_path / ".github" / "workflows"
    if github_dir.exists():
        for file_path in github_dir.glob("*.yml"):
            _append(file_path)

    k8s_dir = project_dir_path / "k8s"
    if k8s_dir.exists():
        for file_path in k8s_dir.glob("*.yaml"):
            _append(file_path)

    return files


def _resolve_run_project_dir(run_id: str, project_dir: str) -> tuple[dict[str, Any], Path]:
    requested_project_dir = _validate_project_dir(project_dir)
    run = _get_run_state(run_id, requested_project_dir)
    if run is None:
        raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")
    run_project_dir = Path(run.get("project_dir") or requested_project_dir).resolve()
    return run, run_project_dir


def _load_ui_review_summary(project_dir_path: Path) -> dict[str, Any] | None:
    output_dir = project_dir_path / "output"
    json_candidates = sorted(output_dir.glob("*-ui-review.json"))
    if json_candidates:
        try:
            raw_payload = json.loads(json_candidates[-1].read_text(encoding="utf-8"))
            if isinstance(raw_payload, dict):
                payload: dict[str, Any] = raw_payload
                payload.setdefault("json_path", str(json_candidates[-1]))
                md_path = json_candidates[-1].with_suffix(".md")
                if md_path.exists():
                    payload.setdefault("report_path", str(md_path))
                return payload
        except Exception as e:
            _api_logger.debug(f"Failed to parse UI review JSON: {e}")
    return None


def _load_latest_json_artifact(project_dir_path: Path, pattern: str) -> dict[str, Any]:
    output_dir = project_dir_path / "output"
    candidates = sorted(output_dir.glob(pattern))
    if not candidates:
        return {}
    try:
        payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_workflow_ui_governance_summary(
    project_dir_path: Path,
    summary: dict[str, Any] | None,
) -> dict[str, str]:
    ui_contract_payload = _load_latest_json_artifact(project_dir_path, "*-ui-contract.json")
    frontend_runtime_payload = _load_latest_json_artifact(
        project_dir_path, "*-frontend-runtime.json"
    )
    alignment_summary = (
        summary.get("alignment_summary", {})
        if isinstance(summary, dict) and isinstance(summary.get("alignment_summary"), dict)
        else {}
    )

    required_contract_sections = (
        "screen_recipes",
        "design_context_protocol",
        "tweak_strategy",
        "verification_handoff",
    )
    missing_contract_sections = [
        field for field in required_contract_sections if not ui_contract_payload.get(field)
    ]
    if missing_contract_sections:
        return {
            "state": "contract_freeze_incomplete",
            "message": "Claude-Design 风格执行协议尚未完全冻结: "
            + ", ".join(missing_contract_sections),
        }

    runtime_protocol = (
        alignment_summary.get("runtime_claude_design_protocol", {})
        if isinstance(alignment_summary.get("runtime_claude_design_protocol"), dict)
        else {}
    )
    if runtime_protocol and not bool(runtime_protocol.get("passed", False)):
        return {
            "state": "source_runtime_drift",
            "message": str(runtime_protocol.get("observed", "")).strip(),
        }

    source_protocol = (
        alignment_summary.get("source_claude_design_protocol", {})
        if isinstance(alignment_summary.get("source_claude_design_protocol"), dict)
        else {}
    )
    if source_protocol and not bool(source_protocol.get("passed", False)):
        return {
            "state": "source_execution_missing",
            "message": str(source_protocol.get("observed", "")).strip(),
        }

    runtime_checks = (
        frontend_runtime_payload.get("checks", {})
        if isinstance(frontend_runtime_payload.get("checks"), dict)
        else {}
    )
    missing_runtime_checks = missing_claude_design_runtime_checks(
        runtime_checks,
        ui_contract_payload,
    )
    if missing_runtime_checks:
        return {
            "state": "runtime_execution_missing",
            "message": ", ".join(missing_runtime_checks),
        }

    if runtime_protocol or source_protocol:
        return {
            "state": "ready",
            "message": "Claude-Design 风格执行协议在 source/runtime 证据中已闭环。",
        }
    return {"state": "unknown", "message": ""}


def _extract_frontend_governance_summary(payload: dict[str, Any]) -> dict[str, str]:
    summary_payload = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    executive_summary = str(summary_payload.get("executive_summary", "")).strip()
    if not executive_summary:
        return {"state": "unknown", "message": ""}
    if "契约冻结" in executive_summary:
        return {
            "state": "contract_freeze_incomplete",
            "message": executive_summary,
        }
    if "source/runtime 证据漂移" in executive_summary:
        return {
            "state": "source_runtime_drift",
            "message": executive_summary,
        }
    if "runtime 证明" in executive_summary:
        return {
            "state": "runtime_execution_missing",
            "message": executive_summary,
        }
    if "源码/预览落地" in executive_summary:
        return {
            "state": "source_execution_missing",
            "message": executive_summary,
        }
    if "UI 阶段" in executive_summary:
        return {"state": "ready", "message": executive_summary}
    return {"state": "unknown", "message": executive_summary}


def _extract_compliance_governance_summary(payload: dict[str, Any]) -> dict[str, str]:
    summary_payload = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    executive_summary = str(summary_payload.get("executive_summary", "")).strip()
    if not executive_summary:
        return {"state": "unknown", "message": ""}
    if "合规链当前优先卡在证据状态" in executive_summary:
        return {"state": "artifact_gap", "message": executive_summary}
    if "合规链证据已齐，但内容仍未达标" in executive_summary:
        return {"state": "content_gap", "message": executive_summary}
    if "合规链证据与内容检查当前均已闭环" in executive_summary:
        return {"state": "ready", "message": executive_summary}
    return {"state": "unknown", "message": executive_summary}


def _find_ui_review_screenshot(project_dir_path: Path) -> Path | None:
    screenshot_dir = project_dir_path / "output" / "ui-review"
    if not screenshot_dir.exists():
        return None
    candidates = sorted(screenshot_dir.glob("*-preview-desktop.png"))
    return candidates[-1] if candidates else None


def _normalize_string_list(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _build_policy_response(
    policy: PipelinePolicy, manager: PipelinePolicyManager
) -> dict[str, Any]:
    return {
        "require_redteam": policy.require_redteam,
        "require_quality_gate": policy.require_quality_gate,
        "require_rehearsal_verify": policy.require_rehearsal_verify,
        "min_quality_threshold": policy.min_quality_threshold,
        "allowed_cicd_platforms": policy.allowed_cicd_platforms,
        "require_host_profile": policy.require_host_profile,
        "required_hosts": policy.required_hosts,
        "enforce_required_hosts_ready": policy.enforce_required_hosts_ready,
        "min_required_host_score": policy.min_required_host_score,
        "policy_file": str(manager.policy_path),
        "policy_exists": manager.policy_path.exists(),
    }


# ==================== API 路由 ====================
# NOTE: Routes below use /api/ prefix for backward compatibility.
# The canonical prefix is /api/v1/ — see v1_router above.


@app.get("/api/health")
@v1_router.get("/health")
@app.get("/health")  # Alias for k8s probes and load balancers
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": __version__}


@app.get("/api/config")
@v1_router.get("/config")
async def get_config(project_dir: str = ".") -> dict:
    """获取项目配置"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = ConfigManager(project_dir_path)
        if not manager.exists():
            raise HTTPException(status_code=404, detail="项目未初始化")

        config = manager.config
        return {
            "name": config.name,
            "description": config.description,
            "version": config.version,
            "platform": config.platform,
            "frontend": config.frontend,
            "backend": config.backend,
            "database": config.database,
            "domain": config.domain,
            "language_preferences": config.language_preferences,
            "quality_gate": config.quality_gate,
            "host_compatibility_min_score": config.host_compatibility_min_score,
            "host_compatibility_min_ready_hosts": config.host_compatibility_min_ready_hosts,
            "host_profile_targets": config.host_profile_targets,
            "host_profile_enforce_selected": config.host_profile_enforce_selected,
            "phases": config.phases,
            "experts": config.experts,
            "output_dir": config.output_dir,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/policy", response_model=PipelinePolicyResponse)
async def get_policy(project_dir: str = ".") -> dict[str, Any]:
    """获取 pipeline policy"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = PipelinePolicyManager(project_dir_path)
        policy = manager.load()
        return _build_policy_response(policy=policy, manager=manager)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/policy/presets")
async def list_policy_presets() -> dict[str, Any]:
    """列出可用策略预设"""
    return {
        "presets": [
            {
                "id": "default",
                "description": "默认策略（兼顾灵活性）",
            },
            {
                "id": "balanced",
                "description": "团队协作增强（要求 host profile）",
            },
            {
                "id": "enterprise",
                "description": "商业级强治理（更高质量阈值 + host profile，可按项目配置关键宿主）",
            },
        ]
    }


@app.put("/api/policy", response_model=PipelinePolicyResponse, dependencies=[Depends(get_api_key)])
async def update_policy(
    request: PipelinePolicyUpdateRequest,
    project_dir: str = ".",
) -> dict[str, Any]:
    """更新 pipeline policy"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = PipelinePolicyManager(project_dir_path)
        preset_name = request.preset.strip().lower() if isinstance(request.preset, str) else ""
        if preset_name:
            current = manager.build_preset(preset_name)
        else:
            current = manager.load()

        min_quality_threshold = current.min_quality_threshold
        if request.min_quality_threshold is not None:
            if request.min_quality_threshold < 0 or request.min_quality_threshold > 100:
                raise HTTPException(
                    status_code=400, detail="min_quality_threshold 必须在 0-100 之间"
                )
            min_quality_threshold = request.min_quality_threshold

        allowed_cicd_platforms = current.allowed_cicd_platforms
        if request.allowed_cicd_platforms is not None:
            normalized = _normalize_string_list(request.allowed_cicd_platforms)
            if not normalized:
                raise HTTPException(status_code=400, detail="allowed_cicd_platforms 不能为空")
            invalid = [item for item in normalized if item not in VALID_CICD_PLATFORMS]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效 CI/CD 平台: {', '.join(invalid)}",
                )
            allowed_cicd_platforms = normalized

        required_hosts = current.required_hosts
        if request.required_hosts is not None:
            normalized_hosts = _normalize_string_list(request.required_hosts)
            allowed_hosts = {item["id"] for item in HOST_TOOL_CATALOG}
            invalid_hosts = [item for item in normalized_hosts if item not in allowed_hosts]
            if invalid_hosts:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效宿主: {', '.join(invalid_hosts)}",
                )
            required_hosts = normalized_hosts

        min_required_host_score = current.min_required_host_score
        if request.min_required_host_score is not None:
            if request.min_required_host_score < 0 or request.min_required_host_score > 100:
                raise HTTPException(
                    status_code=400, detail="min_required_host_score 必须在 0-100 之间"
                )
            min_required_host_score = request.min_required_host_score

        updated = PipelinePolicy(
            require_redteam=(
                request.require_redteam
                if request.require_redteam is not None
                else current.require_redteam
            ),
            require_quality_gate=(
                request.require_quality_gate
                if request.require_quality_gate is not None
                else current.require_quality_gate
            ),
            require_rehearsal_verify=(
                request.require_rehearsal_verify
                if request.require_rehearsal_verify is not None
                else current.require_rehearsal_verify
            ),
            min_quality_threshold=min_quality_threshold,
            allowed_cicd_platforms=allowed_cicd_platforms,
            require_host_profile=(
                request.require_host_profile
                if request.require_host_profile is not None
                else current.require_host_profile
            ),
            required_hosts=required_hosts,
            enforce_required_hosts_ready=(
                request.enforce_required_hosts_ready
                if request.enforce_required_hosts_ready is not None
                else current.enforce_required_hosts_ready
            ),
            min_required_host_score=min_required_host_score,
        )
        manager.save(updated)
        return _build_policy_response(policy=updated, manager=manager)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/init", dependencies=[Depends(get_api_key)])
@v1_router.post("/init", dependencies=[Depends(get_api_key)])
async def init_project(request: ProjectInitRequest, project_dir: str = ".") -> dict:
    """初始化项目"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = ConfigManager(project_dir_path)
        if manager.exists():
            raise HTTPException(status_code=400, detail="项目已初始化")

        config = manager.create(
            name=request.name,
            description=request.description,
            platform=request.platform,
            frontend=request.frontend,
            backend=request.backend,
            domain=request.domain,
            language_preferences=request.language_preferences,
            quality_gate=request.quality_gate,
            host_compatibility_min_score=request.host_compatibility_min_score,
            host_compatibility_min_ready_hosts=request.host_compatibility_min_ready_hosts,
            host_profile_targets=request.host_profile_targets,
            host_profile_enforce_selected=request.host_profile_enforce_selected,
        )

        return {
            "status": "success",
            "message": "项目已初始化",
            "config": {
                "name": config.name,
                "platform": config.platform,
                "frontend": config.frontend,
                "backend": config.backend,
            },
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/config", dependencies=[Depends(get_api_key)])
async def update_config(updates: dict, project_dir: str = ".") -> dict:
    """更新项目配置"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = ConfigManager(project_dir_path)
        if not manager.exists():
            raise HTTPException(status_code=404, detail="项目未初始化")

        config = manager.update(**updates)
        return {"status": "success", "config": config.__dict__}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/run", dependencies=[Depends(get_api_key)])
@v1_router.post("/workflow/run", dependencies=[Depends(get_api_key)])
async def run_workflow(
    request: WorkflowRunRequest, background_tasks: BackgroundTasks, project_dir: str = "."
) -> WorkflowRunResponse:
    """运行工作流"""
    try:
        project_dir_path = _validate_project_dir(project_dir)
        manager = ConfigManager(project_dir_path)
        if not manager.exists():
            raise HTTPException(status_code=404, detail="项目未初始化")

        # 更新门禁配置
        workflow_updates: dict[str, Any] = {}
        if request.quality_gate is not None:
            workflow_updates["quality_gate"] = request.quality_gate
        if request.host_compatibility_min_score is not None:
            workflow_updates["host_compatibility_min_score"] = request.host_compatibility_min_score
        if request.host_compatibility_min_ready_hosts is not None:
            workflow_updates["host_compatibility_min_ready_hosts"] = (
                request.host_compatibility_min_ready_hosts
            )
        if request.host_profile_targets is not None:
            workflow_updates["host_profile_targets"] = request.host_profile_targets
        if request.host_profile_enforce_selected is not None:
            workflow_updates["host_profile_enforce_selected"] = (
                request.host_profile_enforce_selected
            )
        if request.language_preferences is not None:
            workflow_updates["language_preferences"] = request.language_preferences
        if workflow_updates:
            manager.update(**workflow_updates)
        config = manager.config

        # 解析阶段
        phases = None
        requested_phase_names = None
        if request.phases:
            phase_map = {
                "discovery": Phase.DISCOVERY,
                "intelligence": Phase.INTELLIGENCE,
                "drafting": Phase.DRAFTING,
                "redteam": Phase.REDTEAM,
                "qa": Phase.QA,
                "delivery": Phase.DELIVERY,
                "deployment": Phase.DEPLOYMENT,
            }
            requested_phase_names = list(request.phases)
            resolved_phase_names = resolve_engine_phase_names(requested_phase_names)
            invalid_phases = [p for p in resolved_phase_names if p not in phase_map]
            if invalid_phases:
                raise HTTPException(
                    status_code=400, detail=f"无效阶段: {', '.join(invalid_phases)}"
                )
            phases = [phase_map[p] for p in resolved_phase_names]
            require_docs_confirmation(
                project_dir_path,
                action="workflow_run",
                requested_phases=requested_phase_names,
                require_context=False,
            )
            require_preview_confirmation(
                project_dir_path,
                action="workflow_run",
                requested_phases=requested_phase_names,
                require_context=True,
            )
        else:
            requested_phase_names = list(manager.config.phases)

        # 生成运行 ID
        import uuid

        run_id = str(uuid.uuid4())[:8]

        _store_run_state(
            run_id,
            persist_dir=project_dir_path,
            status="queued",
            project_dir=str(project_dir_path),
            requested_phases=requested_phase_names,
            completed_phases=[],
            progress=0,
            message="工作流排队中",
            cancel_requested=False,
            error=None,
            started_at=_utc_now(),
            finished_at=None,
            results=[],
        )

        # 后台运行工作流
        async def _run_workflow_background() -> None:
            if _is_cancel_requested(run_id):
                _store_run_state(
                    run_id,
                    persist_dir=project_dir_path,
                    status="cancelled",
                    message="工作流已取消（启动前）",
                    finished_at=_utc_now(),
                )
                return

            _store_run_state(
                run_id,
                persist_dir=project_dir_path,
                status="running",
                message="工作流运行中",
                progress=5,
            )
            try:
                engine = WorkflowEngine(project_dir_path)
                context = WorkflowContext(
                    project_dir=project_dir_path,
                    config=manager,
                    user_input={
                        "name": request.name or config.name or project_dir_path.name,
                        "description": (
                            request.description
                            if request.description is not None
                            else config.description
                        ),
                        "platform": request.platform or config.platform,
                        "frontend": request.frontend or config.frontend,
                        "backend": request.backend or config.backend,
                        "domain": request.domain if request.domain is not None else config.domain,
                        "language_preferences": (
                            request.language_preferences
                            if request.language_preferences is not None
                            else config.language_preferences
                        ),
                        "cicd": request.cicd or "github",
                        "orm": request.orm,
                        "offline": request.offline,
                        "quality_threshold": request.quality_gate,
                        "host_compatibility_min_score": (
                            request.host_compatibility_min_score
                            if request.host_compatibility_min_score is not None
                            else config.host_compatibility_min_score
                        ),
                        "host_compatibility_min_ready_hosts": (
                            request.host_compatibility_min_ready_hosts
                            if request.host_compatibility_min_ready_hosts is not None
                            else config.host_compatibility_min_ready_hosts
                        ),
                        "host_profile_targets": (
                            request.host_profile_targets
                            if request.host_profile_targets is not None
                            else config.host_profile_targets
                        ),
                        "host_profile_enforce_selected": (
                            request.host_profile_enforce_selected
                            if request.host_profile_enforce_selected is not None
                            else config.host_profile_enforce_selected
                        ),
                    },
                )
                context.metadata["workflow_run_id"] = run_id
                results = await engine.run(
                    phases=phases,
                    context=context,
                    stop_requested=lambda: _is_cancel_requested(run_id),
                )

                planned = max(len(requested_phase_names or []), 1)
                completed = []
                serialized_results = []
                for phase, result in results.items():
                    completed.append(phase.value)
                    serialized_results.append(
                        {
                            "phase": phase.value,
                            "success": result.success,
                            "duration": result.duration,
                            "quality_score": result.quality_score,
                            "errors": list(result.errors or []),
                            "output": _sanitize_run_payload(result.output),
                        }
                    )

                all_success = (
                    all(item["success"] for item in serialized_results)
                    if serialized_results
                    else True
                )
                progress = min(100, int(len(completed) / planned * 100))
                if _is_cancel_requested(run_id):
                    status = "cancelled"
                    message = "工作流已取消"
                else:
                    status = "completed" if all_success and progress >= 100 else "failed"
                    message = "工作流执行完成" if status == "completed" else "工作流执行失败"

                _store_run_state(
                    run_id,
                    persist_dir=project_dir_path,
                    status=status,
                    message=message,
                    completed_phases=completed,
                    progress=progress,
                    results=serialized_results,
                    finished_at=_utc_now(),
                )
            except Exception as e:
                cancel_requested = _is_cancel_requested(run_id)
                status = "cancelled" if cancel_requested else "failed"
                message = "工作流已取消" if cancel_requested else "工作流执行异常"
                _store_run_state(
                    run_id,
                    persist_dir=project_dir_path,
                    status=status,
                    message=message,
                    cancel_requested=cancel_requested,
                    error=str(e),
                    finished_at=_utc_now(),
                )

        def _run_workflow_background_sync() -> None:
            asyncio.run(_run_workflow_background())

        background_tasks.add_task(_run_workflow_background_sync)

        return WorkflowRunResponse(
            status="started", message=f"工作流已启动 (ID: {run_id})", run_id=run_id
        )

    except HTTPException:
        raise
    except WorkflowGateError as e:
        raise HTTPException(status_code=409, detail=e.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/status/{run_id}")
@v1_router.get("/workflow/status/{run_id}")
async def get_workflow_status(run_id: str, project_dir: str = ".") -> dict:
    """获取工作流状态"""
    run_id = _validate_run_id(run_id)
    project_dir_path = _validate_project_dir(project_dir)
    run = _get_run_state(run_id, project_dir_path)
    if run is None:
        raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")
    enriched = _with_pipeline_summary(run, project_dir_path)
    _store_run_state(
        run_id, persist_dir=project_dir_path, pipeline_summary=enriched["pipeline_summary"]
    )
    return enriched


@app.get("/api/workflow/docs-confirmation")
@v1_router.get("/workflow/docs-confirmation")
async def get_workflow_docs_confirmation(project_dir: str = ".") -> dict:
    """获取三文档确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_docs_confirmation(project_dir_path) or {}
    gate_state = require_docs_confirmation(
        project_dir_path,
        action="docs_confirmation_status",
        requested_phases=[],
        require_context=False,
    )
    return {
        "project_dir": str(project_dir_path),
        "status": str(payload.get("status", "")).strip() or "pending_review",
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "artifact_binding": payload.get("artifact_binding", {}),
        "current_artifact_binding": gate_state.get("artifact_binding", {}),
        "binding_matches_current": gate_state.get("binding_matches_current", True),
        "ledger_entry": gate_state.get("ledger_entry", {}),
        "exists": bool(payload),
        "file_path": str(docs_confirmation_file(project_dir_path)),
    }


@app.get("/api/workflow/baseline-confirmation")
@v1_router.get("/workflow/baseline-confirmation")
async def get_workflow_baseline_confirmation(project_dir: str = ".") -> dict:
    """获取当前项目基线确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_baseline_confirmation(project_dir_path) or {}
    status = str(payload.get("status", "")).strip() or "pending_review"
    baseline_governance = inspect_baseline_governance(project_dir_path)
    workflow_context = build_host_workflow_context(project_dir_path)
    return {
        "project_dir": str(project_dir_path),
        "status": status,
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "exists": bool(payload),
        "file_path": str(baseline_confirmation_file(project_dir_path)),
        "baseline_governance": baseline_governance,
        "workflow_context": workflow_context,
        "host_guidance": {
            "summary": str(baseline_governance.get("host_guidance_summary", "")).strip()
            or "已有项目先 baseline，再由用户确认 baseline，之后才继续差量文档与实现。",
            "next_host_action": (
                "回到宿主里说“继续当前流程”"
                if status == "confirmed"
                else "回到宿主里说“baseline 确认，可以继续当前流程”"
            ),
            "fallback_text_entry": str(baseline_governance.get("fallback_text_entry", "")).strip()
            or (
                "super-dev: 继续当前流程"
                if status == "confirmed"
                else "super-dev: baseline 确认，可以继续当前流程"
            ),
        },
    }


@app.post("/api/workflow/baseline-confirmation", dependencies=[Depends(get_api_key)])
@v1_router.post("/workflow/baseline-confirmation", dependencies=[Depends(get_api_key)])
async def update_workflow_baseline_confirmation(
    request: WorkflowBaselineConfirmationRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新当前项目基线确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path = save_baseline_confirmation(project_dir_path, payload)
    baseline_governance = inspect_baseline_governance(project_dir_path)
    workflow_context = build_host_workflow_context(project_dir_path)
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": (load_baseline_confirmation(project_dir_path) or {}).get("updated_at", ""),
        "file_path": str(file_path),
        "baseline_governance": baseline_governance,
        "workflow_context": workflow_context,
        "host_guidance": {
            "summary": str(baseline_governance.get("host_guidance_summary", "")).strip()
            or (
                "baseline confirmation 已更新；确认完成后，回到宿主继续当前流程。"
                if request.status == "confirmed"
                else "baseline confirmation 已更新；在宿主里先完成 baseline 确认，再继续当前流程。"
            ),
            "next_host_action": (
                "回到宿主里说“继续当前流程”"
                if request.status == "confirmed"
                else "回到宿主里说“baseline 确认，可以继续当前流程”"
            ),
        },
    }


@app.post("/api/workflow/docs-confirmation", dependencies=[Depends(get_api_key)])
@v1_router.post("/workflow/docs-confirmation", dependencies=[Depends(get_api_key)])
async def update_workflow_docs_confirmation(
    request: WorkflowDocsConfirmationRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新三文档确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path, ledger_entry = save_bound_docs_confirmation(project_dir_path, payload)
    saved_payload = load_docs_confirmation(project_dir_path) or {}
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": saved_payload.get("updated_at", ""),
        "artifact_binding": saved_payload.get("artifact_binding", {}),
        "current_artifact_binding": saved_payload.get("artifact_binding", {}),
        "binding_matches_current": True,
        "ledger_entry": ledger_entry,
        "file_path": str(file_path),
    }


@app.get("/api/workflow/preview-confirmation")
@v1_router.get("/workflow/preview-confirmation")
async def get_workflow_preview_confirmation(project_dir: str = ".") -> dict:
    """获取前端预览确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_preview_confirmation(project_dir_path) or {}
    gate_state = preview_gate_status(project_dir_path)
    return {
        "project_dir": str(project_dir_path),
        "status": str(payload.get("status", "")).strip() or "pending_review",
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "artifact_binding": payload.get("artifact_binding", {}),
        "current_artifact_binding": gate_state.get("artifact_binding", {}),
        "binding_matches_current": gate_state.get("binding_matches_current", True),
        "ledger_entry": gate_state.get("ledger_entry", {}),
        "exists": bool(payload),
        "file_path": str(preview_confirmation_file(project_dir_path)),
    }


@app.post("/api/workflow/preview-confirmation", dependencies=[Depends(get_api_key)])
@v1_router.post("/workflow/preview-confirmation", dependencies=[Depends(get_api_key)])
async def update_workflow_preview_confirmation(
    request: WorkflowPreviewConfirmationRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新前端预览确认状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path, ledger_entry = save_bound_preview_confirmation(project_dir_path, payload)
    saved_payload = load_preview_confirmation(project_dir_path) or {}
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": saved_payload.get("updated_at", ""),
        "artifact_binding": saved_payload.get("artifact_binding", {}),
        "current_artifact_binding": saved_payload.get("artifact_binding", {}),
        "binding_matches_current": True,
        "ledger_entry": ledger_entry,
        "file_path": str(file_path),
    }


@app.get("/api/workflow/ui-revision")
async def get_workflow_ui_revision(project_dir: str = ".") -> dict:
    """获取 UI 改版状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_ui_revision(project_dir_path) or {}
    return {
        "project_dir": str(project_dir_path),
        "status": str(payload.get("status", "")).strip() or "pending_review",
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "exists": bool(payload),
        "file_path": str(ui_revision_file(project_dir_path)),
    }


@app.post("/api/workflow/ui-revision", dependencies=[Depends(get_api_key)])
async def update_workflow_ui_revision(
    request: WorkflowUIRevisionRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新 UI 改版状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path = save_ui_revision(project_dir_path, payload)
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": (load_ui_revision(project_dir_path) or {}).get("updated_at", ""),
        "file_path": str(file_path),
    }


@app.get("/api/workflow/architecture-revision")
async def get_workflow_architecture_revision(project_dir: str = ".") -> dict:
    """获取架构返工状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_architecture_revision(project_dir_path) or {}
    return {
        "project_dir": str(project_dir_path),
        "status": str(payload.get("status", "")).strip() or "pending_review",
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "exists": bool(payload),
        "file_path": str(architecture_revision_file(project_dir_path)),
    }


@app.post("/api/workflow/architecture-revision", dependencies=[Depends(get_api_key)])
async def update_workflow_architecture_revision(
    request: WorkflowArchitectureRevisionRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新架构返工状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path = save_architecture_revision(project_dir_path, payload)
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": (load_architecture_revision(project_dir_path) or {}).get("updated_at", ""),
        "file_path": str(file_path),
    }


@app.get("/api/workflow/quality-revision")
async def get_workflow_quality_revision(project_dir: str = ".") -> dict:
    """获取质量返工状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = load_quality_revision(project_dir_path) or {}
    return {
        "project_dir": str(project_dir_path),
        "status": str(payload.get("status", "")).strip() or "pending_review",
        "comment": str(payload.get("comment", "")).strip(),
        "actor": str(payload.get("actor", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "updated_at": str(payload.get("updated_at", "")).strip(),
        "exists": bool(payload),
        "file_path": str(quality_revision_file(project_dir_path)),
    }


@app.post("/api/workflow/quality-revision", dependencies=[Depends(get_api_key)])
async def update_workflow_quality_revision(
    request: WorkflowQualityRevisionRequest,
    project_dir: str = ".",
    run_id: str = "",
) -> dict:
    """更新质量返工状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    payload = {
        "status": request.status,
        "comment": request.comment.strip(),
        "actor": request.actor.strip() or "user",
        "run_id": run_id.strip(),
    }
    file_path = save_quality_revision(project_dir_path, payload)
    return {
        "status": request.status,
        "comment": payload["comment"],
        "actor": payload["actor"],
        "run_id": payload["run_id"],
        "updated_at": (load_quality_revision(project_dir_path) or {}).get("updated_at", ""),
        "file_path": str(file_path),
    }


@app.post("/api/workflow/cancel/{run_id}", dependencies=[Depends(get_api_key)])
async def cancel_workflow(run_id: str, project_dir: str = ".") -> dict:
    """取消工作流运行"""
    run_id = _validate_run_id(run_id)
    project_dir_path = _validate_project_dir(project_dir)
    run = _get_run_state(run_id, project_dir_path)
    if run is None:
        raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")

    status = str(run.get("status", "unknown"))
    if status in {"completed", "failed", "cancelled"}:
        return {
            "run_id": run_id,
            "status": status,
            "message": "运行已结束，无需取消",
        }

    if status == "queued":
        _store_run_state(
            run_id,
            persist_dir=project_dir_path,
            status="cancelled",
            cancel_requested=True,
            message="工作流已取消（未开始执行）",
            finished_at=_utc_now(),
        )
        return {
            "run_id": run_id,
            "status": "cancelled",
            "message": "工作流已取消",
        }

    _store_run_state(
        run_id,
        persist_dir=project_dir_path,
        status="cancelling",
        cancel_requested=True,
        message="已收到取消请求，将在当前阶段完成后停止",
    )
    return {
        "run_id": run_id,
        "status": "cancelling",
        "message": "取消请求已受理",
    }


@app.get("/api/workflow/runs")
async def list_workflow_runs(project_dir: str = ".", limit: int = 20) -> dict:
    """列出工作流运行历史（最近优先）"""
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit 必须大于 0")
    if limit > 500:
        limit = 500

    project_dir_path = _validate_project_dir(project_dir)
    runs = [
        _with_pipeline_summary(run, project_dir_path)
        for run in _list_persisted_runs(project_dir_path, limit=limit)
    ]
    return {"runs": runs, "count": len(runs)}


@app.get("/api/workflow/artifacts/{run_id}")
async def list_workflow_artifacts(run_id: str, project_dir: str = ".") -> dict:
    """列出某次工作流可下载的交付物文件。"""
    run, run_project_dir = _resolve_run_project_dir(run_id, project_dir)
    artifact_files = _collect_workflow_artifact_files(run_project_dir)
    items = []
    for file_path in artifact_files:
        try:
            relative = file_path.relative_to(run_project_dir).as_posix()
        except ValueError:
            relative = file_path.name
        items.append(
            {
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": str(relative),
                "size_bytes": file_path.stat().st_size,
            }
        )

    return {
        "run_id": run_id,
        "project_dir": str(run_project_dir),
        "count": len(items),
        "items": items,
    }


@app.get("/api/workflow/artifacts/{run_id}/archive")
async def download_workflow_artifacts_archive(run_id: str, project_dir: str = ".") -> FileResponse:
    """下载某次工作流交付物压缩包。"""
    _, run_project_dir = _resolve_run_project_dir(run_id, project_dir)
    artifact_files = _collect_workflow_artifact_files(run_project_dir)
    if not artifact_files:
        raise HTTPException(status_code=404, detail="未找到可下载的交付物文件")

    archive_dir = run_project_dir / "output" / "artifacts"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"workflow-{run_id}-artifacts.zip"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in artifact_files:
            try:
                arcname = str(file_path.relative_to(run_project_dir))
            except ValueError:
                arcname = file_path.name
            zf.write(file_path, arcname=arcname)

    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )


@app.get("/api/workflow/ui-review/{run_id}")
async def get_workflow_ui_review(run_id: str, project_dir: str = ".") -> dict:
    """获取某次工作流的 UI 审查摘要。"""
    run, run_project_dir = _resolve_run_project_dir(run_id, project_dir)
    summary = _load_ui_review_summary(run_project_dir)
    screenshot = _find_ui_review_screenshot(run_project_dir)

    qa_result = None
    if isinstance(run.get("results"), list):
        qa_result = next((item for item in run["results"] if item.get("phase") == "qa"), None)

    if summary is None and qa_result and isinstance(qa_result.get("output"), dict):
        nested = qa_result["output"].get("ui_review")
        if isinstance(nested, dict):
            summary = nested

    if summary is None and screenshot is None:
        raise HTTPException(status_code=404, detail="未找到 UI 审查结果")

    screenshot_url = ""
    screenshot_relative_path = ""
    if screenshot is not None:
        screenshot_url = (
            f"/api/workflow/ui-review/{run_id}/screenshot?"
            f"{urlencode({'project_dir': str(run_project_dir)})}"
        )
        try:
            screenshot_relative_path = screenshot.relative_to(run_project_dir).as_posix()
        except ValueError:
            screenshot_relative_path = screenshot.name

    frontend_governance_summary = _extract_workflow_ui_governance_summary(
        run_project_dir,
        summary if isinstance(summary, dict) else None,
    )
    alignment_summary = (
        summary.get("alignment_summary", {})
        if isinstance(summary, dict) and isinstance(summary.get("alignment_summary"), dict)
        else {}
    )

    return {
        "run_id": run_id,
        "project_dir": str(run_project_dir),
        "summary": summary or {},
        "frontend_governance_summary": frontend_governance_summary,
        "runtime_claude_design_protocol": (
            alignment_summary.get("runtime_claude_design_protocol", {})
            if isinstance(alignment_summary.get("runtime_claude_design_protocol"), dict)
            else {}
        ),
        "source_claude_design_protocol": (
            alignment_summary.get("source_claude_design_protocol", {})
            if isinstance(alignment_summary.get("source_claude_design_protocol"), dict)
            else {}
        ),
        "report_path": summary.get("report_path", "") if isinstance(summary, dict) else "",
        "json_path": summary.get("json_path", "") if isinstance(summary, dict) else "",
        "screenshot": {
            "exists": screenshot is not None,
            "path": str(screenshot) if screenshot is not None else "",
            "relative_path": screenshot_relative_path,
            "url": screenshot_url,
        },
    }


@app.get("/api/workflow/ui-review/{run_id}/screenshot")
async def download_workflow_ui_review_screenshot(
    run_id: str, project_dir: str = "."
) -> FileResponse:
    """获取某次工作流 UI 审查截图。"""
    _, run_project_dir = _resolve_run_project_dir(run_id, project_dir)
    screenshot = _find_ui_review_screenshot(run_project_dir)
    if screenshot is None:
        raise HTTPException(status_code=404, detail="未找到 UI 审查截图")
    return FileResponse(path=screenshot, media_type="image/png", filename=screenshot.name)


@app.get("/api/experts")
@v1_router.get("/experts")
async def list_experts() -> dict:
    """列出可用专家"""
    return {"experts": list_expert_catalog()}


@app.get("/api/phases")
@v1_router.get("/phases")
async def list_phases() -> dict:
    """列出工作流阶段"""
    phases = [
        {"id": "discovery", "name": "需求发现", "description": "收集和分析用户需求"},
        {"id": "intelligence", "name": "情报收集", "description": "市场研究、竞品分析"},
        {"id": "drafting", "name": "专家起草", "description": "专家协作生成文档"},
        {"id": "redteam", "name": "红队审查", "description": "安全、性能审查"},
        {"id": "qa", "name": "质量门禁", "description": "质量检查和验证"},
        {"id": "delivery", "name": "幻影交付", "description": "生成原型预览"},
        {"id": "deployment", "name": "工业化部署", "description": "生成部署配置"},
    ]
    return {"phases": phases}


@app.get("/api/catalogs")
async def get_catalogs() -> dict:
    """返回前端初始化和工作流表单所需的选项目录。"""
    return {
        "platforms": PLATFORM_CATALOG,
        "frontends": PIPELINE_FRONTEND_TEMPLATE_CATALOG,
        "backends": SUPPORTED_BACKEND_TEMPLATES,
        "domains": DOMAIN_CATALOG,
        "cicd_platforms": CICD_PLATFORM_CATALOG,
        "host_tools": _build_host_tool_catalog_payload(),
        "languages": SUPPORTED_LANGUAGE_PREFERENCES,
    }


@app.get("/api/hosts/doctor")
async def doctor_hosts(
    project_dir: str = ".",
    host: str | None = None,
    auto: bool = False,
    skill_name: str = "super-dev",
    skip_integrate: bool = False,
    skip_skill: bool = False,
    skip_slash: bool = False,
    repair: bool = False,
    force: bool = False,
) -> dict:
    """诊断宿主接入状态，并返回兼容性评分。"""
    project_dir_path = _validate_project_dir(project_dir)
    integration_manager = IntegrationManager(project_dir_path)
    all_targets = [item.name for item in integration_manager.list_targets()]
    available_targets = _public_host_targets(integration_manager=integration_manager)
    detected_targets, detected_meta = _detect_host_targets(available_targets)

    if host:
        if host not in all_targets:
            raise HTTPException(status_code=400, detail=f"不支持的 host: {host}")
        targets = [host]
    elif auto:
        targets = detected_targets or available_targets
    else:
        targets = available_targets

    check_integrate = not skip_integrate
    check_skill = not skip_skill
    check_slash = not skip_slash

    report = _collect_host_diagnostics(
        project_dir=project_dir_path,
        targets=targets,
        skill_name=skill_name,
        check_integrate=check_integrate,
        check_skill=check_skill,
        check_slash=check_slash,
    )
    compatibility = _build_host_compatibility_summary(
        report=report,
        targets=targets,
        check_integrate=check_integrate,
        check_skill=check_skill,
        check_slash=check_slash,
    )
    repair_actions: dict[str, dict[str, str]] = {}
    if repair:
        repair_actions = _repair_host_diagnostics(
            project_dir=project_dir_path,
            report=report,
            skill_name=skill_name,
            force=force,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
        )
        report = _collect_host_diagnostics(
            project_dir=project_dir_path,
            targets=targets,
            skill_name=skill_name,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
        )
        compatibility = _build_host_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
        )

    report["compatibility"] = compatibility
    if repair:
        report["repair_actions"] = repair_actions

    usage_profiles = {
        target: _serialize_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        for target in targets
    }
    decision_card = _build_detected_host_decision_card(
        project_dir=project_dir_path,
        integration_manager=integration_manager,
        detected_targets=detected_targets,
        detected_meta=detected_meta,
        preferred_targets=targets if host else None,
    )
    workflow_context = build_host_workflow_context(
        project_dir_path,
        entry_mode=str(decision_card.get("workflow_mode", "")).strip(),
        target=str(decision_card.get("selected_host", "")).strip(),
    )
    decision_card["workflow_context"] = workflow_context

    return {
        "status": "success",
        "project_dir": str(project_dir_path),
        "selected_targets": targets,
        "detected_targets": detected_targets,
        "detection_details": detected_meta,
        "detection_details_pretty": _explain_detection_details(detected_meta),
        "report": report,
        "compatibility": compatibility,
        "usage_profiles": usage_profiles,
        "adaptation_contracts": {
            target: dict(usage.get("adaptation_contract", {}))
            for target, usage in usage_profiles.items()
            if isinstance(usage, dict) and isinstance(usage.get("adaptation_contract", {}), dict)
        },
        "experience_profiles": {
            target: dict(usage.get("experience_profile", {}))
            for target, usage in usage_profiles.items()
            if isinstance(usage, dict) and isinstance(usage.get("experience_profile", {}), dict)
        },
        "workflow_context": workflow_context,
        "decision_card": decision_card,
        "selected_host_adaptation": (
            dict(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()][
                    "adaptation_contract"
                ]
            )
            if str(decision_card.get("selected_host", "")).strip() in usage_profiles
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()],
                dict,
            )
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()].get(
                    "adaptation_contract",
                    {},
                ),
                dict,
            )
            else {}
        ),
        "selected_host_experience": (
            dict(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()][
                    "experience_profile"
                ]
            )
            if str(decision_card.get("selected_host", "")).strip() in usage_profiles
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()],
                dict,
            )
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()].get(
                    "experience_profile",
                    {},
                ),
                dict,
            )
            else {}
        ),
        "selected_host_post_onboard_self_check": (
            list(decision_card.get("selected_host_post_onboard_self_check", []))
            if isinstance(decision_card.get("selected_host_post_onboard_self_check", []), list)
            else []
        ),
        "selected_host_start_playbook": (
            list(decision_card.get("selected_host_start_playbook", []))
            if isinstance(decision_card.get("selected_host_start_playbook", []), list)
            else []
        ),
        "selected_host_standard_flow_first_prompt": str(
            decision_card.get("selected_host_standard_flow_first_prompt", "")
        ).strip(),
        "selected_host_competition_flow_first_prompt": str(
            decision_card.get("selected_host_competition_flow_first_prompt", "")
        ).strip(),
        "selected_host_resume_guidance": (
            list(decision_card.get("selected_host_resume_guidance", []))
            if isinstance(decision_card.get("selected_host_resume_guidance", []), list)
            else []
        ),
        "selected_host_injection_closure": (
            dict(decision_card.get("selected_host_injection_closure", {}))
            if isinstance(decision_card.get("selected_host_injection_closure", {}), dict)
            else {}
        ),
        "selected_host_ready_for_standard_flow": bool(
            decision_card.get("selected_host_ready_for_standard_flow", False)
        ),
        "selected_host_ready_for_competition_flow": bool(
            decision_card.get("selected_host_ready_for_competition_flow", False)
        ),
        "selected_host_standard_flow_label": str(
            decision_card.get("selected_host_standard_flow_label", "")
        ).strip(),
        "selected_host_competition_flow_label": str(
            decision_card.get("selected_host_competition_flow_label", "")
        ).strip(),
        "selected_host_official_workflow_checks": (
            list(decision_card.get("selected_host_official_workflow_checks", []))
            if isinstance(decision_card.get("selected_host_official_workflow_checks", []), list)
            else []
        ),
        "selected_host_repair_playbook": str(
            decision_card.get("selected_host_repair_playbook", "")
        ).strip(),
        "primary_repair_action": _build_primary_repair_action(
            report=report,
            targets=targets,
            integration_manager=integration_manager,
            decision_card=decision_card,
        ),
        "session_resume_cards": {
            target: _build_session_resume_card(
                project_dir_path,
                target,
                usage_profiles[target],
            )
            for target in targets
        },
        "auto": auto,
        "repair": repair,
    }


@app.get("/api/hosts/validate")
async def validate_hosts(
    project_dir: str = ".",
    host: str | None = None,
    auto: bool = False,
    skill_name: str = "super-dev",
) -> dict[str, Any]:
    project_dir_path = _validate_project_dir(project_dir)
    integration_manager = IntegrationManager(project_dir_path)
    all_targets = [item.name for item in integration_manager.list_targets()]
    available_targets = _public_host_targets(integration_manager=integration_manager)
    detected_targets, detected_meta = _detect_host_targets(available_targets)

    if host:
        if host not in all_targets:
            raise HTTPException(status_code=400, detail=f"不支持的 host: {host}")
        targets = [host]
    elif auto:
        targets = detected_targets or available_targets
    else:
        targets = available_targets

    report = _collect_host_diagnostics(
        project_dir=project_dir_path,
        targets=targets,
        skill_name=skill_name,
        check_integrate=True,
        check_skill=True,
        check_slash=True,
    )
    usage_profiles = {
        target: _serialize_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        for target in targets
    }
    decision_card = _build_detected_host_decision_card(
        project_dir=project_dir_path,
        integration_manager=integration_manager,
        detected_targets=detected_targets,
        detected_meta=detected_meta,
        preferred_targets=targets if host else None,
    )
    workflow_context = build_host_workflow_context(
        project_dir_path,
        entry_mode=str(decision_card.get("workflow_mode", "")).strip(),
        target=str(decision_card.get("selected_host", "")).strip(),
    )
    decision_card["workflow_context"] = workflow_context
    payload = _build_host_runtime_validation_payload(
        project_dir=project_dir_path,
        targets=targets,
        detected_meta=detected_meta,
        report=report,
        usage_profiles=usage_profiles,
    )

    return {
        "status": "success",
        "project_dir": str(project_dir_path),
        "selected_targets": targets,
        "detected_targets": detected_targets,
        "detection_details": detected_meta,
        "detection_details_pretty": _explain_detection_details(detected_meta),
        "report": payload,
        "usage_profiles": usage_profiles,
        "adaptation_contracts": {
            target: dict(usage.get("adaptation_contract", {}))
            for target, usage in usage_profiles.items()
            if isinstance(usage, dict) and isinstance(usage.get("adaptation_contract", {}), dict)
        },
        "experience_profiles": {
            target: dict(usage.get("experience_profile", {}))
            for target, usage in usage_profiles.items()
            if isinstance(usage, dict) and isinstance(usage.get("experience_profile", {}), dict)
        },
        "workflow_context": workflow_context,
        "decision_card": decision_card,
        "selected_host_adaptation": (
            dict(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()][
                    "adaptation_contract"
                ]
            )
            if str(decision_card.get("selected_host", "")).strip() in usage_profiles
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()],
                dict,
            )
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()].get(
                    "adaptation_contract",
                    {},
                ),
                dict,
            )
            else {}
        ),
        "selected_host_experience": (
            dict(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()][
                    "experience_profile"
                ]
            )
            if str(decision_card.get("selected_host", "")).strip() in usage_profiles
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()],
                dict,
            )
            and isinstance(
                usage_profiles[str(decision_card.get("selected_host", "")).strip()].get(
                    "experience_profile",
                    {},
                ),
                dict,
            )
            else {}
        ),
        "selected_host_post_onboard_self_check": (
            list(decision_card.get("selected_host_post_onboard_self_check", []))
            if isinstance(decision_card.get("selected_host_post_onboard_self_check", []), list)
            else []
        ),
        "selected_host_start_playbook": (
            list(decision_card.get("selected_host_start_playbook", []))
            if isinstance(decision_card.get("selected_host_start_playbook", []), list)
            else []
        ),
        "selected_host_standard_flow_first_prompt": str(
            decision_card.get("selected_host_standard_flow_first_prompt", "")
        ).strip(),
        "selected_host_competition_flow_first_prompt": str(
            decision_card.get("selected_host_competition_flow_first_prompt", "")
        ).strip(),
        "selected_host_resume_guidance": (
            list(decision_card.get("selected_host_resume_guidance", []))
            if isinstance(decision_card.get("selected_host_resume_guidance", []), list)
            else []
        ),
        "selected_host_injection_closure": (
            dict(decision_card.get("selected_host_injection_closure", {}))
            if isinstance(decision_card.get("selected_host_injection_closure", {}), dict)
            else {}
        ),
        "selected_host_ready_for_standard_flow": bool(
            decision_card.get("selected_host_ready_for_standard_flow", False)
        ),
        "selected_host_ready_for_competition_flow": bool(
            decision_card.get("selected_host_ready_for_competition_flow", False)
        ),
        "selected_host_standard_flow_label": str(
            decision_card.get("selected_host_standard_flow_label", "")
        ).strip(),
        "selected_host_competition_flow_label": str(
            decision_card.get("selected_host_competition_flow_label", "")
        ).strip(),
        "selected_host_official_workflow_checks": (
            list(decision_card.get("selected_host_official_workflow_checks", []))
            if isinstance(decision_card.get("selected_host_official_workflow_checks", []), list)
            else []
        ),
        "selected_host_repair_playbook": str(
            decision_card.get("selected_host_repair_playbook", "")
        ).strip(),
        "session_resume_cards": {
            target: _build_session_resume_card(project_dir_path, target, usage_profiles[target])
            for target in targets
        },
        "auto": auto,
    }


@app.get("/api/hosts/runtime-validation")
async def get_hosts_runtime_validation(
    project_dir: str = ".",
    host: str | None = None,
    auto: bool = False,
    skill_name: str = "super-dev",
) -> dict[str, Any]:
    """读取宿主真人运行时验收状态。"""
    return await validate_hosts(
        project_dir=project_dir, host=host, auto=auto, skill_name=skill_name
    )


@app.post("/api/hosts/runtime-validation", dependencies=[Depends(get_api_key)])
async def update_hosts_runtime_validation(
    request: HostRuntimeValidationRequest,
    project_dir: str = ".",
) -> dict[str, Any]:
    """更新宿主真人运行时验收状态。"""
    project_dir_path = _validate_project_dir(project_dir)
    integration_manager = IntegrationManager(project_dir_path)
    available_targets = [item.name for item in integration_manager.list_targets()]
    if request.host not in available_targets:
        raise HTTPException(status_code=400, detail=f"不支持的 host: {request.host}")

    runtime_state, file_path = _update_host_runtime_validation_state(
        project_dir=project_dir_path,
        host=request.host,
        status=request.status,
        comment=request.comment,
        actor=request.actor,
        competition_evidence=request.competition_evidence,
    )
    host_entry = runtime_state.get("hosts", {}).get(request.host, {})
    if not isinstance(host_entry, dict):
        host_entry = {}
    return {
        "status": "success",
        "host": request.host,
        "manual_runtime_status": request.status,
        "manual_runtime_status_label": _host_runtime_status_label(request.status),
        "comment": str(host_entry.get("comment", "")).strip(),
        "actor": str(host_entry.get("actor", "")).strip(),
        "updated_at": str(host_entry.get("updated_at", "")).strip(),
        "competition_evidence": normalize_competition_evidence(
            host_entry.get("competition_evidence", {})
        ),
        "competition_evidence_ready": bool(host_entry.get("competition_evidence_ready", False)),
        "competition_evidence_missing": list(host_entry.get("competition_evidence_missing", [])),
        "repo_probe": build_host_runtime_probe(
            project_dir_path,
            target=request.host,
            surface_ready=True,
        ),
        "runtime_evidence": _build_runtime_evidence_record(
            host_id=request.host,
            surface_ready=True,
            runtime_entry=host_entry,
        ),
        "file_path": str(file_path),
    }


@app.get("/api/release/readiness")
async def get_release_readiness(
    project_dir: str = ".",
    verify_tests: bool = False,
    persist: bool = False,
) -> dict[str, Any]:
    project_dir_path = _validate_project_dir(project_dir)
    evaluator = ReleaseReadinessEvaluator(project_dir_path)
    report = evaluator.evaluate(verify_tests=verify_tests)
    payload = report.to_dict()
    if persist:
        files = evaluator.write(report)
        payload["report_file"] = str(files["markdown"])
        payload["json_file"] = str(files["json"])
    else:
        payload["report_file"] = ""
        payload["json_file"] = ""
    payload["persisted"] = persist
    payload["frontend_governance_summary"] = _extract_frontend_governance_summary(payload)
    payload["compliance_governance_summary"] = _extract_compliance_governance_summary(payload)
    return payload


@app.get("/api/release/proof-pack")
async def get_release_proof_pack(
    project_dir: str = ".",
    verify_tests: bool = False,
    persist: bool = False,
) -> dict[str, Any]:
    project_dir_path = _validate_project_dir(project_dir)
    builder = ProofPackBuilder(project_dir_path)
    report = builder.build(verify_tests=verify_tests)
    payload = report.to_dict()
    if persist:
        files = builder.write(report)
        payload["report_file"] = str(files["markdown"])
        payload["json_file"] = str(files["json"])
        payload["summary_file"] = str(files["summary"])
    else:
        payload["report_file"] = ""
        payload["json_file"] = ""
        payload["summary_file"] = ""
    payload["persisted"] = persist
    payload["frontend_governance_summary"] = _extract_frontend_governance_summary(payload)
    payload["compliance_governance_summary"] = _extract_compliance_governance_summary(payload)
    return payload


# ==================== Hooks 端点 ====================


def _mount_frontend_if_present() -> None:
    """在 API 路由注册完成后挂载前端，避免遮蔽 /api 路由。"""
    frontend_path = Path(__file__).parent / "frontend" / "dist"
    if not frontend_path.exists():
        return

    for route in app.routes:
        if getattr(route, "name", "") == "frontend":
            return

    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


# Mount v1 router
app.include_router(v1_router)

_mount_frontend_if_present()


# ==================== 主函数 ====================


def main():
    """启动 API 服务器"""
    host = os.getenv("SUPER_DEV_API_HOST", "127.0.0.1")
    port = int(os.getenv("SUPER_DEV_API_PORT", "8000"))
    reload_enabled = os.getenv("SUPER_DEV_API_RELOAD", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    uvicorn.run(
        "super_dev.web.api:app", host=host, port=port, reload=reload_enabled, log_level="info"
    )


if __name__ == "__main__":
    main()
