import json
import subprocess
from pathlib import Path

from tests.helpers import cli_python_executable


def test_plan_fail_on_orphan_exit_code(tmp_path: Path) -> None:
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

    orphan = repo / "orphan-only.txt"
    orphan.write_text("x", encoding="utf-8")
    meta = json.loads((repo / "scaffold.metadata.json").read_text(encoding="utf-8"))
    meta["managedFiles"]["orphan-only.txt"] = "replace"
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
            "--fail-on-orphan",
        ],
        cwd=root,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert r.returncode == 5
