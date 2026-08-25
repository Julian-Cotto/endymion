import subprocess
from pathlib import Path

from tests.helpers import cli_python_executable


def test_apply_non_interactive_fails_on_modified(tmp_path: Path) -> None:
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
    (repo / "README.md").write_text("changed", encoding="utf-8")
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
            "--non-interactive",
        ],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert r.returncode == 2
