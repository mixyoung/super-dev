"""测试完整性与静态反作弊探针 (Test Integrity & Anti-Gaming Probe)

借鉴 UmaDev U4 软内容规范与工业级测试交付标准：
静态审查测试代码的 AST 与结构特征，严密防范 AI 编程中通过以下手段“伪造测试绿灯”：
1. 注释断言 (Commented Assertions)：将失败的 assert / expect 注释掉换取无报错；
2. 跳过测试 (Skipped Tests)：私自添加 @pytest.mark.skip / it.skip 逃避失败检查；
3. 空测试/无断言测试 (Assertion-free Tests)：编写空测试或无 assert 语句的假用例。
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.reviewers.test_integrity")

IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".super-dev",
}


@dataclass
class TestIntegrityViolation:
    """测试完整性违规条目"""

    file_path: str
    line_number: int
    violation_type: str  # commented_assertion | skipped_test | assertion_free_test
    message: str
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestIntegrityReport:
    """测试完整性反作弊报告"""

    passed: bool
    violations: list[TestIntegrityViolation]
    scanned_files_count: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "scanned_files_count": self.scanned_files_count,
            "summary": self.summary,
            "violation_count": len(self.violations),
        }


class TestIntegrityChecker:
    """测试完整性反作弊检查器"""

    # 正则规则：用于匹配被注释的断言
    _PY_COMMENTED_ASSERT_RE = re.compile(r"^\s*#\s*(assert\b|self\.assert[a-zA-Z0-9_]*\b|pytest\.(raises|warns)\b)")
    _JS_COMMENTED_ASSERT_RE = re.compile(r"^\s*//\s*(expect\s*\(|assert\s*\(|assert\.[a-zA-Z0-9_]+\s*\()")

    # 正则规则：用于匹配 JS/TS 中的测试跳过
    _JS_SKIP_RE = re.compile(r"\b(it\.skip|test\.skip|describe\.skip|xit|xdescribe)\s*\(")

    @classmethod
    def scan_file(cls, file_path: Path) -> list[TestIntegrityViolation]:
        """扫描单个测试文件"""
        if not file_path.is_file():
            return []

        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return cls._scan_python_file(file_path)
        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            return cls._scan_js_file(file_path)
        return []

    @classmethod
    def _scan_python_file(cls, file_path: Path) -> list[TestIntegrityViolation]:
        violations: list[TestIntegrityViolation] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            _logger.warning("读取测试文件失败 %s: %s", file_path, e)
            return []

        lines = content.splitlines()

        # 1. 扫描行级别：被注释的断言
        for idx, line in enumerate(lines, 1):
            if cls._PY_COMMENTED_ASSERT_RE.match(line):
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=idx,
                        violation_type="commented_assertion",
                        message="检测到被注释的断言语句，疑似通过弱化校验以规避测试失败",
                        snippet=line.strip(),
                    )
                )

        # 2. AST 解析：检查跳过标记与无断言空测试
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            # 语法错误由常规 lint 捕获，此处跳过 AST 分析
            return violations

        for node in ast.walk(tree):
            # 检测跳过装饰器或跳过调用
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # 检查装饰器
                for decorator in node.decorator_list:
                    dec_src = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                    if any(s in dec_src for s in ("pytest.mark.skip", "pytest.mark.skipif", "unittest.skip")):
                        violations.append(
                            TestIntegrityViolation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                violation_type="skipped_test",
                                message=f"测试函数 `{node.name}` 带有跳过装饰器: {dec_src}",
                                snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                            )
                        )

                # 检查是否为测试函数：必须含有有效断言
                if node.name.startswith("test_") or node.name.endswith("_test"):
                    if not cls._has_valid_assertion(node):
                        violations.append(
                            TestIntegrityViolation(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                violation_type="assertion_free_test",
                                message=f"测试函数 `{node.name}` 缺少实质性 assert 断言，属于空假测试",
                                snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                            )
                        )

            # 检查函数体内的显式 pytest.skip 调用
            elif isinstance(node, ast.Call):
                call_src = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
                if call_src in {"pytest.skip", "unittest.skip"}:
                    violations.append(
                        TestIntegrityViolation(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            violation_type="skipped_test",
                            message=f"调用了逃避测试的显式跳过函数: {call_src}",
                            snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        )
                    )

        return violations

    @classmethod
    def _has_valid_assertion(cls, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """检查 Python 函数节点内是否包含有效的断言语句或断言上下文"""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                func_name = ast.unparse(child.func) if hasattr(ast, "unparse") else ""
                if (
                    func_name.startswith("self.assert")
                    or func_name in {"pytest.raises", "pytest.warns", "pytest.approx"}
                    or func_name.endswith("raises")
                ):
                    return True
            if isinstance(child, ast.With):
                for item in child.items:
                    ctx_name = ast.unparse(item.context_expr) if hasattr(ast, "unparse") else ""
                    if "pytest.raises" in ctx_name or "pytest.warns" in ctx_name:
                        return True
        return False

    @classmethod
    def _scan_js_file(cls, file_path: Path) -> list[TestIntegrityViolation]:
        violations: list[TestIntegrityViolation] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            _logger.warning("读取 JS 测试文件失败 %s: %s", file_path, e)
            return []

        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            if cls._JS_COMMENTED_ASSERT_RE.match(line):
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=idx,
                        violation_type="commented_assertion",
                        message="检测到被注释的 expect/assert 语句",
                        snippet=line.strip(),
                    )
                )
            elif cls._JS_SKIP_RE.search(line):
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=idx,
                        violation_type="skipped_test",
                        message="检测到跳过测试的函数调用（如 it.skip/xit）",
                        snippet=line.strip(),
                    )
                )

        return violations

    @classmethod
    def scan_project(cls, project_dir: Path | str) -> TestIntegrityReport:
        """扫描整个项目中的全部测试文件"""
        root = Path(project_dir).resolve()
        test_files: list[Path] = []

        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in IGNORE_DIRS for part in p.parts):
                continue

            name = p.name.lower()
            if (
                name.startswith("test_")
                or name.endswith("_test.py")
                or name.endswith(".test.js")
                or name.endswith(".spec.js")
                or name.endswith(".test.ts")
                or name.endswith(".spec.ts")
                or name.endswith(".test.tsx")
                or name.endswith(".spec.tsx")
            ):
                test_files.append(p)

        all_violations: list[TestIntegrityViolation] = []
        for tf in test_files:
            all_violations.extend(cls.scan_file(tf))

        passed = len(all_violations) == 0
        if passed:
            summary = f"通过：扫描了 {len(test_files)} 个测试文件，未发现注释断言或恶意跳过作弊行为。"
        else:
            summary = f"拦截：扫描了 {len(test_files)} 个测试文件，发现 {len(all_violations)} 处测试完整性违规/作弊项！"

        return TestIntegrityReport(
            passed=passed,
            violations=all_violations,
            scanned_files_count=len(test_files),
            summary=summary,
        )
