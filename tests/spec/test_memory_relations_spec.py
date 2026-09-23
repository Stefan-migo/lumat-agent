"""MEM-11 relation judging and read-path annotations."""

import json
from unittest.mock import Mock

import pytest
from sqlalchemy import select, text

from app.db import SessionLocal
from app.models import Conversation, Customer, Memory, MemoryRelation, MemoryStatus, MemoryType
from app.services import relations, tukulpan

pytestmark = pytest.mark.spec("MEM-11")


class _Completion:
    def __init__(self, content: str):
        self.choices = [Mock(message=Mock(content=content))]


class _Client:
    def __init__(self, content: str):
        self.chat = self
        self.completions = self
        self.content = content
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return _Completion(self.content)


def _memory(session, *, content, key, tipo=MemoryType.DECISION, entity="relation-customer"):
    return tukulpan.upsert(
        session,
        scope="customer",
        entity_id=entity,
        topic_key=key,
        tipo=tipo,
        titulo=key,
        contenido=content,
    )


def _verdict(memory_id: int, relation: str = "conflicts") -> str:
    return json.dumps(
        {
            "verdicts": [
                {
                    "candidate_id": memory_id,
                    "relation": relation,
                    "confidence": 0.91,
                    "reason": "The assertions disagree.",
                }
            ]
        }
    )


def test_mem11_contradicting_write_records_judged_relation(fake_embedder, migrated_db, monkeypatch):
    client = _Client(_verdict(1))
    monkeypatch.setattr(relations.llm, "openai_client", lambda: client)

    with SessionLocal() as session:
        previous = _memory(session, content="The customer prefers mornings.", key="preference-old")
        session.flush()
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()
        monkeypatch.setattr(relations, "find_candidates", lambda _session, _memory, top_k=5: [previous])
        relations.judge_memory_relations(session, current)
        row = session.execute(select(MemoryRelation)).scalar_one()

        assert row.id_a == current.id
        assert row.id_b == previous.id
        assert row.relation == "conflicts"
        assert row.confidence == pytest.approx(0.91)
        assert row.reason == "The assertions disagree."
        assert row.source == "judge"
        assert row.human_resolved_at is None
        assert client.calls == 1


def test_mem11_close_conversation_judges_customer_memo(
    fake_embedder, migrated_db, monkeypatch
):
    client = _Client(_verdict(1))
    monkeypatch.setattr(relations.llm, "openai_client", lambda: client)

    with SessionLocal() as session:
        customer = Customer(phone_e164="+56900000001")
        session.add(customer)
        session.flush()
        previous = _memory(
            session,
            content="The customer prefers mornings.",
            key="preference-old",
            entity=str(customer.id),
        )
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        monkeypatch.setattr(
            relations,
            "find_candidates",
            lambda _session, _memory, top_k=5: [previous],
        )

        tukulpan.close_conversation(
            session, conversation, acta_text="The customer prefers afternoons."
        )

        memo = session.scalar(
            select(Memory).where(
                Memory.scope == "customer",
                Memory.entity_id == str(customer.id),
                Memory.topic_key == "customer_memo",
            )
        )
        row = session.execute(select(MemoryRelation)).scalar_one()
        assert memo is not None
        assert row.id_a == memo.id
        assert row.id_b == previous.id
        assert row.relation == "conflicts"
        assert client.calls == 1


def test_mem11_close_conversation_survives_unavailable_judge(
    fake_embedder, migrated_db, monkeypatch
):
    monkeypatch.setattr(relations.llm, "openai_client", Mock(side_effect=TimeoutError()))

    with SessionLocal() as session:
        customer = Customer(phone_e164="+56900000002")
        session.add(customer)
        session.flush()
        previous = _memory(
            session,
            content="The customer prefers mornings.",
            key="preference-old",
            entity=str(customer.id),
        )
        session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation)
        session.flush()
        monkeypatch.setattr(relations, "find_candidates", lambda *_args, **_kwargs: [previous])

        tukulpan.close_conversation(session, conversation, acta_text="Customer memo")

        assert session.scalar(
            select(Memory).where(Memory.topic_key == "customer_memo")
        ) is not None
        assert session.execute(select(MemoryRelation)).scalars().all() == []


@pytest.mark.parametrize("response", [None, "not json", '{"verdicts": [{"candidate_id": 1}]}' ])
def test_mem11_bad_judge_response_writes_no_relation(
    fake_embedder, migrated_db, monkeypatch, response
):
    with SessionLocal() as session:
        previous = _memory(session, content="The customer prefers mornings.", key="preference-old")
        session.flush()
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()

        monkeypatch.setattr(relations, "find_candidates", lambda _session, _memory, top_k=5: [previous])
        if response is None:
            monkeypatch.setattr(relations.llm, "openai_client", Mock(side_effect=TimeoutError()))
        else:
            monkeypatch.setattr(relations.llm, "openai_client", lambda: _Client(response))

        relations.judge_memory_relations(session, current)
        assert session.execute(select(MemoryRelation)).scalars().all() == []
        assert session.get(Memory, current.id) is not None


def test_mem11_duplicate_candidate_id_is_rejected_deterministically():
    content = json.dumps(
        {
            "verdicts": [
                {
                    "candidate_id": 1,
                    "relation": "conflicts",
                    "confidence": 0.91,
                    "reason": "First verdict.",
                },
                {
                    "candidate_id": 1,
                    "relation": "related",
                    "confidence": 0.80,
                    "reason": "Duplicate verdict.",
                },
            ]
        }
    )

    with pytest.raises(ValueError, match="invalid verdict value"):
        relations._parse_verdicts(content, {1, 2})


