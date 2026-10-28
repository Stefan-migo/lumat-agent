"""Commercial KB and Max persona contract (S2–S13 of `chatbot-cerebro-max-v4`).

Spec: `odd/tasks/chatbot-cerebro-max-v4.md`. These are DB-free: they pin the
documents' shape and content, and the persona's normative lines, so a later edit
cannot silently drop a commune, a guarantee or the honesty rule. Prices are not
part of the customer KB: they live in settings and reach the prompt resolved by
date, so a document must never quote one.

The chunker invariant is the reason S3 exists: `app/services/kb.py` splits at
500 characters with 50 of overlap and `respond` hands the model only 5 chunks
above 0.50 similarity. A fact paragraph that the splitter cuts never reaches the
model whole, so each one is asserted to survive inside a real chunk.
"""

from __future__ import annotations

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

KB = "docs/kb"
DOCS = [
    "lumat-identidad.md",
    "lumat-servicios.md",
    "lumat-cobertura-horarios.md",
    "lumat-garantias-pagos.md",
]
AMOUNTS = ("30.000", "50.000", "40.000", "80.000", "60.000", "140.000", "120.000")
COMMUNES = (
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
)
JARGON = ("control humano", "derivar", "escalar", "el bot", "LLM", "prompt")


def _read(repo_root, name: str) -> str:
    return (repo_root / KB / name).read_text(encoding="utf-8")


def _facts(text: str) -> list[str]:
    """Paragraphs that carry a fact (heading-only blocks excluded)."""
    blocks = re.split(r"\n\s*\n", text)
    return [
        block.strip()
        for block in blocks
        if block.strip()
        and not all(line.lstrip().startswith("#") for line in block.strip().splitlines())
    ]


def test_kb_has_four_customer_docs_without_internal_jargon(repo_root):
    """S2/S5: four documents, written for the customer."""
    assert sorted(path.name for path in (repo_root / KB).glob("*.md")) == sorted(DOCS)
    for name in DOCS:
        text = _read(repo_root, name)
        for term in JARGON:
            assert not re.search(re.escape(term), text, re.I), f"{name} contains {term!r}"


def test_kb_fact_paragraphs_fit_and_survive_the_chunker(repo_root):
    """S3: <= 480 chars and never split by CHUNK_SIZE=500 / CHUNK_OVERLAP=50."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    for name in DOCS:
        text = _read(repo_root, name)
        paragraphs = _facts(text)
        assert paragraphs, name
        chunks = splitter.split_text(text)
        for paragraph in paragraphs:
            assert len(paragraph) <= 480, f"{name}: {len(paragraph)} chars"
            assert any(paragraph in chunk for chunk in chunks), f"{name}: split fact"


def test_customer_kb_publishes_no_price(repo_root):
    """S5: prices live only in settings, resolved by date before the prompt."""
    for name in DOCS:
        text = _read(repo_root, name)
        for amount in AMOUNTS:
            assert amount not in text, f"{name} quotes {amount}"
        assert not re.search(r"\$\s?\d", text), f"{name} quotes a price"


def test_kb_makes_no_tax_claim(repo_root):
    """S5: no IVA/total/neto/bruto; tax detail goes to an asesor."""
    for name in DOCS:
        text = _read(repo_root, name)
        assert not re.search(r"\b(IVA|total|neto|bruto)\b", text, re.I), name
    assert "detalle tributario" in _read(repo_root, "lumat-garantias-pagos.md")


def test_kb_each_service_declares_scope(repo_root):
    """S6: four services, includes and does-not-include."""
    text = _read(repo_root, "lumat-servicios.md")
    for topic in (
        "Visita técnica",
        "Mantención de calefont",
        "Mantención de caldera",
        "Lavado de red",
    ):
        assert f"**{topic}" in text, topic
    assert text.count("qué incluye") >= 3
    assert text.count("qué no incluye") >= 4


def test_kb_lists_seven_communes_and_coordinates_outside(repo_root):
    """S7: exact coverage list, out-of-area coordination, no rejection."""
    text = _read(repo_root, "lumat-cobertura-horarios.md")
    for commune in COMMUNES:
        assert commune in text, commune
    assert "un asesor coordina" in text


def test_kb_hours_and_guarantees(repo_root):
    """S8/S9 + S5 (agenda-preferencia): the agenda is bookable Monday to Saturday.

    The KB used to send every Saturday to an advisor while `technician_weekly_schedule`
    carried Saturday blocks, so the bot denied availability the agenda would honour.
    The owner resolved the contradiction in favour of the agenda: Saturday is online,
    Sunday and holidays stay with an advisor.
    """
    hours = _read(repo_root, "lumat-cobertura-horarios.md")
    assert "lunes a sábado" in hours and "09:00 a 18:00" in hours
    assert "sábados, domingos" not in hours.lower()
    assert "domingos, los festivos" in hours.lower()
    guarantees = _read(repo_root, "lumat-garantias-pagos.md")
    assert "un año o hasta la próxima mantención" in guarantees
    assert "6 meses" in guarantees
    assert "No cubre repuestos" in guarantees
    assert "otra empresa" in guarantees
    assert "visita técnica" in guarantees


def test_kb_attributes_sec_to_lumat_technicians(repo_root):
    """S10: SEC authorization belongs to the company's technicians."""
    text = _read(repo_root, "lumat-identidad.md")
    assert "técnicos autorizados" in text
    assert "SEC" in text


def test_kb_payment_methods(repo_root):
    """S11: habitual methods, optional prepay or on delivery, boleta and factura."""
    text = _read(repo_root, "lumat-garantias-pagos.md")
    assert "medios de pago habituales" in text
    assert "de forma anticipada" in text
    assert "al momento de recibir el servicio" in text
    assert "boleta y factura" in text.lower()


def test_max_persona_contract(repo_root):
    """S13: identity, honesty, no personal SEC credential, style, gas safety."""
    text = (repo_root / "agent/personas/orchestrator.md").read_text(encoding="utf-8")
    assert text.startswith("Eres Max, el asistente virtual de Lumat")
    assert "Si te preguntan si eres un bot o una IA" in text
    assert "Nunca afirmes ser técnico SEC ni tener una credencial personal" in text
    assert "Nunca respondas un saludo con un formulario" in text
    assert "Español natural de Chile" in text
    assert "Sin emojis" in text
    assert "Ante olor a gas" in text and "Bomberos al 132" in text
    assert "No afirmes que derivaste el caso a una persona" in text
    assert not any(ord(char) > 0x2100 for char in text), "emoji or pictograph in persona"
