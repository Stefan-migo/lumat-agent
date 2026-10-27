"""Deterministic topic routing for customer KB retrieval (S2)."""

from app.chat.nodes import respond
from app.services import kb


TOPIC_CASES = [
    ("hola, ustedes trabajan en maipu?", ["lumat-cobertura-horarios"]),
    (
        "necesito una visita, el calefont no calienta. vivo en ñuñoa y solo puedo un sabado",
        ["lumat-cobertura-horarios", "lumat-servicios"],
    ),
    (
        "carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber",
        ["lumat-cobertura-horarios"],
    ),
    ("y eso cuanto de garantia tiene?", ["lumat-garantias-pagos"]),
    (
        "hola, necesito mantencion de caldera, estoy en temuquito",
        ["lumat-cobertura-horarios"],
    ),
]


def test_schedule_terms_are_recognised_without_a_question_mark():
    """S4/T4: the measured sentence that used to be stored as the name."""
    assert respond.asks_about_schedule(
        "carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber"
    )
    assert respond.asks_about_schedule("¿atienden los domingos?")


def test_location_and_other_answers_are_not_schedule_questions():
    """T5/T5a and plain answers must keep landing in capture."""
    assert not respond.asks_about_schedule("estoy en providencia")
    assert not respond.asks_about_schedule("vivo en ñuñoa")
    assert not respond.asks_about_schedule("cuanto cuesta la mantención")


def test_topic_map_routes_s2_questions_to_seeded_document_ids():
    for question, expected in TOPIC_CASES:
        assert respond.topic_document_ids(question) == expected


def test_topic_search_returns_answer_from_the_routed_document(monkeypatch):
    calls = []
    hit = {
        "document_id": 7,
        "content": "Otras comunas: igual podemos ayudarte.",
        "similarity": 0.4033,
    }

    def retrieve(session, query, **kwargs):
        calls.append((query, kwargs))
        return [hit] if kwargs.get("source_ids") == ["lumat-cobertura-horarios"] else []

    monkeypatch.setattr(kb, "retrieve", retrieve)
    question = "hola, ustedes trabajan en maipu?"
    results = respond.retrieve_for_queries(
        None, [question], topic_source_ids=respond.topic_document_ids(question)
    )

    assert results == [hit]
    assert calls == [
        (
            question,
            {
                "top_k": kb.DEFAULT_TOP_K,
                "audience": "customer",
                "global_only": True,
                "source_ids": ["lumat-cobertura-horarios"],
            },
        )
    ]


def test_topic_miss_falls_back_to_full_corpus_without_changing_global_cutoff(monkeypatch):
    calls = []
    hit = {"document_id": 8, "content": "general customer KB fallback"}
    question = "pregunta asociada a cobertura"

    def retrieve(session, query, **kwargs):
        calls.append(kwargs)
        return [hit] if "source_ids" not in kwargs else []

    monkeypatch.setattr(kb, "retrieve", retrieve)
    results = respond.retrieve_for_queries(
        None, [question], topic_source_ids=["lumat-cobertura-horarios"]
    )

    assert results == [hit]
    assert "min_sim" not in calls[0]
    assert calls[1]["min_sim"] == kb.DEFAULT_MIN_SIM
    assert calls[0]["source_ids"] == ["lumat-cobertura-horarios"]
    assert "source_ids" not in calls[1]


def test_multi_topic_question_uses_both_documents_and_deduplicates_in_order(monkeypatch):
    first = {"document_id": 1, "chunk_index": 0, "content": "horario"}
    second = {"document_id": 2, "chunk_index": 0, "content": "servicio"}
    calls = []

    def retrieve(session, query, **kwargs):
        calls.append(kwargs.get("source_ids"))
        if kwargs.get("source_ids") == ["lumat-cobertura-horarios", "lumat-servicios"]:
            return [first, second, first]
        return []

    monkeypatch.setattr(kb, "retrieve", retrieve)
    question = "¿Atienden el sábado para reparar el calefont?"
    results = respond.retrieve_for_queries(
        None, [question], topic_source_ids=respond.topic_document_ids(question)
    )

    assert calls == [["lumat-cobertura-horarios", "lumat-servicios"]]
    assert results == [first, second]


def test_unmapped_and_near_miss_queries_keep_the_unfiltered_retrieval(monkeypatch):
    calls = []
    unrelated = {"document_id": 4, "content": "coincidencia semántica histórica"}

    def retrieve(session, query, **kwargs):
        calls.append((query, kwargs))
        return [unrelated]

    monkeypatch.setattr(kb, "retrieve", retrieve)
    question = "hola, arreglan lavadoras? se me inundo el lavadero"
    assert respond.topic_document_ids(question) == []
    assert respond.retrieve_for_queries(None, [question]) == [unrelated]
    assert calls == [
        (
            question,
            {
                "top_k": kb.DEFAULT_TOP_K,
                "min_sim": kb.DEFAULT_MIN_SIM,
                "audience": "customer",
                "global_only": True,
            },
        )
    ]


def test_no_topic_query_retains_existing_raw_then_service_order(monkeypatch):
    calls = []
    hit = {"document_id": 9, "content": "service hit"}

    def retrieve(session, query, **kwargs):
        calls.append(query)
        return [hit] if query == "mantención de caldera" else []

    monkeypatch.setattr(kb, "retrieve", retrieve)
    queries = respond.turn_queries(
        "hola, consulta", intent="consulta", service="mantención de caldera"
    )
    assert respond.retrieve_for_queries(None, queries) == [hit]
    assert calls == ["hola, consulta", "mantención de caldera"]
