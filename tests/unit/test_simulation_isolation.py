from pathlib import Path


def test_simulation_migration_adds_default_false_flags():
    sql = " ".join(Path("db/migrations/071_simulation_isolation.sql").read_text().split())
    assert "ALTER TABLE conversations ADD COLUMN simulated boolean NOT NULL DEFAULT false" in sql
    assert "ALTER TABLE cases ADD COLUMN simulated boolean NOT NULL DEFAULT false" in sql


def test_simulated_models_have_shared_flag_and_exclusion_predicate():
    from app.models import Case, Conversation
    from app.services.cases import not_simulated_expr

    assert Case.simulated is not None
    assert Conversation.simulated is not None
    assert "simulated IS false" in str(not_simulated_expr(Conversation).compile(compile_kwargs={"literal_binds": True}))
    assert "simulated IS false" in str(not_simulated_expr(Case).compile(compile_kwargs={"literal_binds": True}))
