"""测试完整性与静态反作弊探针 (Test Integrity & Anti-Gaming Probe)

借鉴 UmaDev U4 软内容规范与工业级测试交付标准：
静态审查测试代码的 AST 与词法特征，防范 AI 编程中通过以下手段“伪造测试绿灯”：
1. 注释断言 (Commented Assertions)：将失败的 assert / expect 注释掉换取无报错；
2. 无条件跳过测试 (Skipped Tests)：私自添加无条件 skip / skipif(True) / it.skip 逃避失败检查；
3. 空测试/无断言测试 (Assertion-free Tests)：编写空占位或无有效断言的假用例。

同时避免对真实工程实践造成误伤：
- 仅基于 Python tokenize 识别真实注释，不误判多行测试夹具字符串中的 `# assert`；
- 区分动态条件平台/环境跳过（如 `@pytest.mark.skipif(os.name != 'nt')`、`if ...: pytest.skip(...)`、`except ...: pytest.skip(...)`）与无条件逃避测试；
- 仅检查顶层测试函数及测试类方法，不误伤测试函数内部的嵌套回调辅助函数；
- 识别 mock 断言（`mock.assert_*`）及断言/契约校验辅助函数（`assert_*` / `validate_*` / `verify_*` / `check_*`）。
"""

from __future__ import annotations

import ast
import io
import logging
import re
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.reviewers.test_integrity")

IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".tox",
    ".nox",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "site-packages",
    ".super-dev",
    ".claude",
    ".agents",
    ".codex",
    ".cursor",
    ".opencode",
    ".kilocode",
    ".roo",
    ".openclaw",
    ".windsurf",
    ".cline",
    ".junie",
    "plugins",
}

_TRIVIAL_BUILTINS = {
    "print",
    "len",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "range",
    "enumerate",
    "zip",
    "type",
    "isinstance",
    "issubclass",
    "repr",
    "sorted",
    "min",
    "max",
    "sum",
    "any",
    "all",
    "super",
    "Path",
}


@dataclass
class TestIntegrityViolation:
    """测试完整性违规条目"""

    file_path: str
    line_number: int
    violation_type: str  # commented_assertion | skipped_test | assertion_free_test
    message: str
    snippet: str = ""
    severity: str = "error"  # error (blocking) | warning (advisory)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestIntegrityReport:
    """测试完整性反作弊报告"""

    passed: bool
    violations: list[TestIntegrityViolation]
    scanned_files_count: int
    summary: str

    @property
    def blocking_violations(self) -> list[TestIntegrityViolation]:
        return [v for v in self.violations if v.severity == "error"]

    @property
    def advisory_violations(self) -> list[TestIntegrityViolation]:
        return [v for v in self.violations if v.severity != "error"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "scanned_files_count": self.scanned_files_count,
            "summary": self.summary,
            "violation_count": len(self.violations),
            "blocking_count": len(self.blocking_violations),
            "warning_count": len(self.advisory_violations),
        }


