from __future__ import annotations

import yaml

from super_dev.extensions.manifest import load_manifest, parse_manifest
from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.source_lock import SourceLockVerifier, stable_content_digest

from .helpers import manifest_payload


def _write_lock(path, *, digest: str, manifest_digest: str = "") -> None:
    source_entry = {
        "kind": "builtin",
        "path": "builtins/probe.py",
        "content_digest": digest,
        "reviewed_at": "2026-08-25",
    }
    if manifest_digest:
        source_entry["manifest_digest"] = manifest_digest
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "sources": {
                    "contract-probe": source_entry,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_source_lock_matches_local_content(tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "builtins" / "probe.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    digest = stable_content_digest(source)
    lock = tmp_path / "sources.lock.yaml"
    _write_lock(lock, digest=digest)
    manifest = parse_manifest(manifest_payload(digest=digest))

    result = SourceLockVerifier(source_root=source_root, lock_path=lock).verify(manifest)

    assert result.status == ExtensionStatus.PASS
    assert result.actual_digest == digest


def test_source_content_drift_is_blocked(tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "builtins" / "probe.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    digest = stable_content_digest(source)
    lock = tmp_path / "sources.lock.yaml"
    _write_lock(lock, digest=digest)
    manifest = parse_manifest(manifest_payload(digest=digest))
    source.write_text("VALUE = 2\n", encoding="utf-8")

    result = SourceLockVerifier(source_root=source_root, lock_path=lock).verify(manifest)

    assert result.status == ExtensionStatus.BLOCKED
    assert "本地扩展内容" in " ".join(result.errors)


def test_directory_digest_is_stable_by_relative_path(tmp_path) -> None:
    first = tmp_path / "tree"
    (first / "b").mkdir(parents=True)
    (first / "b" / "two.txt").write_text("two", encoding="utf-8")
    (first / "one.txt").write_text("one", encoding="utf-8")

    before = stable_content_digest(first)
    after = stable_content_digest(first)

    assert before == after


def test_manifest_content_is_also_locked(tmp_path) -> None:
    source_root = tmp_path / "source"
    source = source_root / "builtins" / "probe.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    digest = stable_content_digest(source)
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest_payload(digest=digest), sort_keys=False),
        encoding="utf-8",
    )
    lock = tmp_path / "sources.lock.yaml"
    _write_lock(
        lock,
        digest=digest,
        manifest_digest=stable_content_digest(manifest_path),
    )
    manifest = load_manifest(manifest_path)
    verifier = SourceLockVerifier(source_root=source_root, lock_path=lock)
    assert verifier.verify(manifest).status == ExtensionStatus.PASS
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + "# drift\n")

    drifted = verifier.verify(load_manifest(manifest_path))

    assert drifted.status == ExtensionStatus.BLOCKED
    assert "清单内容" in " ".join(drifted.errors)
