from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.panel.api.deps import require_user_json
from app.panel.deps import get_db
from app.services.dashboard import drilldown as dashboard_drilldown
from app.services.dashboard import operational_summary, trend as dashboard_trend

router = APIRouter(prefix="/dashboard", tags=["panel-api-dashboard"])


@router.get("/summary")
def summary(start: datetime, end: datetime, timezone: str = Query(...), session: Session = Depends(get_db), _user=Depends(require_user_json)):
    return operational_summary(session, start, end, timezone)


@router.get("/trend")
def trend(start: datetime, end: datetime, timezone: str = Query(...), metric: str = Query(...), bucket: str = Query("day"), session: Session = Depends(get_db), _user=Depends(require_user_json)):
    if bucket != "day":
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="only day buckets are supported")
    return dashboard_trend(session, start, end, timezone, metric)


@router.get("/drilldown")
def drilldown(start: datetime, end: datetime, timezone: str = Query(...), metric: str = Query(...), bucket_start: date = Query(...), session: Session = Depends(get_db), _user=Depends(require_user_json)):
    return dashboard_drilldown(session, start, end, timezone, metric, bucket_start)
