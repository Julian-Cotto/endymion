import json
import os
import subprocess
from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig

from tests.helpers import cli_python_executable


def test_render_manifest_includes_environment(tmp_path: Path) -> None:
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
    env["FEATURE_ENVIRONMENT"] = "test"
    env["FEATURE_FRONTEND_ENTRY_URL"] = "https://cdn.example.com/orders/bootstrap.js"
    env["FEATURE_BACKEND_BASE_URL"] = "https://api.example.com/orders"
    py = cli_python_executable()

    subprocess.run(
        [py, "scripts/render-manifest.py"],
        cwd=repo_dir,
        env=env,
        check=True,
    )

    resolved = json.loads(
        (repo_dir / "build" / "feature-manifest.resolved.json").read_text(encoding="utf-8")
    )

    assert resolved["environment"] == "test"
    assert resolved["frontend"]["entryUrl"] == "https://cdn.example.com/orders/bootstrap.js"
    assert resolved["backend"]["baseUrl"] == "https://api.example.com/orders"
    assert resolved["backend"]["healthEndpoint"] == "https://api.example.com/orders/health"
    


def test_resolved_manifest_contains_route_and_api_base_url(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(
            feature_name="orders",
            display_name="Orders",
            base_path="/orders",
        ),
        tmp_path,
    )

    contracts_manifest = {
        "featureKey": "orders",
        "displayName": "Orders",
        "description": "Orders management feature",
        "basePath": "/orders",
        "navigation": {
            "label": "Orders",
            "icon": "package",
        },
        "version": "0.1.0",
        "frontend": {
            "enabled": True,
            "entryStrategy": "vite-dynamic-import",
            "entryUrl": "/features/orders/assets/bootstrap.js",
            "mountFunction": "mount",
        },
        "backend": {
            "enabled": True,
            "baseUrl": "/api/orders",
            "healthEndpoint": "/api/orders/health",
        },
        "auth": {
            "required": True,
            "mode": "entra",
            "shellAuthRequired": True,
            "tokenForwarding": True,
            "tokenStrategy": "forwarded-bearer",
            "allowedDevModes": ["mock"],
            "roles": ["admin", "developer", "reader", "operator"],
        },
        "registry": {
            "enabled": True,
            "mode": "rest",
        },
        "events": {
            "publishes": ["orders.created"],
            "consumes": ["inventory.reserved"],
        },
        "workers": {
            "scheduledJobs": ["nightly-reconciliation"],
            "eventDrivenJobs": ["submit-order"],
            "eventListeners": ["inventory-reserved"],
        },
    }

    contracts_path = repo_dir / "contracts" / "feature-manifest.json"
    contracts_path.write_text(json.dumps(contracts_manifest, indent=2), encoding="utf-8")

    build_dir = repo_dir / "build"
    build_dir.mkdir(exist_ok=True)

    resolved = contracts_manifest.copy()
    resolved["environment"] = "dev"
    resolved["route"] = "/orders"
    resolved["frontend"]["entryUrl"] = "/features/orders/assets/bootstrap.js"
    resolved["backend"]["baseUrl"] = "/api/orders"
    resolved["backend"]["apiBaseUrl"] = "/api/orders"
    resolved["backend"]["healthEndpoint"] = "/api/orders/health"

    (build_dir / "feature-manifest.resolved.json").write_text(
        json.dumps(resolved, indent=2),
        encoding="utf-8",
    )

    manifest = json.loads((build_dir / "feature-manifest.resolved.json").read_text(encoding="utf-8"))

    assert manifest["route"] == "/orders"
    assert manifest["backend"]["apiBaseUrl"] == "/api/orders"