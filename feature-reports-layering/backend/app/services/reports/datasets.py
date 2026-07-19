"""Persist and load parsed file uploads (see ingest.parse_file)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportSource, UploadedDataset
from app.services.reports.ingest import ParsedFile


def create_dataset(
    db: Session, *, filename: str, parsed: ParsedFile, created_by: str | None
) -> UploadedDataset:
    ds = UploadedDataset(
        ref=uuid.uuid4().hex,
        filename=filename,
        columns=parsed.columns,
        row_data=parsed.rows,
        row_count=parsed.row_count,
        created_by=created_by,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def get_dataset(db: Session, ref: str) -> UploadedDataset | None:
    return db.execute(
        select(UploadedDataset).where(UploadedDataset.ref == ref)
    ).scalar_one_or_none()


def delete_orphans(db: Session, *, older_than_hours: int = 24) -> int:
    """Delete uploaded datasets no report source references and that are older
    than `older_than_hours`. Returns the number removed."""
    referenced = select(ReportSource.file_ref).where(ReportSource.file_ref.is_not(None))
    # Naive UTC to match the DB's CURRENT_TIMESTAMP storage (SQLite/Postgres).
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    cutoff = now_utc - dt.timedelta(hours=older_than_hours)
    orphans = list(
        db.execute(
            select(UploadedDataset).where(
                UploadedDataset.ref.not_in(referenced),
                UploadedDataset.created_at < cutoff,
            )
        ).scalars().all()
    )
    for ds in orphans:
        db.delete(ds)
    db.commit()
    return len(orphans)
