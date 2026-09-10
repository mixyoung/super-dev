from __future__ import annotations

from super_dev import terminal


class _StdoutStub:
    def __init__(self, encoding: str) -> None:
        self.encoding = encoding


def test_normalize_terminal_text_keeps_unicode_on_utf8(monkeypatch):
    monkeypatch.delenv("SUPER_DEV_OUTPUT_MODE", raising=False)
    monkeypatch.setattr(terminal.sys, "stdout", _StdoutStub("utf-8"))
    assert terminal.normalize_terminal_text("✓ Ready → next…") == "✓ Ready → next…"


def test_normalize_terminal_text_downgrades_on_cp936(monkeypatch):
    monkeypatch.setenv("SUPER_DEV_OUTPUT_MODE", "ascii")
    assert (
        terminal.normalize_terminal_text("✓ Failed ✗ → next… [●][✓][○]")
        == "* Failed X -> next... [>][*][o]"
    )


def test_output_mode_ascii_forces_downgrade(monkeypatch):
    monkeypatch.setenv("SUPER_DEV_OUTPUT_MODE", "ascii")
    monkeypatch.setattr(terminal.sys, "stdout", _StdoutStub("utf-8"))
    assert terminal.supports_unicode_output() is False
    assert terminal.symbol("success") == "*"


def test_output_mode_unicode_forces_unicode(monkeypatch):
    monkeypatch.setenv("SUPER_DEV_OUTPUT_MODE", "unicode")
    monkeypatch.setattr(terminal.sys, "stdout", _StdoutStub("cp936"))
    assert terminal.supports_unicode_output() is True
    assert terminal.symbol("success") == "✓"


def test_output_mode_reason_reflects_ascii_override(monkeypatch):
    monkeypatch.setenv("SUPER_DEV_OUTPUT_MODE", "ascii")
    monkeypatch.setattr(terminal.sys, "stdout", _StdoutStub("utf-8"))
    assert terminal.output_mode_label() == "ascii-fallback"
    assert terminal.output_mode_reason() == "SUPER_DEV_OUTPUT_MODE=ascii"
