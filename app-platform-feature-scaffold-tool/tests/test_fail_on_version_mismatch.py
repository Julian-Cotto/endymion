import json
import subprocess
from pathlib import Path

from tests.helpers import cli_python_executable


def test_plan_fail_on_version_mismatch(tmp_path: Path) -> None:
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
    meta = json.loads((repo / "scaffold.metadata.json").read_text(encoding="utf-8"))
    meta["scaffoldVersion"] = "0.0.0-old"
    (repo / "scaffold.metadata.json").write_text(json.dumps(meta), encoding="utf-8")

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
            "--fail-on-version-mismatch",
        ],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert r.returncode == 3
