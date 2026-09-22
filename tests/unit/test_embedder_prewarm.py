import logging
import asyncio
import sys
import threading
import time
import types

from app.services import kb


def test_prewarm_does_not_block_boot_on_a_slow_load(monkeypatch):
    from app import main

    started = threading.Event()
    unfinished = threading.Event()

    def slow_load():
        started.set()
        unfinished.wait()

    monkeypatch.setattr(main, "get_settings", lambda: types.SimpleNamespace(embed_prewarm=True))
    monkeypatch.setattr(kb, "get_embedder", slow_load)

    start = time.monotonic()
    thread = main.start_embedder_prewarm()
    elapsed = time.monotonic() - start

    assert thread is not None
    assert elapsed < 1
    assert started.wait(timeout=1)
    assert not unfinished.is_set()

    for sweep_name in (
        "reset_stale_processing",
        "sweep_received",
        "run_notification_sweep",
    ):
        monkeypatch.setattr(main, sweep_name, lambda: None)
    monkeypatch.setattr(main, "reap_orphaned_runs", lambda *_args: None)
    boot_yielded = threading.Event()

    async def run_lifespan():
        async with main.lifespan(None):
            boot_yielded.set()

    boot_thread = threading.Thread(target=lambda: asyncio.run(run_lifespan()))
    boot_thread.start()
    try:
        assert boot_yielded.wait(timeout=1), "lifespan waited for the prewarm"
    finally:
        unfinished.set()
        thread.join(timeout=1)
        boot_thread.join(timeout=1)

    assert not thread.is_alive()
    assert not boot_thread.is_alive()


def test_prewarm_failure_is_logged_and_swallowed(monkeypatch, caplog):
    from app import main

    def fail_load():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(kb, "get_embedder", fail_load)

    with caplog.at_level(logging.ERROR):
        main._prewarm_embedder()

    assert any("embedder prewarm failed" in record.message for record in caplog.records)


def test_prewarm_is_off_when_the_setting_is_off(monkeypatch):
    from app import main

    called = False

    def fail_if_called():
        nonlocal called
        called = True

    monkeypatch.setattr(main, "get_settings", lambda: types.SimpleNamespace(embed_prewarm=False))
    monkeypatch.setattr(kb, "get_embedder", fail_if_called)

    assert main.start_embedder_prewarm() is None
    assert not called


def test_get_embedder_constructs_once_under_concurrency(monkeypatch):
    calls = 0
    calls_lock = threading.Lock()

    class FakeEmbedder:
        pass

    def construct(**kwargs):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.05)
        return FakeEmbedder()

    monkeypatch.setitem(sys.modules, "fastembed", types.SimpleNamespace(TextEmbedding=construct))
    monkeypatch.setattr(kb, "_embedder", None)

    barrier = threading.Barrier(5)
    results = []
    errors = []

    def load():
        try:
            barrier.wait()
            results.append(kb.get_embedder())
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=load) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert not errors
    assert calls == 1
    assert len(results) == 5
    assert all(result is results[0] for result in results)
