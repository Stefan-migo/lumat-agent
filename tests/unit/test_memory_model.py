import app.models as models


def test_memory_provenance_model_shape():
    assert hasattr(models, "MemoryProducer")
    assert hasattr(models, "MemoryVisibility")
    assert [member.value for member in models.MemoryProducer] == [
        "user", "system", "agent", "pipeline"
    ]
    assert [member.value for member in models.MemoryVisibility] == ["thread", "global"]
    assert models.MemoryVisibility.GLOBAL.value == "global"
    assert not hasattr(models.MemoryVisibility, "PROJECT")
    assert models.Memory.__table__.c.producer.type.name == "memory_producer"
    assert models.Memory.__table__.c.origin_thread_id.type.length == 100
    assert models.Memory.__table__.c.visibility.type.name == "memory_visibility"


def test_memory_handoff_model_shape():
    handoff = models.Memory.__table__.c.handoff
    assert isinstance(handoff.type, models.Boolean)
    assert handoff.default.arg is False
