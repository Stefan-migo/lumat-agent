"""CSV export (T5.5; AP-7).

GET /panel/export/clients.csv — clients with the panel-visible fields.
GET /panel/export/cases.csv   — cases with customer + responsible, the
                                 fields the cases view shows.

Streaming via the stdlib `csv` writer over a generator (design D7 — no
export library; AP-7 "CSV or Excel", Excel cut by the ponytail review).
Requires login; the data stays under Lumat's control (export is a panel
read over the same tables).
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.models import Case, Customer, User
from app.panel.deps import get_db, require_user

router = APIRouter(tags=["panel-export"])


def _csv_stream(headers: list[str], rows) -> object:
    """Yield CSV lines from a row iterable (stdlib csv, streaming)."""

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        yield buffer.getvalue()
        for row in rows:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow(row)
            yield buffer.getvalue()

    return generate()


def _csv_response(stream, filename: str) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


CLIENT_HEADERS = [
    "id",
    "phone_e164",
    "name",
    "email",
    "comuna",
    "address",
    "state",
    "consent_status",
    "created_at",
]


@router.get("/export/clients.csv")
def export_clients(session=Depends(get_db), current=Depends(require_user)):
    customers = session.scalars(select(Customer).order_by(Customer.id)).all()

    def rows():
        for c in customers:
            yield [
                c.id,
                c.phone_e164,
                c.name or "",
                c.email or "",
                c.comuna or "",
                c.address or "",
                c.state.value,
                "yes" if c.consent_status else "no",
                c.created_at.isoformat() if c.created_at else "",
            ]

    return _csv_response(_csv_stream(CLIENT_HEADERS, rows()), "clients.csv")


CASE_HEADERS = [
    "id",
    "customer_name",
    "customer_phone",
    "service",
    "priority",
    "status",
    "emergency",
    "responsible_username",
    "summary",
    "created_at",
    "escalated_at",
    "closed_at",
]


@router.get("/export/cases.csv")
def export_cases(session=Depends(get_db), current=Depends(require_user)):
    rows_data = session.execute(
        select(Case, Customer, User)
        .join(Customer, Case.customer_id == Customer.id)
        .outerjoin(User, Case.responsible_id == User.id)
        .order_by(Case.id)
    ).all()

    def rows():
        for case, customer, responsible in rows_data:
            yield [
                case.id,
                customer.name or "",
                customer.phone_e164,
                case.service or "",
                case.priority or "",
                case.status or "",
                "yes" if case.emergency else "no",
                responsible.username if responsible else "",
                case.summary or "",
                case.created_at.isoformat() if case.created_at else "",
                case.escalated_at.isoformat() if case.escalated_at else "",
                case.closed_at.isoformat() if case.closed_at else "",
            ]

    return _csv_response(_csv_stream(CASE_HEADERS, rows()), "cases.csv")
