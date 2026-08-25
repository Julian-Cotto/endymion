from .config import JobSettings
from .runner import run_job

def test_run_job_executes_without_error() -> None:
    run_job(JobSettings(feature_key="lead-locator", job_name="refresh-source-caches", schedule="0 3 * * *"))