"""Shared predicates for a question about the visit the customer already holds.

Measured production case (2026-11-27, conversation 50): «Tengo una visita para el
lunes, puedes confirmarme que técnico va?» and «Tengo una hora agendada para el
lunes», asked about appointment 24 — `booked`, 30/11 14:00, technician assigned.
Neither turn reached any code that reads the customer's own appointments, so the
first was answered with free slots and the second with a questionnaire.

These predicates are the one definition of both shapes: the router decides where
the turn goes and the deterministic answer decides what it reads, from the same
function, so they cannot disagree.
"""

from __future__ import annotations

import pytest

from app.chat.visit_questions import asks_about_booked_visit, asks_for_change

MEASURED_TURNS = (
    "Tengo una visita para el lunes, puedes confirmarme que tecnico va?",
    "Tengo una hora agendada para el lunes",
    "Hola, me confirmas a que hora es mi visita?",
    "Cual es el tecnico que viene a mi visita?",
    "A que hora viene el tecnico hoy?",
    "puedes confirmarme mi hora agendada para el martes",
    "Quien va a ir a la visita del lunes?",
    "Tengo una visita agendada para el sabado, a que hora llega?",
)


@pytest.mark.parametrize("text", MEASURED_TURNS)
def test_a_turn_about_the_customers_own_visit_is_recognised(text):
    assert asks_about_booked_visit(text) is True


NOT_ABOUT_A_BOOKED_VISIT = (
    # Free-agenda questions keep their own answer.
    "¿tienen hora el lunes?",
    "¿Pueden el sábado?",
    "¿tienen horas disponibles esta semana?",
    "¿atienden en La Florida?",
    # Configured-hours questions.
    "¿hasta qué hora abren el sábado?",
    # Price of the visit service, not the customer's appointment.
    "¿cuánto cuesta la visita técnica?",
    # A new visit request, nothing is booked yet.
    "quiero agendar una visita",
    "necesito una visita técnica para mi calefont",
    # A change request belongs to `manage`, never to the status answer.
    "quiero reagendar mi visita",
    "necesito cancelar la visita del lunes",
    "Tengo una visita agendada necesito cambiar la fecha de la visita",
    "Tengo una visita agendada, necesito cambiar la fecha de la visita",
)


@pytest.mark.parametrize("text", NOT_ABOUT_A_BOOKED_VISIT)
def test_other_questions_are_not_the_booked_visit_shape(text):
    assert asks_about_booked_visit(text) is False


def test_the_two_predicates_do_not_overlap_on_a_change_request():
    """A change request names the visit, and still must not be answered as status."""
    text = "necesito cambiar la fecha de mi visita para el jueves"
    assert asks_for_change(text) is True
    assert asks_about_booked_visit(text) is False


def test_a_status_question_is_not_a_change_request():
    text = "Tengo una visita para el lunes, puedes confirmarme que tecnico va?"
    assert asks_about_booked_visit(text) is True
    assert asks_for_change(text) is False
