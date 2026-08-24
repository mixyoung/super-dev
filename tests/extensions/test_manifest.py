from __future__ import annotations

import pytest

from super_dev.extensions.manifest import ManifestValidationError, parse_manifest

from .helpers import manifest_payload


def test_valid_builtin_manifest_is_strictly_parsed() -> None:
    manifest = parse_manifest(manifest_payload())

    assert manifest.id == "contract-probe"
    assert manifest.source.kind == "builtin"
    assert manifest.required_capabilities[0].value == "write_evidence"
    assert manifest.execution.executor == "builtin-python"


def test_unknown_top_level_field_is_rejected() -> None:
    payload = manifest_payload()
    payload["surprise"] = True

    with pytest.raises(ManifestValidationError) as exc:
        parse_manifest(payload)

    assert "未知字段" in str(exc.value)


def test_unknown_capability_and_stage_are_rejected() -> None:
    payload = manifest_payload()
    payload["capabilities"]["required"] = ["become-owner"]
    payload["trigger"]["allowed_stages"] = ["review"]

    with pytest.raises(ManifestValidationError) as exc:
        parse_manifest(payload)

    assert "未知能力" in str(exc.value)
    assert "未知阶段" in str(exc.value)


def test_non_boolean_authority_is_rejected() -> None:
    payload = manifest_payload()
    payload["authority"]["push"] = "false"

    with pytest.raises(ManifestValidationError) as exc:
        parse_manifest(payload)

    assert "authority.push 必须是布尔值" in str(exc.value)


def test_adapted_source_requires_exact_upstream_identity() -> None:
    payload = manifest_payload()
    payload["source"]["kind"] = "adapted"
    payload["kind"] = "engineering-method"

    with pytest.raises(ManifestValidationError) as exc:
        parse_manifest(payload)

    assert "upstream_commit" in str(exc.value)
    assert "upstream_digest" in str(exc.value)


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "C:\\escape.py", "~/x.py"])
def test_source_path_escape_is_rejected(path: str) -> None:
    payload = manifest_payload(source_path=path)

    with pytest.raises(ManifestValidationError):
        parse_manifest(payload)