class TestIntegrityChecker:
    """测试完整性反作弊检查器"""

    _PY_COMMENTED_ASSERT_RE = re.compile(
        r"^#\s*(assert\b|self\.assert[a-zA-Z0-9_]*\b|pytest\.(raises|warns)\b)"
    )
    _JS_COMMENTED_ASSERT_RE = re.compile(
        r"^\s*//\s*(expect\s*\(|assert\s*\(|assert\.[a-zA-Z0-9_]+\s*\()"
    )
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

        # 1. 使用 Python tokenize 仅检查真实注释，避免误报多行测试字符串夹具
        try:
            for tok in tokenize.generate_tokens(io.StringIO(content).readline):
                if tok.type == tokenize.COMMENT and cls._PY_COMMENTED_ASSERT_RE.match(tok.string):
                    lineno = tok.start[0]
                    violations.append(
                        TestIntegrityViolation(
                            file_path=str(file_path),
                            line_number=lineno,
                            violation_type="commented_assertion",
                            message="检测到被注释的断言语句，疑似通过弱化校验以规避测试失败",
                            snippet=(
                                lines[lineno - 1].strip() if lineno <= len(lines) else tok.string
                            ),
                            severity="error",
                        )
                    )
        except (tokenize.TokenError, IndentationError):
            pass

        # 2. AST 解析：仅检查顶层测试函数与测试类方法
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return violations

        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if cls._is_test_function_name(node.name):
                    violations.extend(cls._inspect_python_test_func(node, file_path, lines))
            elif isinstance(node, ast.ClassDef) and cls._is_test_class(node):
                violations.extend(cls._inspect_class_skip_decorators(node, file_path, lines))
                for item in node.body:
                    if isinstance(
                        item, ast.FunctionDef | ast.AsyncFunctionDef
                    ) and cls._is_test_function_name(item.name):
                        violations.extend(cls._inspect_python_test_func(item, file_path, lines))

        return violations

    @staticmethod
    def _is_test_function_name(name: str) -> bool:
        return name.startswith("test_") or name.endswith("_test")

    @staticmethod
    def _is_test_class(node: ast.ClassDef) -> bool:
        if node.name.startswith("Test"):
            return True
        for base in node.bases:
            base_name = ast.unparse(base) if hasattr(ast, "unparse") else ""
            if base_name.endswith("TestCase"):
                return True
        return False

    @staticmethod
    def _eval_static_bool(expr: ast.expr) -> bool | None:
        if isinstance(expr, ast.Constant):
            return bool(expr.value)
        return None

    @classmethod
    def _inspect_class_skip_decorators(
        cls,
        node: ast.ClassDef,
        file_path: Path,
        lines: list[str],
    ) -> list[TestIntegrityViolation]:
        violations: list[TestIntegrityViolation] = []
        for decorator in node.decorator_list:
            reason = cls._check_skip_decorator(decorator)
            if reason:
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        violation_type="skipped_test",
                        message=f"测试类 `{node.name}` {reason}",
                        snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        severity="error",
                    )
                )
        return violations

    @classmethod
    def _check_skip_decorator(cls, decorator: ast.expr) -> str | None:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        dec_name = ast.unparse(target) if hasattr(ast, "unparse") else ""

        if dec_name in {"pytest.mark.skip", "unittest.skip"}:
            return f"带有无条件跳过装饰器: {dec_name}"

        if dec_name in {"pytest.mark.skipif", "unittest.skipIf"} and isinstance(
            decorator, ast.Call
        ):
            if decorator.args:
                const_val = cls._eval_static_bool(decorator.args[0])
                if const_val is True:
                    return f"带有恒真跳过装饰器: {ast.unparse(decorator)}"
            return None

        if dec_name == "unittest.skipUnless" and isinstance(decorator, ast.Call):
            if decorator.args:
                const_val = cls._eval_static_bool(decorator.args[0])
                if const_val is False:
                    return f"带有恒假 skipUnless 装饰器: {ast.unparse(decorator)}"
            return None

        return None

    @classmethod
    def _inspect_python_test_func(
        cls,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        lines: list[str],
    ) -> list[TestIntegrityViolation]:
        violations: list[TestIntegrityViolation] = []

        for decorator in node.decorator_list:
            reason = cls._check_skip_decorator(decorator)
            if reason:
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=node.lineno,
                        violation_type="skipped_test",
                        message=f"测试函数 `{node.name}` {reason}",
                        snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        severity="error",
                    )
                )

        # 检查函数体内的无条件 pytest.skip / unittest.skip 调用（放行条件/异常分支下的守卫式跳过）
        for skip_lineno, call_src in cls._find_unguarded_skip_calls(node.body):
            violations.append(
                TestIntegrityViolation(
                    file_path=str(file_path),
                    line_number=skip_lineno,
                    violation_type="skipped_test",
                    message=f"调用了无条件逃避测试的跳过函数: {call_src}",
                    snippet=lines[skip_lineno - 1].strip() if skip_lineno <= len(lines) else "",
                    severity="error",
                )
            )

        # 检查是否存在有效断言；无断言时区分纯空桩（阻断）与无显式断言的冒烟调用（提示）
        if not cls._has_valid_assertion(node):
            has_sut_call = cls._has_non_trivial_call(node)
            violations.append(
                TestIntegrityViolation(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    violation_type="assertion_free_test",
                    message=(
                        f"测试函数 `{node.name}` 仅执行调用但缺少显式断言"
                        if has_sut_call
                        else f"测试函数 `{node.name}` 缺少实质性 assert 断言，属于空假测试"
                    ),
                    snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                    severity="warning" if has_sut_call else "error",
                )
            )

        return violations

    @classmethod
    def _find_unguarded_skip_calls(
        cls, stmts: list[ast.stmt], *, in_guard: bool = False
    ) -> list[tuple[int, str]]:
        hits: list[tuple[int, str]] = []
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                const_test = cls._eval_static_bool(stmt.test)
                branch_guarded = in_guard or (const_test is None)
                if const_test is not False:
                    hits.extend(cls._find_unguarded_skip_calls(stmt.body, in_guard=branch_guarded))
                if const_test is not True:
                    hits.extend(
                        cls._find_unguarded_skip_calls(stmt.orelse, in_guard=branch_guarded)
                    )
            elif isinstance(stmt, ast.Try):
                hits.extend(cls._find_unguarded_skip_calls(stmt.body, in_guard=in_guard))
                for handler in stmt.handlers:
                    hits.extend(cls._find_unguarded_skip_calls(handler.body, in_guard=True))
                hits.extend(cls._find_unguarded_skip_calls(stmt.orelse, in_guard=in_guard))
                hits.extend(cls._find_unguarded_skip_calls(stmt.finalbody, in_guard=in_guard))
            elif isinstance(stmt, ast.With | ast.AsyncWith):
                hits.extend(cls._find_unguarded_skip_calls(stmt.body, in_guard=in_guard))
            elif isinstance(stmt, ast.For | ast.AsyncFor | ast.While):
                hits.extend(cls._find_unguarded_skip_calls(stmt.body, in_guard=in_guard))
                hits.extend(cls._find_unguarded_skip_calls(stmt.orelse, in_guard=in_guard))
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and not in_guard:
                call_src = ast.unparse(stmt.value.func) if hasattr(ast, "unparse") else ""
                if call_src in {"pytest.skip", "unittest.skip"}:
                    hits.append((stmt.lineno, call_src))
        return hits

    @classmethod
    def _has_valid_assertion(cls, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """检查 Python 测试函数内是否包含有效的断言语句、Mock 断言或校验辅助调用"""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                func_name = ast.unparse(child.func) if hasattr(ast, "unparse") else ""
                leaf_name = func_name.rsplit(".", 1)[-1]
                if (
                    func_name.startswith("self.assert")
                    or func_name.startswith("self.fail")
                    or func_name
                    in {"pytest.raises", "pytest.warns", "pytest.approx", "pytest.fail"}
                    or func_name.endswith("raises")
                    or leaf_name.startswith(("assert_", "validate_", "verify_", "check_", "expect"))
                    or leaf_name in {"assert", "expect", "fail"}
                ):
                    return True
            if isinstance(child, ast.With | ast.AsyncWith):
                for item in child.items:
                    ctx_name = ast.unparse(item.context_expr) if hasattr(ast, "unparse") else ""
                    if "raises" in ctx_name or "warns" in ctx_name:
                        return True
        return False

    @classmethod
    def _has_non_trivial_call(cls, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """判断测试体是否至少调用了业务/被测代码而非纯占位字面量"""
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                func_name = ast.unparse(child.func) if hasattr(ast, "unparse") else ""
                leaf_name = func_name.rsplit(".", 1)[-1]
                if leaf_name not in _TRIVIAL_BUILTINS:
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
        in_block_comment = False
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped[2:]:
                    in_block_comment = True
                continue

            if cls._JS_COMMENTED_ASSERT_RE.match(line):
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=idx,
                        violation_type="commented_assertion",
                        message="检测到被注释的 expect/assert 语句",
                        snippet=stripped,
                        severity="error",
                    )
                )
            elif not stripped.startswith("//") and cls._JS_SKIP_RE.search(line):
                violations.append(
                    TestIntegrityViolation(
                        file_path=str(file_path),
                        line_number=idx,
                        violation_type="skipped_test",
                        message="检测到跳过测试的函数调用（如 it.skip/xit）",
                        snippet=stripped,
                        severity="error",
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
            try:
                rel_parts = p.relative_to(root).parts
            except ValueError:
                rel_parts = p.parts
            if any(part in IGNORE_DIRS for part in rel_parts):
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

        blocking_count = sum(1 for v in all_violations if v.severity == "error")
        warning_count = len(all_violations) - blocking_count
        passed = blocking_count == 0
        if passed:
            if warning_count == 0:
                summary = f"通过：扫描了 {len(test_files)} 个测试文件，未发现注释断言、无条件跳过或空假测试。"
            else:
                summary = (
                    f"通过：扫描了 {len(test_files)} 个测试文件，未发现阻断性作弊行为"
                    f"（另有 {warning_count} 处无显式断言的冒烟用例提示）。"
                )
        else:
            summary = (
                f"拦截：扫描了 {len(test_files)} 个测试文件，发现 {blocking_count} 处测试完整性违规"
                + (f"（另有 {warning_count} 处提示）！" if warning_count else "！")
            )

        return TestIntegrityReport(
            passed=passed,
            violations=all_violations,
            scanned_files_count=len(test_files),
            summary=summary,
        )
