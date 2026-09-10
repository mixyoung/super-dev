"""
开发:Excellent(11964948@qq.com)
功能:异常系统测试
作用:验证自定义异常类功能正常
创建时间:2025-01-29
最后修改:2025-01-29
"""

from super_dev.exceptions import (
    ExternalServiceError,
    FileSystemError,
    OpenAIError,
    PhaseExecutionError,
    QualityGateError,
    SuperDevError,
    ValidationError,
)


class TestSuperDevError:
    """基础异常类测试"""

    def test_basic_error(self):
        """测试基本异常创建"""
        error = SuperDevError("Test error")
        assert str(error) == "[SuperDevError] Test error"
        assert error.message == "Test error"
        assert error.code == "SuperDevError"

    def test_error_with_code(self):
        """测试带错误码的异常"""
        error = SuperDevError("Test error", code="CUSTOM_ERROR")
        assert error.code == "CUSTOM_ERROR"

    def test_error_with_details(self):
        """测试带详细信息的异常"""
        details = {"field": "name", "value": "test"}
        error = SuperDevError("Validation failed", details=details)
        assert error.details == details

    def test_error_to_dict(self):
        """测试异常转换为字典"""
        error = SuperDevError("Test error", code="TEST_ERROR", details={"key": "value"})
        error_dict = error.to_dict()
        assert error_dict == {
            "error": "TEST_ERROR",
            "message": "Test error",
            "details": {"key": "value"},
        }


class TestWorkflowError:
    """工作流异常测试"""

    def test_phase_execution_error(self):
        """测试阶段执行异常"""
        error = PhaseExecutionError(
            phase="DISCOVERY", message="Discovery phase failed", details={"reason": "timeout"}
        )
        assert error.phase == "DISCOVERY"
        assert "Discovery phase failed" in str(error)
        assert error.details["reason"] == "timeout"

    def test_quality_gate_error(self):
        """测试质量门禁异常"""
        error = QualityGateError(
            score=65.0, threshold=80.0, details={"failed_checks": ["security", "performance"]}
        )
        assert error.score == 65.0
        assert error.threshold == 80.0
        assert "65.0" in str(error)
        assert "80.0" in str(error)


class TestConfigurationError:
    """配置异常测试"""

    def test_validation_error(self):
        """测试验证异常"""
        error = ValidationError(
            field="email", message="Invalid email format", details={"value": "not-an-email"}
        )
        assert error.field == "email"
        assert error.details["value"] == "not-an-email"


class TestExternalServiceError:
    """外部服务异常测试"""

    def test_external_service_error(self):
        """测试外部服务异常"""
        error = ExternalServiceError(
            service="openai",
            message="API rate limit exceeded",
            status_code=429,
            details={"retry_after": 60},
        )
        assert error.service == "openai"
        assert error.status_code == 429

    def test_openai_error(self):
        """测试OpenAI异常"""
        error = OpenAIError("Invalid API key", details={"key": "sk-***"})
        assert error.service == "openai"
        assert error.status_code is None


class TestFileSystemError:
    """文件系统异常测试"""

    def test_filesystem_error(self):
        """测试文件系统异常"""
        error = FileSystemError(
            path="/tmp/test.txt",
            message="File not found",
            details={"checked_paths": ["/tmp/test.txt", "./test.txt"]},
        )
        assert error.path == "/tmp/test.txt"
        assert error.details["checked_paths"] == ["/tmp/test.txt", "./test.txt"]
