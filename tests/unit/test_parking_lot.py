"""Unit tests for ParkingLotRegister and session brief synchronization."""

from pathlib import Path

from super_dev.parking_lot import ParkingLotItem, ParkingLotRegister
from super_dev.session.brief import SessionBrief


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


def test_parking_lot_register_save_and_load(tmp_path: Path) -> None:
    reg = ParkingLotRegister()
    it1 = reg.add_item(
        title="支付网关沙箱切换",
        reason_for_deferral="沙箱联调账号未审批",
        revisit_trigger="收到测试密钥",
        current_compromise="使用 MockPaymentGateway",
        affected_components=["payments/gateway.py"],
    )
    assert it1.id == "PARK-001"

    saved_path = reg.save(tmp_path)
    assert saved_path.exists()

    loaded = ParkingLotRegister.load(tmp_path)
    assert len(loaded.items) == 1
    assert loaded.items[0].title == "支付网关沙箱切换"


def test_parking_lot_resolve_and_open_items() -> None:
    reg = ParkingLotRegister()
    reg.add_item("任务A", "理由A", "条件A", "折衷A")
    reg.add_item("任务B", "理由B", "条件B", "折衷B")

    assert len(reg.get_open_items()) == 2
    success = reg.resolve_item("PARK-001", "已在 PR #10 引入并压测通过")
    assert success is True

    open_items = reg.get_open_items()
    assert len(open_items) == 1
    assert open_items[0].id == "PARK-002"
    assert reg.items[0].status == "resolved"
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
    # 正常完整条目
    reg.add_item("完整项", "清晰原因", "明确触发条件", "清晰妥协方案")
    assert reg.validate_compliance() == []

    # 敷衍占位条目
    reg.add_item("敷衍项", "TBD", "待定", "暂无")
    violations = reg.validate_compliance()
    assert len(violations) >= 2


def test_session_brief_sync_parking_lot(tmp_path: Path) -> None:
    # 1. 建立未决事项
    reg = ParkingLotRegister()
    reg.add_item("微服务拆分", "业务模式尚在探索期", "团队规模超过 15 人", "单体模块化架构")
    reg.save(tmp_path)

    # 2. 同步到会话简报
    SessionBrief.sync_parking_lot(tmp_path)

    # 3. 校验 SESSION_BRIEF.md 中生成了 Open Decisions
    sections = SessionBrief.load(tmp_path)
    assert "Open Decisions" in sections
    assert "微服务拆分" in sections["Open Decisions"]
    assert "团队规模超过 15 人" in sections["Open Decisions"]
