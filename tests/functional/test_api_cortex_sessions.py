"""Legacy planning threads remain ordinary chat threads after API retirement."""

from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User


def test_planning_routes_are_absent_and_legacy_thread_remains_listed(client, make_user):
    make_user("legacy-cortex", "cortex-pass", role="admin")
    login = client.post("/panel/api/login", json={"username": "legacy-cortex", "password": "cortex-pass"})
    assert login.status_code == 200
    with SessionLocal() as session:
        thread = InternalChatThread(
            user_id=session.query(User).filter_by(username="legacy-cortex").one().id,
            proyecto="default",
            assistant_state={"cortex_session": {"slug": "legacy", "status": "closed"}},
        )
        session.add(thread)
        session.flush()
        thread_id = thread.id
        session.add(InternalChatMessage(
            thread_id=thread_id, author="user", content="legacy message", status="completed"
        ))
        session.commit()

    assert client.get("/panel/api/planning/sessions").status_code == 404
    assert client.post("/panel/api/planning/sessions", json={"topic": "new"}).status_code == 404
    listed = client.get("/panel/api/chat/threads?limit=10")
    assert listed.status_code == 200
    assert thread_id in {row["id"] for row in listed.json()["threads"]}
    read = client.get(f"/panel/api/chat/threads/{thread_id}")
    assert read.status_code == 200
    assert read.json()["messages"][0]["content"] == "legacy message"
