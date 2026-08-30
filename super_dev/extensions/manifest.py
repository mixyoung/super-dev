"""扩展清单的严格解析与校验。"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml  # type: ignore[import-untyped]

from ..workflow_contract import CANONICAL_NINE_STAGE_IDS
from .models import (
    AuthoritySpec,
    Capability,
    ExecutionSpec,
    ExtensionManifest,
    OwnershipSpec,
    SourceSpec,
    TriggerSpec,
    WriteSpec,
)

_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ManifestValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _mapping(value: Any, field: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{field} 必须是对象")
        return {}
    return value


def _strict_keys(
    data: dict[str, Any], *, field: str, required: set[str], allowed: set[str], errors: list[str]
) -> None:
    missing = sorted(required - set(data))
    unknown = sorted(set(data) - allowed)
    if missing:
        errors.append(f"{field} 缺少必填字段: {missing}")
    if unknown:
        errors.append(f"{field} 包含未知字段: {unknown}")


def _safe_relative(value: Any, field: str, errors: list[str], *, allow_token: bool = False) -> str:
    raw = str(value or "").strip()
    if allow_token and raw == "$USER_SURFACES/**":
        return raw
    if not raw:
        errors.append(f"{field} 不能为空")
        return raw
    if "\\" in raw:
        errors.append(f"{field} 必须使用正斜杠相对路径")
        return raw
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or raw.startswith(("/", "~")):
        errors.append(f"{field} 必须位于允许根目录内，不能使用绝对路径、~ 或 ..")
    return raw


def _bool_field(data: dict[str, Any], name: str, field: str, errors: list[str]) -> bool:
    value = data.get(name)
    if not isinstance(value, bool):
        errors.append(f"{field}.{name} 必须是布尔值")
        return False
    return value


def parse_manifest(data: Any, *, manifest_path: Path | None = None) -> ExtensionManifest:
    errors: list[str] = []
    root = _mapping(data, "manifest", errors)
    root_required = {
        "schema_version",
        "id",
        "version",
        "kind",
        "source",
        "trigger",
        "capabilities",
        "ownership",
        "writes",
        "authority",
        "execution",
        "result",
    }
    _strict_keys(
        root, field="manifest", required=root_required, allowed=root_required, errors=errors
    )

    schema_version = root.get("schema_version")
    if schema_version != 1:
        errors.append("manifest.schema_version 仅支持 1")

    extension_id = str(root.get("id", "")).strip()
    if not _ID_RE.fullmatch(extension_id):
        errors.append("manifest.id 必须使用小写字母、数字和连字符")
    version = str(root.get("version", "")).strip()
    if not _SEMVER_RE.fullmatch(version):
        errors.append("manifest.version 必须使用三段语义版本")
    kind = str(root.get("kind", "")).strip()
    if kind not in {"builtin-test-adapter", "engineering-method"}:
        errors.append("manifest.kind 必须是 builtin-test-adapter 或 engineering-method")

    source = _mapping(root.get("source"), "source", errors)
    source_kind = str(source.get("kind", "")).strip()
    base_source_keys = {"kind", "path", "content_digest"}
    adapted_keys = {
        *base_source_keys,
        "upstream_repository",
        "upstream_commit",
        "upstream_path",
        "upstream_digest",
    }
    if source_kind == "builtin":
        _strict_keys(
            source,
            field="source",
            required=base_source_keys,
            allowed=base_source_keys,
            errors=errors,
        )
    elif source_kind == "adapted":
        _strict_keys(
            source,
            field="source",
            required=adapted_keys,
            allowed=adapted_keys,
            errors=errors,
        )
    else:
        errors.append("source.kind 必须是 builtin 或 adapted")
        _strict_keys(
            source,
            field="source",
            required=base_source_keys,
            allowed=adapted_keys,
            errors=errors,
        )
    source_path = _safe_relative(source.get("path"), "source.path", errors)
    content_digest = str(source.get("content_digest", "")).strip()
    if not _DIGEST_RE.fullmatch(content_digest):
        errors.append("source.content_digest 必须是 sha256:<64位小写十六进制>")
    upstream_repository = str(source.get("upstream_repository", "")).strip()
    upstream_commit = str(source.get("upstream_commit", "")).strip()
    upstream_path = str(source.get("upstream_path", "")).strip()
    upstream_digest = str(source.get("upstream_digest", "")).strip()
    if source_kind == "adapted":
        if not upstream_repository:
            errors.append("source.upstream_repository 不能为空")
        if not _COMMIT_RE.fullmatch(upstream_commit):
            errors.append("source.upstream_commit 必须是完整 40 位提交摘要")
        _safe_relative(upstream_path, "source.upstream_path", errors)
        if not _DIGEST_RE.fullmatch(upstream_digest):
            errors.append("source.upstream_digest 必须是 sha256:<64位小写十六进制>")

    trigger = _mapping(root.get("trigger"), "trigger", errors)
    _strict_keys(
        trigger,
        field="trigger",
        required={"mode", "allowed_stages"},
        allowed={"mode", "allowed_stages"},
        errors=errors,
    )
    mode = str(trigger.get("mode", "")).strip()
    if mode != "explicit":
        errors.append("trigger.mode 阶段 1 仅支持 explicit")
    raw_stages = trigger.get("allowed_stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        errors.append("trigger.allowed_stages 必须是非空数组")
        raw_stages = []
    stages = tuple(str(item).strip() for item in raw_stages if str(item).strip())
    unknown_stages = sorted(set(stages) - set(CANONICAL_NINE_STAGE_IDS))
    if unknown_stages:
        errors.append(f"trigger.allowed_stages 包含未知阶段: {unknown_stages}")
    if len(set(stages)) != len(stages):
        errors.append("trigger.allowed_stages 不能重复")

    capabilities = _mapping(root.get("capabilities"), "capabilities", errors)
    _strict_keys(
        capabilities,
        field="capabilities",
        required={"required"},
        allowed={"required"},
        errors=errors,
    )
    raw_required = capabilities.get("required")
    if not isinstance(raw_required, list):
        errors.append("capabilities.required 必须是数组")
        raw_required = []
    required_capabilities: list[Capability] = []
    for item in raw_required:
        try:
            required_capabilities.append(Capability(str(item)))
        except ValueError:
            errors.append(f"capabilities.required 包含未知能力: {item}")
    if len(set(required_capabilities)) != len(required_capabilities):
        errors.append("capabilities.required 不能重复")

    ownership = _mapping(root.get("ownership"), "ownership", errors)
    ownership_keys = {
        "lifecycle",
        "orchestration",
        "production_writer",
        "placement",
        "may_spawn_subworkers",
    }
    _strict_keys(
        ownership,
        field="ownership",
        required=ownership_keys,
        allowed=ownership_keys,
        errors=errors,
    )
    ownership_values = {
        name: _bool_field(ownership, name, "ownership", errors) for name in ownership_keys
    }

    writes = _mapping(root.get("writes"), "writes", errors)
    _strict_keys(
        writes,
        field="writes",
        required={"allowed", "forbidden"},
        allowed={"allowed", "forbidden"},
        errors=errors,
    )
    allowed_writes_raw = writes.get("allowed")
    forbidden_writes_raw = writes.get("forbidden")
    if not isinstance(allowed_writes_raw, list):
        errors.append("writes.allowed 必须是数组")
        allowed_writes_raw = []
    if not isinstance(forbidden_writes_raw, list):
        errors.append("writes.forbidden 必须是数组")
        forbidden_writes_raw = []
    allowed_writes = tuple(
        _safe_relative(item, f"writes.allowed[{index}]", errors)
        for index, item in enumerate(allowed_writes_raw)
    )
    forbidden_writes = tuple(
        _safe_relative(
            item,
            f"writes.forbidden[{index}]",
            errors,
            allow_token=True,
        )
        for index, item in enumerate(forbidden_writes_raw)
    )

    authority = _mapping(root.get("authority"), "authority", errors)
    authority_keys = {
        "commit",
        "merge",
        "push",
        "pull_request",
        "deploy",
        "external_write",
        "global_install",
    }
    _strict_keys(
        authority,
        field="authority",
        required=authority_keys,
        allowed=authority_keys,
        errors=errors,
    )
    authority_values = {
        name: _bool_field(authority, name, "authority", errors) for name in authority_keys
    }

    execution = _mapping(root.get("execution"), "execution", errors)
    _strict_keys(
        execution,
        field="execution",
        required={"executor", "entrypoint", "timeout_seconds"},
        allowed={"executor", "entrypoint", "timeout_seconds"},
        errors=errors,
    )
    executor = str(execution.get("executor", "")).strip()
    if executor != "builtin-python":
        errors.append("execution.executor 阶段 1 仅支持 builtin-python")
    entrypoint = str(execution.get("entrypoint", "")).strip()
    if not entrypoint or ":" not in entrypoint:
        errors.append("execution.entrypoint 必须使用 module:function")
    timeout = execution.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not (1 <= timeout <= 3600):
        errors.append("execution.timeout_seconds 必须是 1-3600 的整数")
        timeout = 30

    result = _mapping(root.get("result"), "result", errors)
    _strict_keys(
        result,
        field="result",
        required={"schema"},
        allowed={"schema"},
        errors=errors,
    )
    result_schema = str(result.get("schema", "")).strip()
    if result_schema != "extension-result-v1":
        errors.append("result.schema 仅支持 extension-result-v1")

    if errors:
        raise ManifestValidationError(errors)

    return ExtensionManifest(
        schema_version=1,
        id=extension_id,
        version=version,
        kind=kind,
        source=SourceSpec(
            kind=source_kind,
            path=source_path,
            content_digest=content_digest,
            upstream_repository=upstream_repository,
            upstream_commit=upstream_commit,
            upstream_path=upstream_path,
            upstream_digest=upstream_digest,
        ),
        trigger=TriggerSpec(mode=mode, allowed_stages=stages),
        required_capabilities=tuple(required_capabilities),
        ownership=OwnershipSpec(
            lifecycle=ownership_values["lifecycle"],
            orchestration=ownership_values["orchestration"],
            production_writer=ownership_values["production_writer"],
            placement=ownership_values["placement"],
            may_spawn_subworkers=ownership_values["may_spawn_subworkers"],
        ),
        writes=WriteSpec(allowed=allowed_writes, forbidden=forbidden_writes),
        authority=AuthoritySpec(
            commit=authority_values["commit"],
            merge=authority_values["merge"],
            push=authority_values["push"],
            pull_request=authority_values["pull_request"],
            deploy=authority_values["deploy"],
            external_write=authority_values["external_write"],
            global_install=authority_values["global_install"],
        ),
        execution=ExecutionSpec(executor=executor, entrypoint=entrypoint, timeout_seconds=timeout),
        result_schema=result_schema,
        manifest_path=manifest_path.resolve() if manifest_path else None,
    )


def load_manifest(path: Path | str) -> ExtensionManifest:
    manifest_path = Path(path).resolve()
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestValidationError([f"无法读取扩展清单: {exc}"]) from exc
    return parse_manifest(data, manifest_path=manifest_path)
