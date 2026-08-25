import json
import os
import subprocess
from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig


def cli_python_executable() -> str:
    return os.environ.get("PYTHON", "python")


def test_render_registry_payload_wraps_resolved_manifest(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    env = os.environ.copy()
    env["FEATURE_ENVIRONMENT"] = "prod"
    env["FEATURE_FRONTEND_ENTRY_URL"] = "https://cdn.example.com/orders/bootstrap.js"
    env["FEATURE_BACKEND_BASE_URL"] = "https://api.example.com/orders"

    py = cli_python_executable()

    subprocess.run(
        [py, "scripts/render-manifest.py"],
        cwd=repo_dir,
        env=env,
        check=True,
    )

    subprocess.run(
        [py, "scripts/render-registry-payload.py"],
        cwd=repo_dir,
        env=env,
        check=True,
    )

    payload = json.loads(
        (repo_dir / "build" / "registry-payload.json").read_text(encoding="utf-8")
    )

    assert payload["featureKey"] == "orders"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "prod"
    assert payload["displayName"] == "Orders"
    assert payload["route"] == "/orders"

    assert payload["frontend"]["entryUrl"] == "https://cdn.example.com/orders/bootstrap.js"
    assert payload["frontend"]["type"] == "module"
    assert payload["frontend"]["basePath"] == "/orders"

    assert payload["backend"]["apiBaseUrl"] == "https://api.example.com/orders"

    assert payload["nav"]["label"] == "Orders"
    assert payload["authorization"]["requiredPermissions"] == ["orders.view"]
    assert payload["authorization"]["requiredFlags"] == ["orders.enabled"]

    assert payload["auth"]["required"] is True
    assert payload["auth"]["mode"] in {"mock", "entra"}
    assert "tokenForwarding" in payload["auth"]
    assert "tokenStrategy" in payload["auth"]

    assert "manifest" not in payload