def test_mem11_judge_failure_logs_and_writes_no_relation(
    fake_embedder, migrated_db, monkeypatch, caplog
):
    with SessionLocal() as session:
        previous = _memory(session, content="The customer prefers mornings.", key="preference-old")
        session.flush()
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()
        monkeypatch.setattr(relations, "find_candidates", lambda *_args, **_kwargs: [previous])
        monkeypatch.setattr(relations.llm, "openai_client", Mock(side_effect=RuntimeError("provider down")))

        with caplog.at_level("WARNING", logger=relations.__name__):
            relations.judge_memory_relations(session, current)

        assert session.execute(select(MemoryRelation)).scalars().all() == []
        assert "memory relation judge failed" in caplog.text
        assert "provider down" in caplog.text


def test_mem11_pending_confidence_is_recorded_for_human_queue(fake_embedder, migrated_db, monkeypatch):
    client = _Client(
        json.dumps(
            {
                "verdicts": [
                    {
                        "candidate_id": 1,
                        "relation": "conflicts",
                        "confidence": 0.69,
                        "reason": "Possibly contradictory.",
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(relations.llm, "openai_client", lambda: client)

    with SessionLocal() as session:
        previous = _memory(session, content="The customer prefers mornings.", key="preference-old")
        session.flush()
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()
        monkeypatch.setattr(relations, "find_candidates", lambda _session, _memory, top_k=5: [previous])
        relations.judge_memory_relations(session, current)
        row = session.execute(select(MemoryRelation)).scalar_one()
        assert row.confidence == pytest.approx(0.69)
        assert row.human_resolved_at is None
        assert relations.is_pending(row)


def test_mem11_no_candidate_and_decaying_write_make_no_llm_call(fake_embedder, migrated_db, monkeypatch):
    client = _Client(_verdict(1))
    monkeypatch.setattr(relations.llm, "openai_client", lambda: client)

    with SessionLocal() as session:
        isolated = _memory(session, content="An unrelated assertion.", key="isolated")
        session.flush()
        relations.judge_memory_relations(session, isolated)
        recap = _memory(session, content="A session snapshot.", key="session", tipo=MemoryType.SESSION)
        session.flush()
        relations.judge_memory_relations(session, recap)

        assert client.calls == 0
        assert session.execute(select(MemoryRelation)).scalars().all() == []


def test_mem11_read_paths_exclude_archived_and_annotate_review_and_relations(
    fake_embedder, migrated_db
):
    with SessionLocal() as session:
        archived = _memory(session, content="Archived customer note.", key="archived", entity="0")
        needs_review = _memory(session, content="Customer prefers mornings.", key="review", entity="0")
        current = _memory(session, content="Customer prefers afternoons.", key="current", entity="0")
        session.flush()
        archived.status = MemoryStatus.ARCHIVED
        needs_review.status = MemoryStatus.NEEDS_REVIEW
        session.add(
            MemoryRelation(
                id_a=current.id,
                id_b=needs_review.id,
                relation="supersedes",
                confidence=0.95,
                reason="Newer preference.",
                source="judge",
            )
        )
        session.commit()

        results = tukulpan.hybrid_search(
            session, "Customer prefers", scope="customer", entity_id="0", min_sim=0
        )
        ids = {item["id"] for item in results}
        review_result = next(item for item in results if item["id"] == needs_review.id)
        assert archived.id not in ids
        assert review_result["status"] == "needs_review"
        assert review_result["needs_review"] is True
        assert review_result["relation"] == "supersedes"

        context = tukulpan.load_customer_context(session, 0)
        assert "Archived customer note." not in context
        assert "superseded" in context
        assert "Customer prefers afternoons." in context


def test_mem11_candidate_search_failure_degrades_to_no_relation(
    fake_embedder, migrated_db, monkeypatch, caplog
):
    """A candidate-discovery failure must not escape into the write it was judging."""
    with SessionLocal() as session:
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()
        memory_id = current.id
        monkeypatch.setattr(
            relations, "find_candidates", Mock(side_effect=RuntimeError("candidate search down"))
        )

        with caplog.at_level("WARNING", logger=relations.__name__):
            result = relations.judge_memory_relations(session, current)

        assert result == []
        assert session.execute(select(MemoryRelation)).scalars().all() == []
        assert "memory relation judge failed" in caplog.text
        assert "candidate search down" in caplog.text

        session.commit()

    with SessionLocal() as fresh:
        assert fresh.get(Memory, memory_id) is not None


def test_mem11_candidate_query_error_leaves_the_transaction_usable(
    fake_embedder, migrated_db, monkeypatch, caplog
):
    """A real database error in discovery must not poison the caller's transaction."""
    def failing_query(_session, _memory, **_kwargs):
        _session.execute(text("SELECT * FROM a_table_that_does_not_exist"))
        raise AssertionError("the failing query must raise")

    with SessionLocal() as session:
        current = _memory(session, content="The customer prefers afternoons.", key="preference-new")
        session.flush()
        memory_id = current.id
        monkeypatch.setattr(relations, "find_candidates", failing_query)

        with caplog.at_level("WARNING", logger=relations.__name__):
            result = relations.judge_memory_relations(session, current)

        assert result == []
        assert "memory relation judge failed" in caplog.text

        # The judged write must remain committable: the caller's transaction survives.
        session.commit()

    with SessionLocal() as fresh:
        assert fresh.get(Memory, memory_id) is not None
