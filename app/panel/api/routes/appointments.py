"""Authenticated local scheduling operations (AP-10/11)."""

from datetime import date, datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AppointmentStatus, Case, Conversation, Customer, User
from app.panel.api.deps import require_operator_json
from app.panel.api.serializers import (
    to_agenda_dict,
    to_appointment_detail_dict,
    to_appointment_dict,
)
from app.panel.deps import get_db
from app.services import scheduling
from app.services import technician_schedule

router = APIRouter(tags=["panel-api-appointments"])


class AppointmentBody(BaseModel):
    service: str
    customer_id: int
    case_id: int
    technician_id: int
    local_date: date
    local_time: time
    timezone: str
    duration_minutes: int = Field(gt=0)


class CancelBody(BaseModel):
    reason: str | None = None


class CloseBody(BaseModel):
    outcome: Literal["completed", "no_show"]
    reason: str | None = None


class BulkCloseBody(BaseModel):
    appointment_ids: list[int] = Field(min_length=1, max_length=100)
    outcome: Literal["completed", "no_show"]
    reason: str | None = None


class RescheduleBody(BaseModel):
    local_date: date
    local_time: time
    timezone: str
    duration_minutes: int = Field(gt=0)
    technician_id: int


class TechnicianScheduleEntry(BaseModel):
    weekday: int
    opens_at: time
    closes_at: time


class TechnicianScheduleBody(BaseModel):
    schedule: list[TechnicianScheduleEntry]


