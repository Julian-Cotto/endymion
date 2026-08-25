import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import cli_python_executable


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX paths in test")
def test_plan_fail_on_modified_exit_code(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    py = cli_python_executable()
    cfg = root / "examples" / "orders-feature.json"
    repo = tmp_path / "feature-orders"
    repo.mkdir(parents=True)

    subprocess.run(
        [py, "-m", "feature_scaffold.cli", "create", "--config", str(cfg), "--output-dir", str(tmp_path)],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
        check=True,
    )

    (repo / "README.md").write_text("tampered", encoding="utf-8")

    r = subprocess.run(
        [
            py,
            "-m",
            "feature_scaffold.cli",
            "plan",
            "--config",
            str(cfg),
            "--repo",
            str(repo),
            "--fail-on-modified",
        ],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert r.returncode == 2
