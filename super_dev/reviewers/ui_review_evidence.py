"""Read-only validation and local publication of independent UI evidence.

The host owns browser execution and image input. Validation checks the recorded
chain and scope, not aesthetic quality or the authenticity of an unsigned host log.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit

from ..artifact_utils import (
    resolve_work_item_identity,
    sanitize_artifact_name,
    ui_contract_filename,
)
from ..atomic_io import atomic_write_text
from ..evidence_contract import EvidenceArtifact, EvidenceEnvelope, EvidenceStatus
from ..evidence_identity import build_evidence_identity, evidence_identity_matches
from ..workflow_guard import docs_gate_status

SOURCE = "ui-source-review"
RUNTIME = "frontend-runtime"
VISUAL = "ui-visual-review"
KINDS = (SOURCE, RUNTIME, VISUAL)
LABELS = {SOURCE: "源码规则", RUNTIME: "浏览器运行与交互", VISUAL: "视觉评审"}
STATUS_LABELS = {
    EvidenceStatus.PASS: "通过（PASS）",
    EvidenceStatus.FAIL: "失败（FAIL）",
    EvidenceStatus.BLOCKED: "未验证，验收受阻（BLOCKED）",
    EvidenceStatus.NOT_APPLICABLE: "不适用（NOT_APPLICABLE）",
}
DIMENSIONS = ("layout", "hierarchy", "readability", "brand")
DEVICES = ("desktop", "mobile")
# File reads are limited to the agreed local evidence directory or frontend build/source files.
_LOG_DIR = PurePosixPath("output/ui-review")
_WEB_SUFFIXES = {
    ".html",
    ".htm",
    ".js",
    ".mjs",
    ".css",
    ".svg",
    ".woff",
    ".woff2",
    ".png",
    ".jpeg",
    ".jpg",
    ".webp",
}
_MAX_FILE = 32 * 1024 * 1024


@dataclass(frozen=True)
class UIResult:
    kind: str
    status: EvidenceStatus
    reason: str
    detail: str
    path: Path | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    dependencies: tuple[Path, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "detail": self.detail,
            "path": self.path.name if self.path else "",
            **{
                key: self.payload[key]
                for key in (
                    "producer",
                    "run_id",
                    "observed_at",
                    "coverage",
                    "uncovered",
                    "candidate_digest",
                    "work_item_id",
                    "findings",
                    "observations",
                    "score",
                )
                if key in self.payload
            },
        }


def aggregate_ui_status(results: Iterable[UIResult]) -> EvidenceStatus:
    statuses = {result.status for result in results}
    if EvidenceStatus.FAIL in statuses:
        return EvidenceStatus.FAIL
    if EvidenceStatus.BLOCKED in statuses or not statuses:
        return EvidenceStatus.BLOCKED
    if statuses == {EvidenceStatus.NOT_APPLICABLE}:
        return EvidenceStatus.NOT_APPLICABLE
    return EvidenceStatus.PASS


def ui_status_ok(status: EvidenceStatus) -> bool:
    return status in {EvidenceStatus.PASS, EvidenceStatus.NOT_APPLICABLE}


def ui_result_details(results: Iterable[UIResult]) -> str:
    return "；".join(
        f"{LABELS[result.kind]}：{STATUS_LABELS[result.status]}。{result.detail}"
        for result in results
    )


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return []
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_time(value: Any) -> bool:
    try:
        return datetime.fromisoformat(_text(value).replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _private_url(value: Any) -> bool:
    """Only accept actual network page addresses, never userinfo or opaque data URLs."""
    try:
        url = urlsplit(_text(value))
        return not (
            url.scheme in {"http", "https"}
            and url.hostname
            and not url.username
            and not url.password
        )
    except ValueError:
        return True


class UIReviewEvidence:
    """One view of the current UI inputs. Readers never modify files or start tools."""

    def __init__(self, project_dir: Path, prefix: str, *, required: bool = True):
        self.project = Path(project_dir).resolve()
        self.output = self.project / "output"
        self.required = required
        self.work_item = resolve_work_item_identity(self.project) if required else None
        self.prefix = (
            self.work_item.artifact_prefix if self.work_item else ""
        ) or sanitize_artifact_name(prefix)
        self.uiux = self.output / f"{self.prefix}-uiux.md"
        self.contract = self.output / ui_contract_filename(self.prefix)
        self._binding_cache: dict[str, str] | None = None
        self._results: dict[str, UIResult] = {}

    def path(self, kind: str) -> Path:
        if kind not in KINDS:
            raise ValueError("未知的 UI 证据类型")
        return self.output / f"{self.prefix}-{kind}.json"

    def _file(self, path: str, *, record: bool = False, web_asset: bool = False) -> Path:
        relative = PurePosixPath(_text(path))
        windows = PureWindowsPath(_text(path))
        if (
            relative.is_absolute()
            or windows.anchor
            or "\\" in path
            or ":" in path
            or ".." in relative.parts
        ):
            raise ValueError("证据必须引用当前项目内的相对路径")
        if record and not relative.is_relative_to(_LOG_DIR):
            raise ValueError("原始记录和截图必须位于 output/ui-review")
        if web_asset and (
            relative.suffix.lower() not in _WEB_SUFFIXES
            or any(part.startswith(".") or part == "node_modules" for part in relative.parts)
            or (relative.parts[0] == "output" and not relative.is_relative_to("output/frontend"))
        ):
            raise ValueError("运行对象必须指向当前项目中的前端文件")
        candidate = self.project.joinpath(*relative.parts)
        if candidate.resolve() != candidate or not candidate.is_file():
            raise ValueError("所引用的文件缺失或不是当前项目中的普通文件")
        return candidate

    def _source_file(self, path: str) -> Path:
        relative = PurePosixPath(path)
        allowed_metadata = {
            f"output/{self.uiux.name}",
            f"output/{self.contract.name}",
            "package.json",
            "frontend/package.json",
        }
        if path not in allowed_metadata and (
            relative.suffix.lower()
            not in {
                ".html",
                ".css",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".svelte",
                ".vue",
                ".scss",
                ".less",
                ".dart",
                ".wxml",
                ".wxss",
                ".axml",
                ".acss",
                ".ttml",
                ".ttss",
                ".qml",
                ".swift",
            }
            or any(part.startswith(".") for part in relative.parts)
            or relative.is_relative_to(_LOG_DIR)
        ):
            raise ValueError("源码检查引用了不受支持的项目输入")
        return self._file(path)

    def _bytes(self, path: Path) -> bytes:
        with path.open("rb") as file:
            data = file.read(_MAX_FILE + 1)
        if not data or len(data) > _MAX_FILE:
            raise ValueError("证据文件为空或过大")
        return data

    def _json(self, path: Path) -> dict[str, Any]:
        payload = _object(json.loads(self._bytes(path)))
        if not payload:
            raise ValueError("证据不是有效的 JSON 对象")
        return payload

    def _ref(self, ref: Any, *, web_asset: bool = False) -> tuple[Path, bytes]:
        item = _object(ref)
        path = self._file(_text(item.get("path")), record=not web_asset, web_asset=web_asset)
        data = self._bytes(path)
        if _sha(data) != _text(item.get("sha256")):
            raise ValueError("文件摘要与记录不一致")
        return path, data

    def capture_binding(self) -> dict[str, str]:
        """Take this snapshot before executing the browser, not when filling a report."""
        if self._binding_cache is not None:
            return dict(self._binding_cache)
        if (
            not self.required
            or not self.work_item
            or not self.work_item.valid
            or not self.work_item.work_item_id
            or not self.work_item.active_change_id
        ):
            raise ValueError("没有与正式变更绑定的工作项，不能验证当前 UI")
        uiux = self._file(f"output/{self.uiux.name}")
        contract = self._file(f"output/{self.contract.name}")
        if not docs_gate_status(self.project)["confirmed"]:
            raise ValueError("当前的 UI/UX 文档未确认或已经变化")
        current = build_evidence_identity(
            self.project, artifact_name="ui-input", dependencies=[uiux, contract]
        )
        self._binding_cache = {
            "work_item_id": self.work_item.work_item_id,
            "candidate_digest": current["candidate_digest"],
            "uiux_sha256": _sha(self._bytes(uiux)),
            "contract_sha256": _sha(self._bytes(contract)),
        }
        return dict(self._binding_cache)

    def _matrix(self) -> set[tuple[str, str, str]]:
        recipes = _objects(self._json(self.contract).get("screen_recipes"))
        if not recipes:
            raise ValueError("UI 契约缺少页面与关键状态范围")
        targets: set[tuple[str, str, str]] = set()
        screens: set[str] = set()
        for recipe in recipes:
            name = _text(recipe.get("id"))
            states = recipe.get("required_states")
            if (
                not name
                or name in screens
                or not isinstance(states, list)
                or not all(_text(item) for item in states)
            ):
                raise ValueError("UI 契约中的页面或关键状态范围不明确")
            screens.add(name)
            targets.update(
                (name, device, state)
                for device in DEVICES
                for state in {"default", *map(_text, states)}
            )
        return targets

    def _checked_result(
        self,
        kind: str,
        status: EvidenceStatus,
        reason: str,
        detail: str,
        payload: dict[str, Any],
        dependencies: Iterable[Path],
    ) -> UIResult:
        return UIResult(
            kind,
            status,
            reason,
            detail,
            self.path(kind),
            payload,
            tuple(dict.fromkeys(dependencies)),
        )

    def _record_payload(self, kind: str, record_ref: dict[str, Any]) -> UIResult:
        binding = self.capture_binding()
        path, raw = self._ref(record_ref)
        record = _object(json.loads(raw))
        producer = _object(record.get("producer"))
        run_id = _text(record.get("run_id"))
        observed = _text(record.get("observed_at"))
        expected_format = {
            RUNTIME: "super-dev-browser-run/v1",
            VISUAL: "super-dev-image-review/v1",
        }[kind]
        allowed_producers = {RUNTIME: {"browser"}, VISUAL: {"host_model", "vision_tool"}}[kind]
        if record.get("format") != expected_format or record.get("binding") != binding:
            raise ValueError("原始记录格式不符，或不属于当前工作项、当前代码版本及确认文档")
        if (
            not run_id
            or not _valid_time(observed)
            or producer.get("kind") not in allowed_producers
            or not all(_text(producer.get(key)) for key in ("host", "id"))
        ):
            raise ValueError("缺少可核对的实际执行者、运行编号或时间")
        dependencies = [self.uiux, self.contract, path]
        payload = {
            **binding,
            "producer": producer,
            "run_id": run_id,
            "observed_at": observed,
            "record": record_ref,
            "workflow_run_id": _text(record.get("workflow_run_id")),
        }
        if kind == RUNTIME:
            return self._browser(record, payload, dependencies)
        blocked_reason = _text(record.get("blocked_reason"))
        if blocked_reason:
            reasons = {
                "no_image_capability": "宿主没有已获授权且可用的图片理解能力。",
                "image_transfer_failed": "图片未传到实际评审执行者。",
                "tool_unavailable": "视觉工具未能完成本次调用。",
                "partial_vision": "工具只能执行局部检查，不能替代视觉评审。",
                "input_record_unavailable": "无法取得可核对的实际图片输入记录。",
            }
            if blocked_reason not in reasons:
                raise ValueError("无法识别未验证原因")
            return self._checked_result(
                VISUAL,
                EvidenceStatus.BLOCKED,
                blocked_reason,
                reasons[blocked_reason],
                payload,
                dependencies,
            )
        return self._vision(record, payload, dependencies)

    def _browser(
        self, record: dict[str, Any], payload: dict[str, Any], dependencies: list[Path]
    ) -> UIResult:
        matrix = self._matrix()
        coverage: set[tuple[str, str, str]] = set()
        screenshots = []
        findings = []
        ids: set[str] = set()
        for page in _objects(record.get("pages")):
            capture_id = _text(page.get("id"))
            viewport = _object(page.get("viewport"))
            target = (
                _text(page.get("screen")),
                _text(viewport.get("device")),
                _text(page.get("state")),
            )
            if (
                not capture_id
                or capture_id in ids
                or _private_url(page.get("url"))
                or target not in matrix
                or not _valid_time(page.get("observed_at"))
                or any(
                    not isinstance(viewport.get(key), int)
                    or isinstance(viewport[key], bool)
                    or not 0 < viewport[key] <= 32768
                    for key in ("width", "height")
                )
            ):
                raise ValueError("浏览器记录缺少有效页面、视口、状态或唯一截图标识")
            ids.add(capture_id)
            assets = _objects(page.get("loaded_files"))
            steps = _objects(page.get("steps"))
            if not assets or not steps or not _text(page.get("event_id")):
                continue
            for asset in assets:
                asset_path, _ = self._ref(asset, web_asset=True)
                dependencies.append(asset_path)
            for step in steps:
                if step.get("status") not in {"PASS", "FAIL"} or not all(
                    _text(step.get(key)) for key in ("action", "expected", "observed")
                ):
                    raise ValueError("没有实际操作、预期和观察结果，不能算作运行验证")
                if step["status"] == "FAIL":
                    findings.append({"page_id": capture_id, **step})
            if not page.get("file"):
                continue
            image_path, image = self._ref(page.get("file"))
            image_type = (
                "image/png"
                if image_path.suffix.lower() == ".png"
                and image.startswith(b"\x89PNG\r\n\x1a\n")
                and image.endswith(b"IEND\xaeB`\x82")
                else (
                    "image/jpeg"
                    if image_path.suffix.lower() in {".jpeg", ".jpg"}
                    and image.startswith(b"\xff\xd8\xff")
                    and image.endswith(b"\xff\xd9")
                    else ""
                )
            )
            if not image_type:
                raise ValueError("只接受已取得的原始 PNG/JPEG 截图")
            dependencies.append(image_path)
            screenshots.append({**page, "media_type": image_type})
            if {step.get("kind") for step in steps} >= {"navigation", "interaction"}:
                coverage.add(target)
        missing = sorted(matrix - coverage)
        payload.update(
            screenshots=screenshots, coverage=sorted(coverage), uncovered=missing, findings=findings
        )
        if findings:
            state, code, message = (
                EvidenceStatus.FAIL,
                "browser_failed",
                "浏览器实际执行发现问题；未覆盖范围另列。",
            )
        elif missing:
            state, code, message = (
                EvidenceStatus.BLOCKED,
                "browser_coverage",
                "缺少要求的桌面、移动端或关键状态运行与交互记录。",
            )
        else:
            state, code, message = (
                EvidenceStatus.PASS,
                "browser_verified",
                "实际页面导航、交互及截图记录齐全。",
            )
        return self._checked_result(RUNTIME, state, code, message, payload, dependencies)

    def _image_input_event(self, attachment: dict[str, Any]) -> Path | None:
        """Match the actual typed image block from a local host event excerpt."""
        if not attachment.get("input_event") or not _text(attachment.get("event_id")):
            return None
        path, data = self._ref(attachment["input_event"])
        event = _object(json.loads(data))
        if (
            event.get("type") not in {"tool_result", "tool_input", "image_message"}
            or (event.get("tool_use_id") or event.get("id")) != attachment["event_id"]
        ):
            return None
        for block in _objects(event.get("content")):
            source = _object(block.get("source"))
            if (
                block.get("type") != "image"
                or source.get("type") != "base64"
                or source.get("media_type") != attachment.get("media_type")
            ):
                continue
            try:
                actual_image = base64.b64decode(_text(source.get("data")), validate=True)
            except ValueError:
                continue
            if actual_image and _sha(actual_image) == attachment["sha256"]:
                return path
        return None

    def _vision(
        self, record: dict[str, Any], payload: dict[str, Any], dependencies: list[Path]
    ) -> UIResult:
        runtime = self.result(RUNTIME)
        if runtime.path:
            dependencies.append(runtime.path)
        dependencies.extend(runtime.dependencies)
        if not runtime.payload.get("screenshots") or record.get(
            "browser_run_id"
        ) != runtime.payload.get("run_id"):
            raise ValueError("图片输入没有对应当前的浏览器运行与截图")
        screenshots = {item["id"]: item for item in runtime.payload["screenshots"]}
        if not record.get("input_record"):
            return self._checked_result(
                VISUAL,
                EvidenceStatus.BLOCKED,
                "image_input_missing",
                "缺少实际图片输入记录；截图存在不等于已经看过。",
                payload,
                dependencies,
            )
        input_path, input_data = self._ref(record.get("input_record"))
        dependencies.append(input_path)
        inputs = _object(json.loads(input_data))
        if (
            inputs.get("format") != "super-dev-host-image-input/v1"
            or inputs.get("producer") != payload["producer"]
            or inputs.get("run_id") != payload["run_id"]
            or not _text(inputs.get("input_event_id"))
            or not _valid_time(inputs.get("observed_at"))
            or not _text(record.get("response_event_id"))
            or record.get("response_to") != inputs["input_event_id"]
            or record["response_event_id"] == inputs["input_event_id"]
        ):
            raise ValueError("图片输入记录与实际评审执行者或工具响应无法对应")
        if not record.get("response_record"):
            return self._checked_result(
                VISUAL,
                EvidenceStatus.BLOCKED,
                "image_response_missing",
                "缺少可核对的实际评审响应记录。",
                payload,
                dependencies,
            )
        response_path, response_data = self._ref(record["response_record"])
        response = _object(json.loads(response_data))
        if (
            response.get("type") not in {"tool_result", "tool_use", "review_message"}
            or (response.get("id") or response.get("tool_use_id")) != record["response_event_id"]
            or response.get("timestamp") != payload["observed_at"]
            or not response.get("content")
        ):
            raise ValueError("评审响应事件与本次视觉评审无法对应")
        dependencies.append(response_path)
        accepted: set[str] = set()
        accepted_events: set[str] = set()
        for item in _objects(inputs.get("attachments")):
            capture_id = _text(item.get("screenshot_id"))
            screenshot = screenshots.get(capture_id)
            if (
                item.get("content_type") != "image"
                or not screenshot
                or item.get("derivation")
                or item.get("media_type") != screenshot["media_type"]
                or item.get("sha256") != screenshot["file"]["sha256"]
            ):
                continue
            native_input = self._image_input_event(item)
            if native_input is not None:
                dependencies.append(native_input)
                accepted.add(capture_id)
                accepted_events.add(item["event_id"])
        if accepted and record["response_to"] not in accepted_events:
            raise ValueError("评审响应没有关联到匹配的真实图片事件")
        seen: set[tuple[str, str]] = set()
        observations = []
        findings = []
        for item in _objects(record.get("observations")):
            capture_id = _text(item.get("screenshot_id"))
            dimension = _text(item.get("dimension"))
            if capture_id not in accepted or dimension not in DIMENSIONS:
                continue
            verdict = item.get("status")
            fields = ["location", "observation", "requirement"]
            if verdict == "FAIL":
                fields += ["impact", "recommendation"]
            if verdict not in {"PASS", "FAIL"} or not all(_text(item.get(key)) for key in fields):
                continue
            if _text(item["observation"]).strip("。.!！ ").lower() in {
                "已检查",
                "通过",
                "无问题",
                "looks good",
                "ok",
                "pass",
            }:
                continue
            seen.add((capture_id, dimension))
            observations.append(item)
            if verdict == "FAIL":
                findings.append(item)
        missing = sorted(
            {(sid, dimension) for sid in screenshots for dimension in DIMENSIONS} - seen
        )
        missing_pages = sorted(
            self._matrix()
            - {
                (page["screen"], page["viewport"]["device"], page["state"])
                for sid, page in screenshots.items()
                if all((sid, dimension) in seen for dimension in DIMENSIONS)
            }
        )
        payload.update(
            coverage=sorted(seen),
            uncovered=[*missing_pages, *missing],
            findings=findings,
            observations=observations,
            input_event_id=inputs["input_event_id"],
            response_event_id=record["response_event_id"],
        )
        if findings:
            state, code, message = (
                EvidenceStatus.FAIL,
                "visual_failed",
                "看图发现未满足已确认设计的可见问题；未覆盖范围另列。",
            )
        elif missing or missing_pages:
            state, code, message = (
                EvidenceStatus.BLOCKED,
                "visual_coverage",
                "原图输入、截图覆盖或对照设计的观察不完整。",
            )
        else:
            state, code, message = (
                EvidenceStatus.PASS,
                "visual_verified",
                "当前原始截图有对应实际图片输入和位置化观察。",
            )
        return self._checked_result(VISUAL, state, code, message, payload, dependencies)

    def _identity(self, result: UIResult) -> dict[str, Any]:
        identity = build_evidence_identity(
            self.project,
            artifact_name=result.kind,
            dependencies=result.dependencies,
            run_id=result.payload["run_id"],
        )
        if any(
            identity[key] != result.payload[key] for key in ("candidate_digest", "work_item_id")
        ):
            raise ValueError("证据处理期间工作项或代码发生变化，需重新执行")
        return identity

    def _write_payload(self, result: UIResult) -> dict[str, Any]:
        if self.output.resolve() != self.output:
            raise ValueError("拒绝向项目外写入 UI 证据")
        path = self.path(result.kind)
        if path.resolve() != path:
            raise ValueError("拒绝覆盖链接指向的 UI 证据")
        identity = self._identity(result)
        envelope = EvidenceEnvelope(
            schema_version=1,
            evidence_id=f"{result.kind}-{result.payload['run_id']}",
            evidence_type=result.kind,
            subject_type="candidate",
            subject_digest=identity["candidate_digest"],
            work_item_id=identity["work_item_id"],
            candidate_digest=identity["candidate_digest"],
            producer=result.payload["producer"]["id"],
            run_id=result.payload["run_id"],
            status=result.status,
            observed_at=result.payload["observed_at"],
            artifacts=tuple(EvidenceArtifact(path=label) for label in identity["dependencies"]),
            invalidation_triggers=("candidate_changed", "inputs_changed", "work_item_changed"),
        )
        return {
            **result.payload,
            "kind": result.kind,
            "schema_version": 1,
            "status": result.status.value,
            "passed": ui_status_ok(result.status),
            "reason": result.reason,
            "detail": result.detail,
            "evidence_identity": identity,
            "evidence_envelope": envelope.to_dict(),
        }

    def write_artifact(self, path: Path, text: str) -> None:
        if (
            path.parent != self.output
            or path.resolve() != path
            or self.output.resolve() != self.output
        ):
            raise ValueError("拒绝向项目外写入 UI 证据")
        if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
            atomic_write_text(path, text)

    def _save(self, result: UIResult) -> None:
        payload = self._write_payload(result)
        self.write_artifact(
            self.path(result.kind), json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        self._results.pop(result.kind, None)
        if result.kind == RUNTIME:
            self._results.pop(VISUAL, None)
            self.write_artifact(
                self.path(RUNTIME).with_suffix(".md"),
                "# 浏览器运行与交互\n\n" + ui_result_details([result]) + "\n",
            )

    def record_host_result(self, kind: str, record_path: str) -> UIResult:
        """Publish an existing host receipt; never generate or refresh its capture binding."""
        if kind not in (RUNTIME, VISUAL):
            raise ValueError("只能导入宿主的浏览器与图片输入记录")
        path = self._file(record_path, record=True)
        result = self._record_payload(
            kind,
            {"path": path.relative_to(self.project).as_posix(), "sha256": _sha(self._bytes(path))},
        )
        self._save(result)
        return result

    def source_result(
        self,
        *,
        status: EvidenceStatus,
        detail: str,
        score: int,
        findings: list[dict[str, Any]],
        alignment: dict[str, Any],
        files: Iterable[Path],
    ) -> UIResult:
        if not self.required:
            return self.result(SOURCE)
        try:
            binding = self.capture_binding()
            dependencies = [self.uiux, self.contract]
            for path in files:
                file = self._source_file(path.relative_to(self.project).as_posix())
                self._bytes(file)
                dependencies.append(file)
            existing = self.result(SOURCE)
            if (
                existing.dependencies == tuple(dict.fromkeys(dependencies))
                and existing.status is status
                and existing.detail == detail
                and existing.payload.get("score") == score
                and existing.payload.get("findings") == findings
                and existing.payload.get("alignment_summary") == alignment
            ):
                return existing
            return self._checked_result(
                SOURCE,
                status,
                "source_checked" if status != EvidenceStatus.BLOCKED else "source_incomplete",
                detail,
                {
                    **binding,
                    "producer": {
                        "kind": "source_checker",
                        "host": "Super Dev",
                        "id": "ui-source-review",
                    },
                    "run_id": uuid.uuid4().hex,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "coverage": [
                        file.relative_to(self.project).as_posix() for file in dependencies
                    ],
                    "uncovered": [],
                    "score": score,
                    "findings": findings,
                    "alignment_summary": alignment,
                },
                dependencies,
            )
        except (OSError, RuntimeError, ValueError):
            return UIResult(
                SOURCE,
                EvidenceStatus.BLOCKED,
                "source_identity_missing",
                "源码诊断可以查看，但缺少当前工作项、确认文档或可读输入，不能作为正式验收。",
            )

    def save_source(self, result: UIResult) -> None:
        if result.kind == SOURCE and result.dependencies:
            self._save(result)

    def _load_source(self, raw: dict[str, Any]) -> UIResult:
        binding = self.capture_binding()
        if any(raw.get(key) != value for key, value in binding.items()):
            raise ValueError("源码检查不属于当前代码版本或文档")
        inputs = _object(raw.get("evidence_identity")).get("dependencies", [])
        if not isinstance(inputs, list) or not all(_text(item) for item in inputs):
            raise ValueError("缺少源码检查输入")
        files = [self._source_file(item.replace("\\", "/")) for item in inputs]
        if (
            not {self.uiux, self.contract}.issubset(files)
            or _object(raw.get("producer")).get("kind") != "source_checker"
        ):
            raise ValueError("源码检查缺少必需输入")
        for path in files:
            self._bytes(path)
        return self._checked_result(
            SOURCE,
            EvidenceStatus(raw.get("status")),
            _text(raw.get("reason")),
            _text(raw.get("detail")),
            raw,
            files,
        )

    def result(self, kind: str) -> UIResult:
        if kind not in self._results:
            self._results[kind] = self._load(kind)
        return self._results[kind]

    def _load(self, kind: str) -> UIResult:
        if not self.required:
            return UIResult(kind, EvidenceStatus.NOT_APPLICABLE, "non_ui", "本工作不要求 UI 验收。")
        path = self.path(kind)
        if not path.is_file():
            return UIResult(
                kind, EvidenceStatus.BLOCKED, "missing", f"未取得当前的{LABELS[kind]}证据。"
            )
        try:
            raw = self._json(self._file(f"output/{path.name}"))
            if raw.get("kind") != kind or raw.get("schema_version") != 1:
                return UIResult(
                    kind,
                    EvidenceStatus.BLOCKED,
                    "legacy",
                    "旧报告不支持当前验收；不能由源码扫描或旧像素判断推定通过。",
                    path,
                )
            result = (
                self._load_source(raw)
                if kind == SOURCE
                else self._record_payload(kind, _object(raw.get("record")))
            )
            identity = self._identity(result)
            envelope = EvidenceEnvelope.from_dict(_object(raw.get("evidence_envelope")))
            if (
                not evidence_identity_matches(raw, expected=identity)[0]
                or envelope.evidence_type != kind
                or envelope.status is not result.status
                or raw.get("status") != result.status.value
                or result.status is EvidenceStatus.NOT_APPLICABLE
                or not envelope.matches_candidate(
                    work_item_id=identity["work_item_id"],
                    candidate_digest=identity["candidate_digest"],
                )
                or envelope.run_id != result.payload["run_id"]
                or envelope.producer != result.payload["producer"]["id"]
            ):
                raise ValueError("证据信封、内容或输入摘要已失效")
            return result
        except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            message = str(exc) if type(exc) is ValueError else "证据不可读取或格式不完整"
            return UIResult(kind, EvidenceStatus.BLOCKED, "invalid", message, path)

    def results(self, *, source: UIResult | None = None) -> tuple[UIResult, ...]:
        return (source or self.result(SOURCE), self.result(RUNTIME), self.result(VISUAL))

    def dependency_paths(self) -> list[Path]:
        """Bind reports to the current UI inputs and verified local references."""
        if not self.required:
            return []
        paths = [
            self.uiux,
            self.contract,
            self.output / f"{self.prefix}-ui-review.json",
            self.output / f"{self.prefix}-ui-contract-alignment.json",
        ]
        for result in self.results():
            if result.path is not None:
                paths.append(result.path)
            paths.extend(result.dependencies)
        return [path for path in dict.fromkeys(paths) if path.is_file() and path.resolve() == path]
