import json
import subprocess
import sys
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "check_delivery_ready.py"


def test_delivery_gate_script_passes_with_ready_manifest(temp_project_dir: Path) -> None:
    manifest = temp_project_dir / "output" / "delivery" / "demo-delivery-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "status": "ready",
                "missing_required": [],
                "included_files": ["output/demo-prd.md"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--project-dir",
            str(temp_project_dir),
            "--manifest",
            str(manifest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout


def test_delivery_gate_script_fails_with_incomplete_manifest(temp_project_dir: Path) -> None:
    manifest = temp_project_dir / "output" / "delivery" / "demo-delivery-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "status": "incomplete",
                "missing_required": [{"path": "x", "reason": "y"}],
                "included_files": ["output/demo-prd.md"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--project-dir",
            str(temp_project_dir),
            "--manifest",
            str(manifest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert proc.returncode == 1
    assert "[FAIL]" in proc.stdout

