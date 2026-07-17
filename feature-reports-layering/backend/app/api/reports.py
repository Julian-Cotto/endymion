from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_auth_context
from app.platform.auth_context import AuthContext
from app.platform.database.session import get_db
from app.platform.permissions import require_permissions
from app.models.report import ReportDefinition
from app.schemas.report import (
    GroupIn,
    GroupOut,
    MembershipIn,
    MembershipOut,
    ReportDefinitionIn,
    ReportDefinitionOut,
    ReportSummary,
    ReportView,
)
from app.services.reports import access, definitions, groups, snapshots
from app.services.reports.definitions import DefinitionError

router = APIRouter(prefix="/reports-layering", tags=["reports-layering"])


@router.get("/debug/snowflake-mode")
def snowflake_mode(ctx: AuthContext = Depends(require_permissions([access.PERM_VIEW]))):
    """Report whether the running server talks to real Snowflake ('live') or
    synthesizes rows ('mock'). Lets you confirm creds are actually loaded."""
    from app.platform.database.snowflake import get_snowflake_client

    client = get_snowflake_client()
    return {"mode": client.mode, "is_mock": client.is_mock}

# Permission dependencies (Entra role == permission).
require_view = require_permissions([access.PERM_VIEW])
require_author = require_permissions([access.PERM_CREATE])
require_admin = require_permissions([access.PERM_ADMIN])


# ----------------------------------------------------------------------------
# Serialization helpers
# ----------------------------------------------------------------------------
def _definition_out(db: Session, defn: ReportDefinition) -> ReportDefinitionOut:
    snap = snapshots.latest_snapshot(db, defn.id)
    out = ReportDefinitionOut.model_validate(defn)
    if snap:
        out.last_snapshot_at = snap.run_at
        out.last_snapshot_status = snap.status
    return out


def _summary(db: Session, defn: ReportDefinition) -> ReportSummary:
    snap = snapshots.latest_snapshot(db, defn.id)
    return ReportSummary(
        slug=defn.slug,
        title=defn.title,
        description=defn.description,
        output_types=defn.output_types,
        access_groups=defn.access_groups,
        status=defn.status,
        last_snapshot_at=snap.run_at if snap else None,
        last_snapshot_status=snap.status if snap else None,
    )


def _load_viewable(db: Session, slug: str, ctx: AuthContext) -> ReportDefinition:
    defn = definitions.get_by_slug(db, slug)
    if defn is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    group_slugs = access.user_group_slugs(db, ctx)
    if not access.can_view(defn, ctx, group_slugs):
        # 404 (not 403) so viewers can't probe which reports exist.
        raise HTTPException(status_code=404, detail="Report not found.")
    return defn


# ----------------------------------------------------------------------------
# Viewer surface
# ----------------------------------------------------------------------------
@router.get("/reports", response_model=list[ReportSummary])
def list_reports(
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_view),
):
    group_slugs = access.user_group_slugs(db, ctx)
    return [
        _summary(db, d)
        for d in definitions.list_definitions(db)
        if access.can_view(d, ctx, group_slugs)
    ]


@router.get("/reports/{slug}", response_model=ReportView)
def get_report(
    slug: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_view),
):
    defn = _load_viewable(db, slug, ctx)
    snap = snapshots.latest_snapshot(db, defn.id)
    return ReportView(
        slug=defn.slug,
        title=defn.title,
        description=defn.description,
        output_types=defn.output_types,
        layout=defn.layout,
        columns=defn.columns,
        chart=defn.chart,
        result_columns=snap.result_columns if snap else [],
        rows=snap.row_data if snap else [],
        row_count=snap.row_count if snap else 0,
        snapshot_at=snap.run_at if snap else None,
        snapshot_status=snap.status if snap else None,
        stale=snap is None,
    )


@router.get("/reports/{slug}/export.csv")
def export_report_csv(
    slug: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_view),
):
    defn = _load_viewable(db, slug, ctx)
    snap = snapshots.latest_snapshot(db, defn.id)
    if snap is None or snap.status != "ok":
        raise HTTPException(status_code=409, detail="No snapshot available to export.")

    cols = snap.result_columns or (list(snap.row_data[0].keys()) if snap.row_data else [])
    # Column config keys may differ in case from the driver's result columns.
    cfg_by_lower = {k.lower(): v for k, v in (defn.columns or {}).items()}
    labels = [(cfg_by_lower.get(c.lower()) or {}).get("label") or c for c in cols]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(labels)
    for row in snap.row_data:
        writer.writerow([row.get(c, "") for c in cols])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{defn.slug}.csv"'},
    )


# ----------------------------------------------------------------------------
# Author surface
# ----------------------------------------------------------------------------
@router.get("/definitions", response_model=list[ReportDefinitionOut])
def list_definitions_admin(
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_author),
):
    return [_definition_out(db, d) for d in definitions.list_definitions(db, include_archived=True)]


@router.get("/definitions/{slug}", response_model=ReportDefinitionOut)
def get_definition(
    slug: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_author),
):
    defn = definitions.get_by_slug(db, slug)
    if defn is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _definition_out(db, defn)


@router.post("/definitions", response_model=ReportDefinitionOut, status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: ReportDefinitionIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_author),
):
    try:
        defn = definitions.create_definition(db, payload, created_by=ctx.email or ctx.user_id)
    except DefinitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Immediate snapshot so the author sees output right away.
    snapshots.refresh_snapshot(db, defn)
    return _definition_out(db, defn)


@router.put("/definitions/{slug}", response_model=ReportDefinitionOut)
def update_definition(
    slug: str,
    payload: ReportDefinitionIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_author),
):
    defn = definitions.get_by_slug(db, slug)
    if defn is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    try:
        defn = definitions.update_definition(db, defn, payload)
    except DefinitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    snapshots.refresh_snapshot(db, defn)
    return _definition_out(db, defn)


@router.post("/definitions/{slug}/refresh", response_model=ReportDefinitionOut)
def refresh_definition(
    slug: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_author),
):
    defn = definitions.get_by_slug(db, slug)
    if defn is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    snap = snapshots.refresh_snapshot(db, defn)
    snapshots.prune_snapshots(db, defn.id)
    if snap.status != "ok":
        raise HTTPException(status_code=502, detail=f"Snapshot failed: {snap.error}")
    return _definition_out(db, defn)


# ----------------------------------------------------------------------------
# Group administration
# ----------------------------------------------------------------------------
@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
):
    out = []
    for group, count in groups.list_groups(db):
        item = GroupOut.model_validate(group)
        item.member_count = count
        out.append(item)
    return out


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
):
    return GroupOut.model_validate(groups.create_group(db, payload))


@router.post("/groups/{slug}/members", response_model=MembershipOut, status_code=status.HTTP_201_CREATED)
def add_member(
    slug: str,
    payload: MembershipIn,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
):
    group = groups.get_group(db, slug)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found.")
    return MembershipOut.model_validate(groups.add_member(db, group, payload))


@router.delete("/groups/{slug}/members/{user_key}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    slug: str,
    user_key: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
):
    group = groups.get_group(db, slug)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found.")
    if not groups.remove_member(db, group, user_key):
        raise HTTPException(status_code=404, detail="Membership not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
