"""
开发:Excellent(11964948@qq.com)
功能:日志系统测试
作用:验证日志系统功能正常
创建时间:2025-01-29
最后修改:2025-01-29
"""

import logging
import tempfile
from contextlib import ExitStack
from pathlib import Path

from super_dev.utils import get_logger, log_with_extra


class TestLogger:
    """日志系统测试"""

    def test_get_logger_basic(self):
        """测试基本日志记录器创建"""
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO

    def test_get_logger_with_file(self):
        """测试带文件输出的日志记录器"""
        with tempfile.TemporaryDirectory() as tmpdir, ExitStack() as cleanup:
            log_file = Path(tmpdir) / "test.log"
            logger = get_logger("test_file_logger", log_file=log_file, level="DEBUG")
            for handler in list(logger.handlers):
                cleanup.callback(handler.close)
                cleanup.callback(logger.removeHandler, handler)

            logger.info("Test message")
            logger.debug("Debug message")

            # 验证日志文件被创建
            assert log_file.exists()

            # 验证日志内容
            log_content = log_file.read_text(encoding="utf-8")
            assert "Test message" in log_content
            assert "Debug message" in log_content

    def test_colored_formatter(self):
        """测试彩色格式化器"""
        from super_dev.utils.logger import ColoredFormatter

        formatter = ColoredFormatter(fmt="%(levelname)s - %(message)s")

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "\033[" in formatted  # 包含ANSI颜色代码

    def test_structured_formatter(self):
        """测试结构化格式化器"""
        from super_dev.utils.logger import StructuredFormatter

        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # 添加额外数据
        record.extra_data = {"user_id": 123, "action": "login"}

        formatted = formatter.format(record)
        assert "timestamp" in formatted
        assert "level" in formatted
        assert "user_id" in formatted

    def test_log_with_extra(self):
        """测试带额外数据的日志记录"""
        with tempfile.TemporaryDirectory() as tmpdir, ExitStack() as cleanup:
            log_file = Path(tmpdir) / "test_extra.log"
            logger = get_logger("test_extra", log_file=log_file)
            for handler in list(logger.handlers):
                cleanup.callback(handler.close)
                cleanup.callback(logger.removeHandler, handler)

            log_with_extra(
                logger, "info", "User login", user_id=123, ip="127.0.0.1", action="login"
            )

            log_content = log_file.read_text(encoding="utf-8")
            assert "User login" in log_content
