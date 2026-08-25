import subprocess
from pathlib import Path

from tests.helpers import cli_python_executable


def test_apply_dry_run_zero_exit(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    py = cli_python_executable()
    cfg = root / "examples" / "orders-feature.json"
    subprocess.run(
        [py, "-m", "feature_scaffold.cli", "create", "--config", str(cfg), "--output-dir", str(tmp_path)],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
        check=True,
    )
    repo = tmp_path / "feature-orders"
    r = subprocess.run(
        [
            py,
            "-m",
            "feature_scaffold.cli",
            "apply",
            "--config",
            str(cfg),
            "--repo",
            str(repo),
            "--dry-run",
        ],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert r.returncode == 0