@router.get("/appointments")
def list_appointments(from_date: date = Query(alias="from"), to_date: date = Query(alias="to"), timezone_name: str = Query(alias="timezone"), session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    try:
        rows = scheduling.list_for_range(session, from_date, to_date, timezone_name)
    except scheduling.InvalidTimezone as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_timezone", "message": str(exc)}) from exc
    except scheduling.InvalidRange as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_range", "message": str(exc)}) from exc
    return {"appointments": [to_agenda_dict(appointment, customer_name=customer_name, customer_address=customer_address, customer_comuna=customer_comuna, case_name=case_name, technician_name=technician_name, timezone_name=timezone_name, sync=sync) for appointment, customer_name, customer_address, customer_comuna, case_name, technician_name, sync in rows]}


@router.get("/appointments/overdue")
def list_overdue_appointments(session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    rows = scheduling.list_overdue(session)
    return {"appointments": [
        to_agenda_dict(
            appointment, customer_name=customer_name, customer_address=customer_address,
            customer_comuna=customer_comuna, case_name=case_name,
            technician_name=technician_name, timezone_name=appointment.timezone, sync=sync,
        )
        for appointment, customer_name, customer_address, customer_comuna, case_name, technician_name, sync in rows
    ]}


@router.post("/appointments/bulk-close")
def bulk_close_appointments(body: BulkCloseBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    outcome = AppointmentStatus(body.outcome)
    results = []
    for appointment_id in body.appointment_ids:
        try:
            appointment = session.get(scheduling.Appointment, appointment_id)
            if appointment is None:
                results.append({
                    "id": appointment_id, "ok": False, "outcome": body.outcome,
                    "error": "appointment not found",
                })
                continue
            scheduling.close(
                session, appointment, outcome=outcome, actor=current.username, reason=body.reason
            )
            session.commit()
        except ValueError as exc:
            results.append({
                "id": appointment_id, "ok": False, "outcome": body.outcome,
                "error": str(exc),
            })
            continue
        except SQLAlchemyError:
            session.rollback()
            results.append({
                "id": appointment_id, "ok": False, "outcome": body.outcome,
                "error": "database error while closing appointment",
            })
            continue
        results.append({"id": appointment_id, "ok": True, "outcome": body.outcome, "error": None})
    closed = sum(result["ok"] for result in results)
    return {"closed": closed, "failed": len(results) - closed, "results": results}


@router.get("/availability/{technician_id}")
def technician_availability(technician_id: int, starts_at: datetime, ends_at: datetime, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    try:
        available = scheduling.availability(session, technician_id, starts_at, ends_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"technician_id": technician_id, "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat(), "available": available}


@router.get("/technicians/{technician_id}/schedule")
def get_technician_schedule(technician_id: int, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    entries = technician_schedule.get_schedule(session, technician_id)
    return {"technician_id": technician_id, "schedule": [
        {**entry, "opens_at": entry["opens_at"].isoformat(), "closes_at": entry["closes_at"].isoformat()}
        for entry in entries
    ]}


@router.put("/technicians/{technician_id}/schedule")
def put_technician_schedule(technician_id: int, body: TechnicianScheduleBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    try:
        entries = technician_schedule.set_schedule(
            session, technician_id, [entry.model_dump() for entry in body.schedule]
        )
    except technician_schedule.InvalidSchedule as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_schedule", "message": str(exc)}) from exc
    session.commit()
    return {"technician_id": technician_id, "schedule": [
        {**entry, "opens_at": entry["opens_at"].isoformat(), "closes_at": entry["closes_at"].isoformat()}
        for entry in entries
    ]}


@router.post("/appointments")
def create_appointment(body: AppointmentBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    try:
        appointment = scheduling.book(session, service=body.service, customer_id=body.customer_id, case_id=body.case_id, technician_id=body.technician_id, local_date=body.local_date, local_time=body.local_time, timezone_name=body.timezone, duration_minutes=body.duration_minutes, actor=current.username)
    except scheduling.UnlinkedAppointment as exc:
        raise HTTPException(status_code=400, detail={"code": "unlinked_appointment", "message": str(exc)}) from exc
    except scheduling.AppointmentConflict as exc:
        raise HTTPException(status_code=409, detail={"code": "appointment_conflict", "message": str(exc)}) from exc
    except scheduling.Unavailable as exc:
        raise HTTPException(status_code=409, detail={"code": "technician_unavailable", "message": str(exc)}) from exc
    except scheduling.InvalidTimezone as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_timezone", "message": str(exc)}) from exc
    except (scheduling.NonexistentLocalTime, scheduling.AmbiguousLocalTime, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_local_time", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True, "appointment": to_appointment_dict(appointment)}


@router.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    customer = session.get(Customer, appointment.customer_id)
    case = session.get(Case, appointment.case_id)
    conversation = session.get(Conversation, case.conversation_id) if case.conversation_id is not None else None
    return to_appointment_detail_dict(
        appointment,
        customer=customer,
        case=case,
        conversation_summary=conversation.summary if conversation is not None else None,
    )


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, body: CancelBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    try:
        scheduling.cancel(session, appointment, actor=current.username, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_lifecycle", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True, "appointment": to_appointment_dict(appointment)}


@router.post("/appointments/{appointment_id}/close")
def close_appointment(appointment_id: int, body: CloseBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    try:
        scheduling.close(session, appointment, outcome=AppointmentStatus(body.outcome), actor=current.username, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_lifecycle", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True, "appointment": to_appointment_dict(appointment)}


@router.patch("/appointments/{appointment_id}")
def reschedule_appointment(appointment_id: int, body: RescheduleBody, session: Session = Depends(get_db), current: User = Depends(require_operator_json)) -> dict:
    appointment = session.get(scheduling.Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    try:
        scheduling.reschedule(session, appointment, local_date=body.local_date, local_time=body.local_time, timezone_name=body.timezone, duration_minutes=body.duration_minutes, technician_id=body.technician_id, actor=current.username)
    except scheduling.Unavailable as exc:
        raise HTTPException(status_code=409, detail={"code": "technician_unavailable", "message": str(exc)}) from exc
    except scheduling.AppointmentConflict as exc:
        raise HTTPException(status_code=409, detail={"code": "appointment_conflict", "message": str(exc)}) from exc
    except scheduling.InvalidTimezone as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_timezone", "message": str(exc)}) from exc
    except (scheduling.NonexistentLocalTime, scheduling.AmbiguousLocalTime) as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_local_time", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "invalid_lifecycle", "message": str(exc)}) from exc
    session.commit()
    return {"ok": True, "appointment": to_appointment_dict(appointment)}
