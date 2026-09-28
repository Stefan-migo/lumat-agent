from app.ops import sweep


def test_sweep_cli_passes_limit_to_bounded_runner(monkeypatch):
    calls = []
    monkeypatch.setattr(sweep, "run", lambda limit=50: calls.append(limit) or 3)
    assert sweep.main(["--limit", "7"]) == 0
    assert calls == [7]
