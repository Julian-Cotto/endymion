from .config import JobSettings
from .runner import run_job

from app.runtime.database import db_session
from app.schemas.report import ReportDefinitionIn
from app.services.reports import definitions


def _make_report(slug: str) -> None:
    with db_session() as db:
        if definitions.get_by_slug(db, slug):
            return
        definitions.create_definition(
            db,
            ReportDefinitionIn(
                title=slug,
                slug=slug,
                sql_text="SELECT region, COUNT(*) AS n FROM t GROUP BY region",
                columns={"region": {"label": "Region"}, "n": {"format": "int"}},
                output_types=["table"],
            ),
            created_by="test",
        )


def test_run_job_refreshes_active_reports() -> None:
    _make_report("job-smoke-report")
    result = run_job(
        JobSettings(
            feature_key="reports-layering",
            job_name="refresh-report-snapshots",
            schedule="0 * * * *",
        )
    )
    assert result["refreshed"] >= 1
    assert result["failed"] == 0
