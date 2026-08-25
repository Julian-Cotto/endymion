from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import (
    AuthConfig,
    BackendConfig,
    EventContract,
    EventDrivenJobConfig,
    EventTriggerConfig,
    EventsConfig,
    FrontendConfig,
    ScaffoldConfig,
    ScheduledJobConfig,
)


def _generator() -> ScaffoldGenerator:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    return ScaffoldGenerator(templates_dir=templates_dir)


def test_generate_frontend_backend_only(tmp_path: Path) -> None:
    repo_dir = _generator().generate(
        ScaffoldConfig(
            feature_name="catalog",
            display_name="Catalog",
            base_path="/catalog",
            backend=BackendConfig(api_base_path="/api/catalog"),
        ),
        tmp_path,
    )

    assert (repo_dir / "frontend").exists()
    assert (repo_dir / "backend").exists()
    assert not (repo_dir / "jobs").exists()
    assert not (repo_dir / "workers").exists()
    assert not (repo_dir / "listeners").exists()


def test_generate_backend_workers_only(tmp_path: Path) -> None:
    repo_dir = _generator().generate(
        ScaffoldConfig(
            feature_name="billing",
            display_name="Billing",
            base_path="/billing",
            frontend=FrontendConfig(enabled=False, shell_integration=False),
            backend=BackendConfig(api_base_path="/api/billing"),
            scheduled_jobs=[
                ScheduledJobConfig(name="invoice-rollup", schedule="0 1 * * *")
            ],
            event_driven_jobs=[
                EventDrivenJobConfig(
                    name="process-payment",
                    trigger=EventTriggerConfig(
                        kind="topic-subscription",
                        topic="billing",
                        subscription="process-payment",
                    ),
                    payload_schema="ProcessPaymentRequested",
                )
            ],
            events=EventsConfig(
                publishes=[EventContract(name="billing.payment-processed", schema="PaymentProcessed")],
                consumes=[EventContract(name="billing.payment-requested", schema="ProcessPaymentRequested")],
            ),
        ),
        tmp_path,
    )

    assert not (repo_dir / "frontend").exists()
    assert (repo_dir / "backend").exists()
    assert (repo_dir / "jobs" / "invoice_rollup").exists()
    assert (repo_dir / "workers" / "process_payment").exists()


def test_generate_auth_none(tmp_path: Path) -> None:
    repo_dir = _generator().generate(
        ScaffoldConfig(
            feature_name="public-portal",
            display_name="Public Portal",
            base_path="/public",
            backend=BackendConfig(api_base_path="/api/public"),
            auth=AuthConfig(
                mode="none",
                shell_auth_required=False,
                backend_token_strategy="none",
                token_forwarding=False,
                allowed_dev_modes=["none", "mock"],
                roles=["reader"],
            ),
        ),
        tmp_path,
    )

    manifest = (repo_dir / "contracts" / "feature-manifest.json").read_text(encoding="utf-8")
    assert '"mode": "none"' in manifest
    assert '"required": false' in manifest
    assert '"shellAuthRequired": false' in manifest
    assert '"tokenForwarding": false' in manifest