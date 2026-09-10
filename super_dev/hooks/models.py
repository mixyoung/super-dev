"""Hook 数据模型 — 定义 hook 事件、配置和执行结果。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HookType(str, Enum):
    """Hook 执行类型"""

    COMMAND = "command"  # Shell 命令
    PYTHON = "python"  # Python callable
    LOG = "log"  # 仅记录日志


@dataclass
class HookDefinition:
    """单个 hook 定义"""

    type: HookType = HookType.COMMAND
    command: str = ""  # 旧命令字符串，仅用于识别并给出迁移提示
    executable: str = ""  # 新结构化命令的程序
    args: tuple[str, ...] = ()  # 新结构化命令的参数列表
    validation_error: str = ""
    timeout: int = 30  # 超时秒数
    matcher: str = "*"  # 事件匹配模式 (阶段名 或 * 通配符)
    description: str = ""
    blocking: bool = True  # 是否阻塞 pipeline


@dataclass
class HookResult:
    """Hook 执行结果"""

    hook_name: str
    event: str
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    blocked: bool = False  # 是否阻止了 pipeline 继续
    phase: str = ""
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize hook result for JSON/API/history logs."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookResult:
        """Restore hook result from persisted JSON data."""
        return cls(
            hook_name=str(data.get("hook_name", "")),
            event=str(data.get("event", "")),
            success=bool(data.get("success", False)),
            output=str(data.get("output", "")),
            error=str(data.get("error", "")),
            duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
            blocked=bool(data.get("blocked", False)),
            phase=str(data.get("phase", "")),
            source=str(data.get("source", "")),
            timestamp=str(data.get("timestamp", "")) or datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class HookConfig:
    """Hook 配置（从 super-dev.yaml 的 hooks 段加载）

    YAML 格式:
    ```yaml
    hooks:
      PrePhase:
        - matcher: "drafting"
          type: command
          command:
            executable: python
            args: [scripts/pre-draft.py]
          timeout: 30
      PostPhase:
        - matcher: "*"
          type: command
          command:
            executable: python
            args: [-c, "print('Phase completed')"]
      PostQualityGate:
        - matcher: "*"
          type: log
          description: "Log quality gate results"
    ```
    """

    hooks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> HookConfig:
        """从字典创建配置"""
        if not data or not isinstance(data, dict):
            return cls()
        return cls(hooks=data)

    def get_definitions(self, event: str) -> list[HookDefinition]:
        """获取指定事件的 hook 定义列表"""
        raw_list = self.hooks.get(event, [])
        definitions: list[HookDefinition] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            validation_errors: list[str] = []
            unknown_item_fields = set(item) - {
                "type",
                "command",
                "timeout",
                "matcher",
                "description",
                "blocking",
            }
            if unknown_item_fields:
                validation_errors.append(f"Hook 包含未知字段: {sorted(unknown_item_fields)}")
            try:
                hook_type = HookType(item.get("type", "command"))
            except ValueError:
                hook_type = HookType.COMMAND
                validation_errors.append(f"未知 Hook 类型: {item.get('type')}")
            raw_command = item.get("command", "")
            legacy_command = raw_command if isinstance(raw_command, str) else ""
            structured_command = raw_command if isinstance(raw_command, dict) else {}
            executable = str(structured_command.get("executable", "")).strip()
            raw_args = structured_command.get("args", [])
            if isinstance(raw_command, dict):
                unknown_command_fields = set(structured_command) - {"executable", "args"}
                if unknown_command_fields:
                    validation_errors.append(
                        f"command 包含未知字段: {sorted(unknown_command_fields)}"
                    )
                if not isinstance(raw_args, list):
                    validation_errors.append("command.args 必须是数组")
            elif not isinstance(raw_command, str):
                validation_errors.append("command 必须是旧字符串或结构化对象")
            args = tuple(str(value) for value in raw_args) if isinstance(raw_args, list) else ()
            raw_timeout = item.get("timeout", 30)
            if (
                not isinstance(raw_timeout, int)
                or isinstance(raw_timeout, bool)
                or not (1 <= raw_timeout <= 3600)
            ):
                validation_errors.append("timeout 必须是 1-3600 的整数")
                timeout = 30
            else:
                timeout = raw_timeout
            raw_blocking = item.get("blocking", True)
            if not isinstance(raw_blocking, bool):
                validation_errors.append("blocking 必须是布尔值")
                blocking = True
            else:
                blocking = raw_blocking
            definitions.append(
                HookDefinition(
                    type=hook_type,
                    command=legacy_command,
                    executable=executable,
                    args=args,
                    validation_error="; ".join(validation_errors),
                    timeout=timeout,
                    matcher=str(item.get("matcher", "*")),
                    description=str(item.get("description", "")),
                    blocking=blocking,
                )
            )
        return definitions
