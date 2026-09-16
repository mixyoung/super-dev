"""
外部代码审查结果集成器

开发：Excellent（11964948@qq.com）
功能：读取 CodeRabbit / Qodo / GitHub PR 审查结果，纳入 quality gate 评分。
创建时间：2026-03-28
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..artifact_utils import resolve_work_item_identity
from ..config import ConfigManager
from ..delivery_facts import resolve_project_target_version
from ..experts.review_protocol import ReviewExecutionEvidence
from ..extensions.evidence import build_candidate_identity

_logger = logging.getLogger("super_dev.reviewers.external_reviews")


@dataclass
class ExternalReviewResult:
    """单个外部审查结果"""

    source: str  # "coderabbit" / "qodo" / "github_pr" / "custom"
    passed: bool
    score: int  # 0-100
    issues_count: int
    critical_count: int
    summary: str
    details: list[dict] = field(default_factory=list)  # 具体问题列表
    raw_path: str = ""  # 原始文件路径
    review_execution: ReviewExecutionEvidence | None = None

    @property
    def independence(self) -> str:
        return self.review_execution.classification if self.review_execution else "unverified"


class ExternalReviewCollector:
    """外部审查结果收集器

    支持从以下来源收集审查结果:
    - CodeRabbit: .coderabbit/ 目录或 output/*-coderabbit-review.json
    - Qodo PR-Agent: .qodo/ 目录或 output/*-qodo-review.json
    - GitHub PR: .github/pr-reviews/ 目录
    - 自定义: output/external-reviews/*.json
    """

    def __init__(
        self,
        project_dir: Path,
        *,
        attested_review_files: dict[str, str] | None = None,
        high_risk: bool = False,
        residual_risk_accepted: bool = False,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.attested_review_files = {
            str(session_id).strip(): str(digest).strip().lower().removeprefix("sha256:")
            for session_id, digest in (attested_review_files or {}).items()
            if str(session_id).strip() and str(digest).strip()
        }
        identity = resolve_work_item_identity(self.project_dir)
        self.current_work_item_id = identity.work_item_id if identity.valid else ""
        config = ConfigManager(self.project_dir).load()
        self.current_target_version = resolve_project_target_version(
            self.project_dir, configured_version=str(config.version or "")
        )
        self.current_candidate_digest = build_candidate_identity(self.project_dir).candidate_digest
        self.high_risk = high_risk
        self.residual_risk_accepted = residual_risk_accepted

    def _review_execution(self, data: dict, *, path: Path) -> ReviewExecutionEvidence | None:
        payload = data.get("review_execution", data.get("review_independence", {}))
        if not isinstance(payload, dict) or not payload:
            return None
        review_session_id = str(payload.get("review_session_id", "")).strip()
        work_item_id = str(payload.get("work_item_id", "")).strip()
        target_version = str(payload.get("target_version", "")).strip()
        candidate_digest = str(payload.get("candidate_digest", "")).strip()
        try:
            review_file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            review_file_digest = ""
        attested_digest = self.attested_review_files.get(review_session_id, "")
        binding_matches = bool(
            review_session_id
            and attested_digest
            and review_file_digest == attested_digest
            and work_item_id
            and work_item_id == self.current_work_item_id
            and target_version
            and target_version == self.current_target_version
            and candidate_digest
            and candidate_digest == self.current_candidate_digest
        )
        readonly_scope = payload.get("readonly_scope", ())
        tool_evidence = payload.get("tool_evidence", ())
        return ReviewExecutionEvidence(
            review_session_id=review_session_id,
            producer_session_id=str(payload.get("producer_session_id", "")),
            model=str(payload.get("model", "")),
            provider=str(payload.get("provider", "")),
            readonly_scope=tuple(
                str(item)
                for item in (readonly_scope if isinstance(readonly_scope, list | tuple) else ())
                if str(item).strip()
            ),
            tool_evidence=tuple(
                str(item)
                for item in (tool_evidence if isinstance(tool_evidence, list | tuple) else ())
                if str(item).strip()
            ),
            file_change_evidence=str(payload.get("file_change_evidence", "")),
            work_item_id=work_item_id,
            target_version=target_version,
            candidate_digest=candidate_digest,
            host_attested=binding_matches,
            attestation_evidence=(
                "caller-attested review file digest and current work item/version/candidate match"
                if binding_matches
                else "self-reported review metadata is not caller-attested for the current candidate"
            ),
            reviewer_model_family=str(payload.get("reviewer_model_family", "")),
            producer_model_family=str(payload.get("producer_model_family", "")),
            different_model_family_available=bool(
                payload.get("different_model_family_available", False)
            ),
            high_risk=self.high_risk,
            residual_risk_accepted=self.residual_risk_accepted,
        )

    def collect_all(self) -> list[ExternalReviewResult]:
        """收集所有外部审查结果"""
        results: list[ExternalReviewResult] = []
        results.extend(self._collect_coderabbit())
        results.extend(self._collect_qodo())
        results.extend(self._collect_github_pr())
        results.extend(self._collect_custom())
        return results

    def _collect_coderabbit(self) -> list[ExternalReviewResult]:
        """收集 CodeRabbit 审查结果

        查找路径:
        1. .coderabbit/reviews/*.json
        2. output/*-coderabbit-review.json
        """
        results: list[ExternalReviewResult] = []

        # 路径1: .coderabbit/reviews/
        coderabbit_dir = self.project_dir / ".coderabbit" / "reviews"
        if coderabbit_dir.is_dir():
            for path in sorted(coderabbit_dir.glob("*.json")):
                result = self._parse_coderabbit_file(path)
                if result is not None:
                    results.append(result)

        # 路径2: output/*-coderabbit-review.json
        if self.output_dir.is_dir():
            for path in sorted(self.output_dir.glob("*-coderabbit-review.json")):
                result = self._parse_coderabbit_file(path)
                if result is not None:
                    results.append(result)

        return results

    def _parse_coderabbit_file(self, path: Path) -> ExternalReviewResult | None:
        """解析 CodeRabbit 审查结果文件"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            issues = data.get("issues", [])
            critical = [i for i in issues if i.get("severity") in ("critical", "high")]
            score = data.get("score", self._score_from_issues(len(issues), len(critical)))
            passed = data.get("passed", len(critical) == 0)
            return ExternalReviewResult(
                source="coderabbit",
                passed=passed,
                score=score,
                issues_count=len(issues),
                critical_count=len(critical),
                summary=data.get("summary", f"CodeRabbit: {len(issues)} issues found"),
                details=issues,
                raw_path=str(path),
                review_execution=self._review_execution(data, path=path),
            )
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            _logger.warning("Failed to parse CodeRabbit file %s: %s", path, exc)
            return None

    def _collect_qodo(self) -> list[ExternalReviewResult]:
        """收集 Qodo PR-Agent 审查结果

        查找路径:
        1. .qodo/reviews/*.json
        2. output/*-qodo-review.json
        """
        results: list[ExternalReviewResult] = []

        # 路径1: .qodo/reviews/
        qodo_dir = self.project_dir / ".qodo" / "reviews"
        if qodo_dir.is_dir():
            for path in sorted(qodo_dir.glob("*.json")):
                result = self._parse_qodo_file(path)
                if result is not None:
                    results.append(result)

        # 路径2: output/*-qodo-review.json
        if self.output_dir.is_dir():
            for path in sorted(self.output_dir.glob("*-qodo-review.json")):
                result = self._parse_qodo_file(path)
                if result is not None:
                    results.append(result)

        return results

    def _parse_qodo_file(self, path: Path) -> ExternalReviewResult | None:
        """解析 Qodo PR-Agent 审查结果文件"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            issues = data.get("issues", data.get("comments", []))
            critical = [
                i
                for i in issues
                if i.get("severity") in ("critical", "high") or i.get("category") == "bug"
            ]
            score = data.get("score", self._score_from_issues(len(issues), len(critical)))
            passed = data.get("passed", len(critical) == 0)
            return ExternalReviewResult(
                source="qodo",
                passed=passed,
                score=score,
                issues_count=len(issues),
                critical_count=len(critical),
                summary=data.get("summary", f"Qodo: {len(issues)} issues found"),
                details=issues,
                raw_path=str(path),
                review_execution=self._review_execution(data, path=path),
            )
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            _logger.warning("Failed to parse Qodo file %s: %s", path, exc)
            return None

    def _collect_github_pr(self) -> list[ExternalReviewResult]:
        """收集 GitHub PR 审查状态

        查找路径:
        1. .github/pr-reviews/*.json
        2. output/*-github-pr-review.json
        """
        results: list[ExternalReviewResult] = []

        # 路径1: .github/pr-reviews/
        pr_dir = self.project_dir / ".github" / "pr-reviews"
        if pr_dir.is_dir():
            for path in sorted(pr_dir.glob("*.json")):
                result = self._parse_github_pr_file(path)
                if result is not None:
                    results.append(result)

        # 路径2: output/*-github-pr-review.json
        if self.output_dir.is_dir():
            for path in sorted(self.output_dir.glob("*-github-pr-review.json")):
                result = self._parse_github_pr_file(path)
                if result is not None:
                    results.append(result)

        return results

    def _parse_github_pr_file(self, path: Path) -> ExternalReviewResult | None:
        """解析 GitHub PR 审查结果文件"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            comments = data.get("comments", data.get("reviews", []))
            # GitHub PR reviews: "APPROVED", "CHANGES_REQUESTED", "COMMENTED"
            state = data.get("state", "").upper()
            changes_requested = [
                c for c in comments if c.get("state", "").upper() == "CHANGES_REQUESTED"
            ]
            issues_count = len(comments)
            critical_count = len(changes_requested)
            passed = state == "APPROVED" or (not changes_requested and state != "CHANGES_REQUESTED")
            score = data.get("score", 90 if passed else max(40, 90 - critical_count * 15))
            return ExternalReviewResult(
                source="github_pr",
                passed=passed,
                score=score,
                issues_count=issues_count,
                critical_count=critical_count,
                summary=data.get(
                    "summary",
                    f"GitHub PR: {state or 'PENDING'} ({issues_count} comments)",
                ),
                details=comments,
                raw_path=str(path),
                review_execution=self._review_execution(data, path=path),
            )
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            _logger.warning("Failed to parse GitHub PR file %s: %s", path, exc)
            return None

    def _collect_custom(self) -> list[ExternalReviewResult]:
        """收集自定义审查结果

        查找路径: output/external-reviews/*.json

        自定义文件格式:
        {
            "source": "my-tool",
            "passed": true,
            "score": 85,
            "issues_count": 3,
            "critical_count": 0,
            "summary": "...",
            "details": [...]
        }
        """
        results: list[ExternalReviewResult] = []
        custom_dir = self.output_dir / "external-reviews"
        if not custom_dir.is_dir():
            return results

        for path in sorted(custom_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                source = data.get("source", "custom")
                issues_count = data.get("issues_count", 0)
                critical_count = data.get("critical_count", 0)
                passed = data.get("passed", critical_count == 0)
                score = data.get(
                    "score",
                    self._score_from_issues(issues_count, critical_count),
                )
                results.append(
                    ExternalReviewResult(
                        source=source,
                        passed=passed,
                        score=score,
                        issues_count=issues_count,
                        critical_count=critical_count,
                        summary=data.get("summary", f"{source}: {issues_count} issues"),
                        details=data.get("details", []),
                        raw_path=str(path),
                        review_execution=self._review_execution(data, path=path),
                    )
                )
            except (json.JSONDecodeError, TypeError, KeyError) as exc:
                _logger.warning("Failed to parse custom review file %s: %s", path, exc)

        return results

    def generate_summary(self, results: list[ExternalReviewResult]) -> str:
        """生成汇总 Markdown 报告"""
        if not results:
            return "## External Review Summary\n\nNo external review results found.\n"

        lines: list[str] = [
            "## External Review Summary",
            "",
            f"Total sources: {len(results)}",
            "",
            "| Source | Status | Independence | Score | Issues | Critical |",
            "|--------|--------|--------------|-------|--------|----------|",
        ]

        total_issues = 0
        total_critical = 0
        total_score = 0

        for r in results:
            status = "PASSED" if r.passed else "FAILED"
            lines.append(
                f"| {r.source} | {status} | {r.independence} | {r.score}/100 "
                f"| {r.issues_count} | {r.critical_count} |"
            )
            total_issues += r.issues_count
            total_critical += r.critical_count
            total_score += r.score

        avg_score = total_score // len(results) if results else 0
        lines.extend(
            [
                "",
                f"**Average Score**: {avg_score}/100",
                f"**Total Issues**: {total_issues} ({total_critical} critical)",
                "",
            ]
        )

        # 详细问题列表
        all_details = [(r.source, detail) for r in results for detail in r.details]
        if all_details:
            lines.extend(["### Issue Details", ""])
            for source, detail in all_details[:20]:  # 最多显示 20 条
                msg = detail.get("message", detail.get("body", str(detail)))
                severity = detail.get("severity", "info")
                lines.append(f"- **[{source}]** ({severity}) {msg}")
            if len(all_details) > 20:
                lines.append(f"- ... and {len(all_details) - 20} more")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _score_from_issues(issues_count: int, critical_count: int) -> int:
        """根据问题数量估算分数"""
        score = 100
        score -= critical_count * 15
        score -= (issues_count - critical_count) * 5
        return max(0, min(100, score))
