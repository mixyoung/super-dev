"""Unit tests for ParkingLotRegister, CLI/Web endpoints, StateStore & SessionBrief sync."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from super_dev.cli import SuperDevCLI
from super_dev.deployers.delivery import DeliveryPackager
from super_dev.enforcement.pre_code_gate import PreCodeGate
from super_dev.host_workflow_context import build_host_workflow_context
from super_dev.integrations import IntegrationManager
from super_dev.parking_lot import (
    ParkingLotItem,
    ParkingLotRegister,
    scan_core_docs_for_untracked_deferrals,
    summarize_parking_lot,
)
from super_dev.release_readiness import ReleaseReadinessEvaluator
from super_dev.reviewers.fresh_verification_evidence import quality_evidence_dependency_paths
from super_dev.reviewers.quality_gate import CheckStatus, QualityGateChecker
from super_dev.session.brief import SessionBrief
from super_dev.specs.generator import SpecGenerator
from super_dev.state_store import StateStore
from super_dev.web.api import app
from super_dev.work_item_identity import start_standard_work_item
from super_dev.workflow_guard import (
    WorkflowGateError,
    docs_gate_status,
    require_docs_confirmation,
    save_bound_docs_confirmation,
)


def test_parking_lot_item_dict_serialization() -> None:
    item = ParkingLotItem(
        id="PARK-001",
        title="缓存架构重构",
        reason_for_deferral="并发低，避免过早引入 Redis",
        revisit_trigger="QPS 超过 200",
        current_compromise="进程内 LRU 内存缓存",
        affected_components=["api/cache.py", "services/user.py"],
    )
    d = item.to_dict()
    assert d["id"] == "PARK-001"
    assert d["status"] == "pending"

    restored = ParkingLotItem.from_dict(d)
    assert restored.id == "PARK-001"
    assert restored.affected_components == ["api/cache.py", "services/user.py"]


def test_parking_lot_register_save_load_and_id_monotonic(tmp_path: Path) -> None:
    reg = ParkingLotRegister()
    it1 = reg.add_item(
        title="支付网关沙箱切换",
        reason_for_deferral="沙箱联调账号未审批",
        revisit_trigger="收到测试密钥",
        current_compromise="使用 MockPaymentGateway",
        affected_components=["payments/gateway.py"],
    )
    assert it1.id == "PARK-001"
    reg.items.append(
        ParkingLotItem(
            id="PARK-005",
            title="跳号历史项",
            reason_for_deferral="历史保留",
            revisit_trigger="Q3 评审",
            current_compromise="维持现状",
        )
    )
    it2 = reg.add_item("后续项", "原因", "条件", "折衷")
    assert it2.id == "PARK-006"

    saved_path = reg.save(tmp_path)
    assert saved_path.exists()

    loaded = ParkingLotRegister.load(tmp_path)
    assert len(loaded.items) == 3
    assert loaded.items[0].title == "支付网关沙箱切换"


def test_parking_lot_resolve_with_target_and_open_items() -> None:
    reg = ParkingLotRegister()
    reg.add_item("任务A", "理由A", "条件A", "折衷A")
    reg.add_item("任务B", "理由B", "条件B", "折衷B")

    assert len(reg.get_open_items()) == 2
    success = reg.resolve_item(
        "PARK-001",
        resolution_notes="已在 PR #10 引入并压测通过",
        resolved_target="output/demo-architecture.md",
    )
    assert success is True

    open_items = reg.get_open_items()
    assert len(open_items) == 1
    assert open_items[0].id == "PARK-002"
    assert reg.items[0].status == "resolved"
    assert reg.items[0].resolved_target == "output/demo-architecture.md"
    assert "PR #10" in reg.items[0].resolution_notes


def test_parking_lot_markdown_rendering() -> None:
    reg = ParkingLotRegister()
    assert reg.render_markdown_table() == "当前无挂起的未决决策或技术妥协。"

    reg.add_item("分库分表规划", "数据量小于 500 万行", "单表达到 300 万行时启动评估", "单表加适度索引")
    table = reg.render_markdown_table()
    assert "| `PARK-001` | 分库分表规划 |" in table
    assert "单表达到 300 万行时启动评估" in table


def test_parking_lot_compliance_validation() -> None:
    reg = ParkingLotRegister()
    reg.add_item("完整项", "清晰原因", "明确触发条件", "清晰妥协方案")
    assert reg.validate_compliance() == []

    reg.add_item("敷衍项", "TBD", "待定", "暂无")
    violations = reg.validate_compliance()
    assert len(violations) >= 3


def test_session_brief_and_state_store_preserve_health_with_parking_lot(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.commit_workflow(
        {
            "work_item_id": "demo-work",
            "artifact_prefix": "demo",
            "binding_status": "pre_spec",
            "active_change_id": "",
            "status": "docs",
        }
    )

    reg = ParkingLotRegister()
    reg.add_item("微服务拆分", "业务模式尚在探索期", "团队规模超过 15 人", "单体模块化架构")
    reg.save(tmp_path)

    SessionBrief.sync_parking_lot(tmp_path)
    assert store.session_brief_health()["current"] is True
    brief_text = (tmp_path / ".super-dev" / "SESSION_BRIEF.md").read_text(encoding="utf-8")
    assert "来源工作项: demo-work" in brief_text
    assert "## Open Decisions" in brief_text
    assert "微服务拆分" in brief_text

    # StateStore 后续提交继续保留 Open Decisions
    current = store.load_workflow()
    store.commit_workflow({**current, "status": "spec"}, expected_revision=current["revision"])
    brief_after = (tmp_path / ".super-dev" / "SESSION_BRIEF.md").read_text(encoding="utf-8")
    assert "微服务拆分" in brief_after
    assert store.session_brief_health()["current"] is True


def test_cli_parking_add_list_resolve_and_check(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()

    rc_bad = cli.run(
        [
            "parking",
            "add",
            "--title",
            "占位项",
            "--reason",
            "TBD",
            "--trigger",
            "待定",
            "--compromise",
            "暂无",
            "--json",
        ]
    )
    assert rc_bad == 1
    bad = json.loads(capsys.readouterr().out)
    assert bad["ok"] is False

    rc_add = cli.run(
        [
            "parking",
            "add",
            "--title",
            "读写分离延后",
            "--reason",
            "日活低于 5000",
            "--trigger",
            "主库 CPU 连续一周超过 65%",
            "--compromise",
            "单主库 + 连接池限制",
            "--components",
            "db/pool.py,api/orders.py",
            "--json",
        ]
    )
    assert rc_add == 0
    added = json.loads(capsys.readouterr().out)
    assert added["ok"] is True
    assert added["item"]["id"] == "PARK-001"
    assert (tmp_path / ".super-dev" / "SESSION_BRIEF.md").exists()

    rc_list = cli.run(["parking", "list", "--json"])
    assert rc_list == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["open_count"] == 1

    # 未传入 --target 或目标文件不存在时必须被硬拒绝
    rc_missing_target = cli.run(
        ["parking", "resolve", "PARK-001", "--notes", "未写核心文档就尝试关闭", "--json"]
    )
    assert rc_missing_target == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False

    rc_nonexistent_target = cli.run(
        [
            "parking",
            "resolve",
            "PARK-001",
            "--notes",
            "指向不存在的文档",
            "--target",
            "output/demo-architecture.md",
            "--json",
        ]
    )
    assert rc_nonexistent_target == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False

    arch_doc = tmp_path / "output" / "demo-architecture.md"
    arch_doc.parent.mkdir(parents=True, exist_ok=True)
    arch_doc.write_text("# Demo Architecture\n\n## 读写分离定论\n已启用只读副本。\n", encoding="utf-8")

    rc_resolve = cli.run(
        [
            "parking",
            "resolve",
            "PARK-001",
            "--notes",
            "已上线只读副本并更新架构定论",
            "--target",
            "output/demo-architecture.md#读写分离定论",
            "--json",
        ]
    )
    assert rc_resolve == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["item"]["status"] == "resolved"
    assert resolved["item"]["resolved_target"] == "output/demo-architecture.md#读写分离定论"

    rc_check = cli.run(["parking", "check", "--strict-delivery", "--json"])
    assert rc_check == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["passed"] is True
    assert checked["open_count"] == 0


def test_web_api_parking_lot_read_and_write_lifecycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUPER_DEV_API_KEY", "test-parking-key")
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(Path(tempfile.gettempdir()).resolve()))
    client = TestClient(app)

    res_empty = client.get("/api/parking-lot", params={"project_dir": str(tmp_path)})
    assert res_empty.status_code == 200
    assert res_empty.json()["exists"] is False
    assert res_empty.json()["open_count"] == 0

    res_unauth = client.post(
        "/api/v1/parking-lot",
        params={"project_dir": str(tmp_path)},
        json={
            "title": "未鉴权请求测试",
            "reason_for_deferral": "检查 API Key 保护",
            "revisit_trigger": "接口未携带凭证时触发",
            "current_compromise": "拒绝写入",
        },
    )
    assert res_unauth.status_code == 401

    headers = {"X-Super-Dev-Key": "test-parking-key"}
    res_add = client.post(
        "/api/v1/parking-lot",
        params={"project_dir": str(tmp_path)},
        headers=headers,
        json={
            "title": "搜索引擎选型延后",
            "reason_for_deferral": "当前数据量低于 10 万条",
            "revisit_trigger": "模糊检索 P95 延迟超过 300ms",
            "current_compromise": "PostgreSQL GIN 全文索引",
            "affected_components": ["search/query.py"],
            "blocks_delivery": True,
        },
    )
    assert res_add.status_code == 200
    body = res_add.json()
    assert body["open_count"] == 1
    assert body["blocking_open_count"] == 1
    assert body["created_item"]["id"] == "PARK-001"
    assert (tmp_path / ".super-dev" / "SESSION_BRIEF.md").exists()

    # 目标核心文档尚未落盘时，API resolve 必须返回 400
    res_bad_resolve = client.post(
        "/api/parking-lot/PARK-001/resolve",
        params={"project_dir": str(tmp_path)},
        headers=headers,
        json={
            "resolution_notes": "接入 Meilisearch 并在架构文档定稿",
            "resolved_target": "output/demo-architecture.md",
        },
    )
    assert res_bad_resolve.status_code == 400

    arch_doc = tmp_path / "output" / "demo-architecture.md"
    arch_doc.parent.mkdir(parents=True, exist_ok=True)
    arch_doc.write_text("# Architecture\n\n## 搜索选型\n采用 Meilisearch。\n", encoding="utf-8")

    res_resolve = client.post(
        "/api/parking-lot/PARK-001/resolve",
        params={"project_dir": str(tmp_path)},
        headers=headers,
        json={
            "resolution_notes": "接入 Meilisearch 并在架构文档定稿",
            "resolved_target": "output/demo-architecture.md",
        },
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["open_count"] == 0
    assert res_resolve.json()["blocking_open_count"] == 0
    assert res_resolve.json()["resolved_item"]["status"] == "resolved"


def test_parking_lot_resolve_hard_rejects_invalid_and_self_referential_targets(
    tmp_path: Path,
) -> None:
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)
    (tmp_path / "output" / "demo-prd.md").write_text("# PRD\n\n已冻结主流程。\n", encoding="utf-8")
    (tmp_path / "output" / "empty.md").write_text("   \n", encoding="utf-8")

    reg = ParkingLotRegister()
    reg.add_item("限流阈值标定", "压测环境未就绪", "完成全链路压测", "保守限流 100 RPS")
    reg.save(tmp_path)
    SessionBrief.sync_parking_lot(tmp_path)

    with pytest.raises(ValueError, match="resolved_target"):
        reg.resolve_item("PARK-001", resolution_notes="完成", resolved_target="")

    with pytest.raises(ValueError, match="账本或简报"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="回指账本",
            resolved_target=".super-dev/parking-lot.json",
            project_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="账本或简报"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="回指简报",
            resolved_target=".super-dev/SESSION_BRIEF.md",
            project_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="内容为空"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="目标空文件",
            resolved_target="output/empty.md",
            project_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="非法父级跳转"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="越权路径",
            resolved_target="../outside.md",
            project_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="超出项目根目录"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="绝对越权路径",
            resolved_target=str(tmp_path.parent / "outside.md"),
            project_dir=tmp_path,
        )

    assert (
        reg.resolve_item(
            "PARK-001",
            resolution_notes="压测完成并写入 PRD",
            resolved_target="output/demo-prd.md",
            project_dir=tmp_path,
        )
        is True
    )
    assert reg.validate_compliance(project_dir=tmp_path, require_no_blocking_open=True) == []


def test_quality_gate_hard_fails_on_parking_lot_violations_and_tracks_dependency(
    tmp_path: Path,
) -> None:
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)
    for suffix, content in (
        ("prd", "# PRD\n\n## 联网研究证据与方案对比\n## 关键决策账本\n## 用户到专业交付统一协议\n" + "内容\n" * 60),
        ("architecture", "# Arch\n\n## 架构选型取舍与证据链\n## 架构决策账本\n## Agent 执行流水线（全端）\n" + "内容\n" * 60),
        ("uiux", "# UX\n\n无前端使用说明。\n" + "内容\n" * 40),
    ):
        (tmp_path / "output" / f"demo-{suffix}.md").write_text(content, encoding="utf-8")

    # 1. 合法的非阻塞未决项 + 已真实回写的解除项 -> QualityGate 未决事项检查为 PASSED
    reg = ParkingLotRegister()
    reg.add_item("多区容灾延后", "单区流量足够", "月活过 50 万", "单区多可用区备份", blocks_delivery=False)
    it2 = reg.add_item("缓存穿透兜底", "需压测确认", "发布前", "临时本地限流", blocks_delivery=True)
    reg.resolve_item(
        it2.id,
        resolution_notes="已定稿空值缓存 60s 方案并写入架构文档",
        resolved_target="output/demo-architecture.md",
        project_dir=tmp_path,
    )
    reg.save(tmp_path)

    deps = quality_evidence_dependency_paths(tmp_path, project_name="demo", frontend_required=False)
    assert (tmp_path / ".super-dev" / "parking-lot.json") in deps

    checker = QualityGateChecker(
        tmp_path,
        name="demo",
        tech_stack={"platform": "cli", "frontend": "none", "backend": "python"},
        threshold_override=0,
    )
    ok_checks = [c for c in checker._check_documentation() if c.name == "未决事项登记簿"]
    assert len(ok_checks) == 1
    assert ok_checks[0].status == CheckStatus.PASSED

    # 2. 加入一条标记 blocks_delivery=True 的未决项 -> QualityGate 必须硬失败（critical_failures + passed=False）
    reg.add_item("支付验签开关待定", "联调未结束", "上线前冻结", "仅日志告警", blocks_delivery=True)
    reg.save(tmp_path)

    gate_blocked = checker.check()
    parking_checks = [c for c in gate_blocked.checks if c.name == "未决事项登记簿"]
    assert parking_checks[0].status == CheckStatus.FAILED
    assert gate_blocked.passed is False
    assert any("[documentation]" in f for f in gate_blocked.critical_failures)

    # 3. 损坏 JSON 也不允许静默放过
    (tmp_path / ".super-dev" / "parking-lot.json").write_text("{broken json", encoding="utf-8")
    gate_corrupt = checker.check()
    assert gate_corrupt.passed is False
    assert [c for c in gate_corrupt.checks if c.name == "未决事项登记簿"][0].status == CheckStatus.FAILED


def test_delivery_and_release_readiness_enforce_parking_lot_hard_gate(tmp_path: Path) -> None:
    (tmp_path / "super-dev.yaml").write_text(
        "name: demo\nplatform: cli\nfrontend: none\nbackend: python\ndatabase: none\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in (
        "research.md",
        "prd.md",
        "architecture.md",
        "uiux.md",
        "redteam.md",
        "quality-gate.md",
        "task-execution.md",
    ):
        (output_dir / f"demo-{suffix}").write_text(f"# {suffix}\n\nok\n", encoding="utf-8")
    task_file = tmp_path / ".super-dev" / "changes" / "demo" / "tasks.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("# Tasks\n\n- [x] **1.1: done**\n", encoding="utf-8")

    # 写入一条缺少真实回写文档的假 resolved 项 -> DeliveryPackager 与 ReleaseReadiness 均须硬拒绝
    bad_reg = ParkingLotRegister(
        items=[
            ParkingLotItem(
                id="PARK-001",
                title="鉴权策略",
                reason_for_deferral="待确认",
                revisit_trigger="发布前",
                current_compromise="单 Token",
                status="resolved",
                resolution_notes="已口头确认",
                resolved_target="output/missing-doc.md",
            )
        ]
    )
    bad_reg.save(tmp_path)

    pkg_blocked = DeliveryPackager(project_dir=tmp_path, name="demo", version="2.6.0").package(
        cicd_platform="all"
    )
    assert pkg_blocked["status"] == "incomplete"
    assert any(
        isinstance(item, dict) and item.get("path") == ".super-dev/parking-lot.json"
        for item in pkg_blocked["missing_required"]
    )

    closure = ReleaseReadinessEvaluator(tmp_path)._check_delivery_closure(
        include_fresh_verification=False
    )
    assert closure.passed is False
    assert "parking lot gate failed" in closure.detail

    # 回写真实核心文档并恢复合规后，DeliveryPackager 放行且纳入 parking-lot.json
    bad_reg.resolve_item(
        "PARK-001",
        resolution_notes="已将最终鉴权方案写回架构文档",
        resolved_target="output/demo-architecture.md",
        project_dir=tmp_path,
    )
    bad_reg.save(tmp_path)

    pkg_ready = DeliveryPackager(project_dir=tmp_path, name="demo", version="2.6.0").package(
        cicd_platform="all"
    )
    assert pkg_ready["status"] == "ready"
    manifest = json.loads(Path(str(pkg_ready["manifest_file"])).read_text(encoding="utf-8"))
    assert ".super-dev/parking-lot.json" in {
        item.replace("\\", "/") for item in manifest["included_files"]
    }


def test_resolve_requires_actual_doc_change_anchor_and_doc_extension(tmp_path: Path) -> None:
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)
    arch_doc = tmp_path / "output" / "demo-architecture.md"
    arch_doc.write_text("# Demo Architecture\n\n## 当前基线\n使用单体结构。\n", encoding="utf-8")
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

    reg = ParkingLotRegister()
    reg.add_item(
        "缓存拆分时机",
        "当前单机 QPS 低于 200",
        "峰值 QPS > 1000",
        "本地 LRU 缓存",
        project_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="必须是文档文件"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="写入源码不算文档定论",
            resolved_target="src/main.py",
            project_dir=tmp_path,
        )

    # 核心文档自 add 以来只字未改 -> 拒绝空转关闭
    with pytest.raises(ValueError, match="未发生内容更新"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="假装已写回架构文档",
            resolved_target="output/demo-architecture.md",
            project_dir=tmp_path,
        )

    # 更新核心文档后，再校验不存在的锚点 -> 拒绝假锚点
    arch_doc.write_text(
        "# Demo Architecture\n\n## 当前基线\n使用单体结构。\n\n## 缓存定论\n已切换到 Redis Cluster。\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="锚点不存在"):
        reg.resolve_item(
            "PARK-001",
            resolution_notes="写入不存在的锚点",
            resolved_target="output/demo-architecture.md#不存在章节",
            project_dir=tmp_path,
        )

    assert (
        reg.resolve_item(
            "PARK-001",
            resolution_notes="已将 Redis Cluster 方案写入缓存定论章节",
            resolved_target="output/demo-architecture.md#缓存定论",
            project_dir=tmp_path,
        )
        is True
    )
    assert reg.items[0].resolved_target_digest
    assert arch_doc.resolve() in reg.get_resolved_target_paths(tmp_path)

    reg.save(tmp_path)
    deps = quality_evidence_dependency_paths(tmp_path, project_name="demo", frontend_required=False)
    assert arch_doc.resolve() in deps


def test_core_doc_untracked_deferral_leak_blocks_quality_gate_without_parking_lot(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    prd = output_dir / "demo-prd.md"
    arch = output_dir / "demo-architecture.md"
    ux = output_dir / "demo-uiux.md"

    prd.write_text(
        "# PRD\n\n## 联网研究证据与方案对比\n## 关键决策账本\n## 用户到专业交付统一协议\n"
        "- 权限模型：待定（先用临时妥协方案应付演示）\n"
        + "正文\n" * 60,
        encoding="utf-8",
    )
    arch.write_text(
        "# Arch\n\n## 架构选型取舍与证据链\n## 架构决策账本\n## Agent 执行流水线（全端）\n"
        "```python\n# TODO inside code block must be ignored\n```\n"
        "- 数据分片策略：TBD\n"
        + "架构\n" * 60,
        encoding="utf-8",
    )
    ux.write_text("# UX\n\n无前端使用说明。\n" + "内容\n" * 40, encoding="utf-8")

    leaks = scan_core_docs_for_untracked_deferrals(tmp_path, artifact_prefix="demo")
    assert len(leaks) == 2
    assert all("TODO inside code block" not in item["snippet"] for item in leaks)

    # 即便 .super-dev/parking-lot.json 压根不存在，QualityGate 与 CLI check 也必须拦截泄漏
    cli = SuperDevCLI()
    assert cli.run(["parking", "check", "--json"]) == 1
    check_payload = json.loads(capsys.readouterr().out)
    assert check_payload["passed"] is False
    assert len(check_payload["core_doc_leaks"]) == 2

    checker = QualityGateChecker(
        tmp_path,
        name="demo",
        tech_stack={"platform": "cli", "frontend": "none", "backend": "python"},
        threshold_override=0,
    )
    gate_res = checker.check()
    assert gate_res.passed is False
    assert [c for c in gate_res.checks if c.name == "未决事项登记簿"][0].status == CheckStatus.FAILED
    assert any("挂起决策硬门禁" in failure for failure in gate_res.critical_failures)

    # 把未决项移入第二账本并清理核心文档后，再次评估通过
    prd.write_text(
        "# PRD\n\n## 产品愿景\n## 功能需求\n## 验收标准\n- Given 权限角色 When 访问接口 Then 校验 RBAC。\n"
        "## 联网研究证据与方案对比\n## 关键决策账本\n## 用户到专业交付统一协议\n"
        "- 权限模型：暂定（见 `.super-dev/parking-lot.json` (`PARK-001`)）。\n"
        + "正文\n" * 60,
        encoding="utf-8",
    )
    arch.write_text(
        "# Arch\n\n## 架构选型取舍与证据链\n## 架构决策账本\n## Agent 执行流水线（全端）\n"
        "- 当前使用单主库模式。\n"
        "```yaml\ndatabase: single-primary\n```\n"
        + "架构\n" * 60,
        encoding="utf-8",
    )
    reg = ParkingLotRegister()
    reg.add_item("权限与分片演进", "MVP 阶段单租户为主", "企业客户突破 20 家", "RBAC 基础角色表", project_dir=tmp_path)
    reg.save(tmp_path)

    assert summarize_parking_lot(tmp_path, artifact_prefix="demo")["passed"] is True
    assert cli.run(["parking", "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
    clean_doc_checks = [c for c in checker._check_documentation() if c.name == "未决事项登记簿"]
    assert len(clean_doc_checks) == 1
    assert clean_doc_checks[0].status == CheckStatus.PASSED
    gate_after_fix = checker.check()
    assert not any("挂起决策硬门禁" in failure for failure in gate_after_fix.critical_failures)


def test_workflow_guard_and_host_workflow_context_surface_and_enforce_parking_lot(
    tmp_path: Path,
) -> None:
    (tmp_path / "super-dev.yaml").write_text(
        "name: demo\nplatform: cli\nfrontend: none\nbackend: python\ndatabase: none\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    prd = output_dir / "demo-prd.md"
    arch = output_dir / "demo-architecture.md"
    ux = output_dir / "demo-uiux.md"
    prd.write_text("# PRD\n\n- 支付通道: [待定]\n", encoding="utf-8")
    arch.write_text("# Arch\n\n单进程服务。\n", encoding="utf-8")
    ux.write_text("# UX\n\nCLI 输出。\n", encoding="utf-8")

    # 1. 核心文档有未入账待定时，不允许通过确认门，且 host_workflow_context 暴露阻断
    with pytest.raises(WorkflowGateError) as exc_info:
        save_bound_docs_confirmation(
            tmp_path,
            {"status": "confirmed", "actor": "user", "comment": "尝试跳过检查确认"},
        )
    assert exc_info.value.gate == "parking_lot"

    ctx_blocked = build_host_workflow_context(tmp_path)
    assert ctx_blocked["parking_lot"]["passed"] is False
    assert len(ctx_blocked["parking_lot"]["core_doc_leaks"]) == 1

    # 2. 清理泄漏并正常登记后，允许确认文档；若确认后有人损坏账本，docs_gate_status 与 require_docs_confirmation 立即拦截
    prd.write_text("# PRD\n\n仅记录已冻结定论。\n", encoding="utf-8")
    reg = ParkingLotRegister()
    reg.add_item("支付通道选型", "商户号审批中", "商户号下发", "Sandbox 模拟器", project_dir=tmp_path)
    reg.save(tmp_path)

    save_bound_docs_confirmation(
        tmp_path,
        {"status": "confirmed", "actor": "user", "comment": "核心文档纯净且第二账本合规"},
    )
    gate_ok = docs_gate_status(tmp_path)
    assert gate_ok["confirmed"] is True
    assert gate_ok["parking_lot"]["open_count"] == 1
    assert require_docs_confirmation(tmp_path, action="create_spec")["confirmed"] is True

    # 确认后再注入损坏 JSON -> 确认门失效、require_docs_confirmation 立即抛 WorkflowGateError(gate="parking_lot")
    (tmp_path / ".super-dev" / "parking-lot.json").write_text("{corrupt", encoding="utf-8")
    gate_tampered = docs_gate_status(tmp_path)
    assert gate_tampered["confirmed"] is False
    with pytest.raises(WorkflowGateError) as exc_tampered:
        require_docs_confirmation(tmp_path, action="create_spec")
    assert exc_tampered.value.gate == "parking_lot"

    ctx_tampered = build_host_workflow_context(tmp_path)
    assert ctx_tampered["parking_lot"]["passed"] is False
    assert ctx_tampered["blocking_gate"] == "waiting_parking_lot_closure"
    assert ctx_tampered["can_progress"] is False


def test_spec_create_and_scaffold_enforce_parking_lot_and_emit_checklist(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    generator = SpecGenerator(tmp_path)
    generator.init_sdd()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    prd = output_dir / "demo-prd.md"
    arch = output_dir / "demo-architecture.md"
    ux = output_dir / "demo-uiux.md"
    prd.write_text("# PRD\n\n- 支付通道：TBD（稍后补齐）\n", encoding="utf-8")
    arch.write_text("# Arch\n\n- 核心服务拆分已完成定稿。\n", encoding="utf-8")
    ux.write_text("# UX\n\n- 设计令牌与页面骨架已完成定稿。\n", encoding="utf-8")

    # Legacy Spec create_change path without bound confirmation must still block core doc leaks
    with pytest.raises(WorkflowGateError) as exc_legacy:
        generator.create_change("demo-chg", "Demo Change", "说明")
    assert exc_legacy.value.gate == "parking_lot"

    # CLI spec scaffold also blocks core doc leaks
    cli = SuperDevCLI()
    assert cli.run(["spec", "scaffold", "demo-chg"]) == 1
    assert "第二账本硬门禁" in capsys.readouterr().out

    # Bind change with clean docs and valid ledger, then test corrupt ledger interception
    prd.write_text(
        "# PRD\n\n- 支付通道：暂用沙箱适配器（见 `.super-dev/parking-lot.json` (`PARK-001`)）。\n",
        encoding="utf-8",
    )
    reg = ParkingLotRegister()
    reg.add_item("支付通道选型", "商户号审批中", "商户号下发", "沙箱适配器", project_dir=tmp_path)
    reg.save(tmp_path)

    start_standard_work_item(tmp_path, "demo")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    (tmp_path / ".super-dev" / "parking-lot.json").write_text("{corrupt", encoding="utf-8")

    with pytest.raises(WorkflowGateError) as exc_corrupt:
        generator.create_change("demo", "Demo Change", "说明")
    assert exc_corrupt.value.gate == "parking_lot"
    assert cli.run(["spec", "scaffold", "demo"]) == 1
    capsys.readouterr()

    # Restore valid ledger -> Spec create_change & scaffold succeed with Option 2 checklist rules
    reg.save(tmp_path)
    change = generator.create_change("demo", "Demo Change", "说明")
    assert change.id == "demo"
    assert cli.run(["spec", "scaffold", "demo"]) == 0
    capsys.readouterr()

    checklist_text = (
        tmp_path / ".super-dev" / "changes" / "demo" / "checklist.md"
    ).read_text(encoding="utf-8")
    assert "第二套账本交付阻塞项" in checklist_text
    assert ".super-dev/parking-lot.json" in checklist_text

    precode_checklist = PreCodeGate()._build_checklist(frontend="react", backend="python")
    assert "super-dev parking check" in precode_checklist
    assert ".super-dev/parking-lot.json" in precode_checklist


def test_integration_manager_host_surfaces_include_parking_lot_contract(tmp_path: Path) -> None:
    targets = (
        "cursor",
        "claude-code",
        "codex-cli",
        "antigravity",
        "trae",
        "windsurf",
        "kiro",
        "gemini-cli",
    )
    for target in targets:
        project_dir = tmp_path / target
        project_dir.mkdir(parents=True, exist_ok=True)
        files = IntegrationManager(project_dir).setup(target, force=True)
        texts = [
            f.read_text(encoding="utf-8")
            for f in files
            if f.exists() and f.is_file()
        ]
        combined = "\n".join(texts)
        assert ".super-dev/parking-lot.json" in combined, f"{target} missing parking-lot.json rule"
        assert "super-dev parking" in combined, f"{target} missing super-dev parking command guidance"


def test_web_dashboard_exposes_parking_lot_ui_and_delivery_smoke_script_runs() -> None:
    import subprocess
    import sys

    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "/api/parking-lot" in res.text
    assert "未决事项登记簿" in res.text
    assert "resolveParkingLotItem" in res.text

    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "check_delivery_ready.py"), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Super Dev" in proc.stdout

