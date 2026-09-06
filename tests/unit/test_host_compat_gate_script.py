import json
import subprocess
import sys
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "check_host_compatibility.py"


def test_host_compat_gate_script_passes_with_score_over_threshold(temp_project_dir: Path) -> None:
    report = temp_project_dir / "output" / "demo-host-compatibility.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "compatibility": {
                    "overall_score": 91.2,
                    "ready_hosts": 2,
                    "total_hosts": 4,
                }
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
            "--report",
            str(report),
            "--min-score",
            "80",
            "--min-ready-hosts",
            "1",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert proc.returncode == 0
    assert "[PASS]" in proc.stdout


def test_host_compat_gate_script_fails_when_score_below_threshold(temp_project_dir: Path) -> None:
    report = temp_project_dir / "output" / "demo-host-compatibility.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "compatibility": {
                    "overall_score": 65,
                    "ready_hosts": 0,
                    "total_hosts": 4,
                }
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
            "--report",
            str(report),
            "--min-score",
            "80",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert proc.returncode == 1
    assert "[FAIL]" in proc.stdout


def test_host_compat_gate_script_uses_thresholds_from_config(temp_project_dir: Path) -> None:
    (temp_project_dir / "super-dev.yaml").write_text(
        (
            "name: demo\n"
            "host_compatibility_min_score: 88\n"
            "host_compatibility_min_ready_hosts: 2\n"
        ),
        encoding="utf-8",
    )
    report = temp_project_dir / "output" / "demo-host-compatibility.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "compatibility": {
                    "overall_score": 90,
                    "ready_hosts": 1,
                    "total_hosts": 3,
                }
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
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert proc.returncode == 1
    assert "min_ready_hosts=2" in proc.stdout
