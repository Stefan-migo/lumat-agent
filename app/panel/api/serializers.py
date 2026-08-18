"""Panel JSON API serializers (B2/T2.1+T2.2; PDW-API, D4).

ORM rows -> plain dicts at the API boundary: no SQLAlchemy objects ever
leave the JSON layer (PDW-API "no ORM leak"). Field names are the service
dict keys (snake_case, same as `customer_history` in app/services/
customers.py), and datetimes are converted to ISO-8601 strings so the
response is fully JSON-native before FastAPI even encodes it.

Each serializer mirrors what the corresponding Jinja template renders —
the SPA must show the same fields the current panel shows.
"""

from __future__ import annotations

from app.models import Customer, CustomerNote


def _iso(value) -> str | None:
    """ISO-8601 string for a tz-aware datetime, else None (PDW-API)."""
    return value.isoformat() if value is not None else None


def to_customer_dict(customer: Customer) -> dict:
    """Customer row -> snake_case service dict (ficha + clients list)."""
    return {
        "id": customer.id,
        "phone_e164": customer.phone_e164,
        "name": customer.name,
        "email": customer.email,
        "comuna": customer.comuna,
        "address": customer.address,
        "state": customer.state.value,
        "consent_status": customer.consent_status,
        "consent_at": _iso(customer.consent_at),
        "created_at": _iso(customer.created_at),
    }


def to_note_dict(note: CustomerNote) -> dict:
    """Internal staff note -> snake_case service dict (CR-4)."""
    return {
        "id": note.id,
        "customer_id": note.customer_id,
        "note": note.note,
        "author": note.author,
        "created_at": _iso(note.created_at),
    }
