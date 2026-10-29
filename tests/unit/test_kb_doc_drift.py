from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import kb_doc_drift  # noqa: E402

COMMUNES = ["Las Condes", "Ñuñoa", "Lo Barnechea", "La Reina", "Peñalolén", "Colina", "Huechuraba"]
WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def findings_for(tmp_path: Path, text: str):
    (tmp_path / "synthetic.md").write_text(text, encoding="utf-8")
    return kb_doc_drift.find_duplicated_values(
        tmp_path, communes=COMMUNES, weekdays=WEEKDAYS
    )


def test_detects_each_duplicable_value_class_with_line_numbers(tmp_path):
    findings = findings_for(
        tmp_path,
        "Ñuñoa\nAtención de 09:00 a 18:00\nPrecio $30.000\n"
        "Dura 45 y 90 minutos\nDe lunes hasta sábado\n",
    )

    assert {(item.kind, item.value, item.line) for item in findings} == {
        ("communes", "Ñuñoa", 1),
        ("clock", "09:00", 2),
        ("clock", "18:00", 2),
        ("price", "$30.000", 3),
        ("duration", "45 minutos", 4),
        ("duration", "90 minutos", 4),
        ("weekday_range", "lunes hasta sábado", 5),
    }
    assert {item.source_id for item in findings} == {"synthetic"}


def test_communes_match_ignoring_accents_and_case(tmp_path):
    findings = findings_for(tmp_path, "Atendemos en NUNOa.\n")

    assert [(item.kind, item.value, item.line) for item in findings] == [
        ("communes", "NUNOa", 1)
    ]


def test_baseline_tolerates_existing_findings_but_reports_new_ones():
    tolerated = kb_doc_drift.Finding("one", "clock", "09:00", 1)
    new = kb_doc_drift.Finding("two", "price", "$30.000", 2)

    tolerated_findings, new_findings = kb_doc_drift.split_findings(
        [tolerated, new], {"one|clock|09:00"}
    )

    assert tolerated_findings == [tolerated]
    assert new_findings == [new]


def test_lumat_identidad_has_no_drift_findings():
    findings = kb_doc_drift.find_duplicated_values(
        kb_doc_drift.KB_DIR, communes=COMMUNES, weekdays=WEEKDAYS
    )

    assert not [item for item in findings if item.source_id == "lumat-identidad"]


def test_real_kb_findings_match_checked_in_baseline():
    config = {
        "communes": COMMUNES,
        "weekdays": WEEKDAYS,
    }
    findings = kb_doc_drift.find_duplicated_values(
        kb_doc_drift.KB_DIR, **config
    )
    baseline = json.loads(kb_doc_drift.BASELINE_PATH.read_text(encoding="utf-8"))
    tolerated, new = kb_doc_drift.split_findings(findings, set(baseline))

    assert tolerated == findings
    assert new == []
    assert baseline == sorted(baseline)


def test_cli_returns_zero_when_only_baseline_findings_remain(tmp_path, monkeypatch, capsys):
    (tmp_path / "synthetic.md").write_text("Atención a las 09:00.\n", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text('["synthetic|clock|09:00"]\n', encoding="utf-8")
    monkeypatch.setattr(kb_doc_drift, "KB_DIR", tmp_path)
    monkeypatch.setattr(kb_doc_drift, "BASELINE_PATH", baseline_path)
    monkeypatch.setattr(kb_doc_drift, "load_config_values", lambda: (COMMUNES, WEEKDAYS))

    assert kb_doc_drift.main([]) == 0
    assert "tolerados: 1" in capsys.readouterr().out


def test_cli_returns_one_when_it_finds_a_new_value(tmp_path, monkeypatch, capsys):
    (tmp_path / "synthetic.md").write_text("Atención a las 09:00.\nPrecio $30.000.\n", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text('["synthetic|clock|09:00"]\n', encoding="utf-8")
    monkeypatch.setattr(kb_doc_drift, "KB_DIR", tmp_path)
    monkeypatch.setattr(kb_doc_drift, "BASELINE_PATH", baseline_path)
    monkeypatch.setattr(kb_doc_drift, "load_config_values", lambda: (COMMUNES, WEEKDAYS))

    assert kb_doc_drift.main([]) == 1
    output = capsys.readouterr().out
    assert "tolerados: 1" in output
    assert "price · $30.000" in output


def test_seed_hook_is_advisory_and_never_raises(monkeypatch, capsys):
    """The seed hook prints, and a broken report cannot change the seed's result."""
    import seed_kb_docs

    monkeypatch.setattr(
        kb_doc_drift, "summarize", lambda **_: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    seed_kb_docs._print_drift_summary()  # must not raise
    assert "reporte no disponible" in capsys.readouterr().out


def test_summarize_and_the_cli_agree_on_the_baseline(monkeypatch, tmp_path):
    """One seam: the seed report and the CLI cannot disagree about what is new."""
    (tmp_path / "synthetic.md").write_text("Atención a las 09:00.\n", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text('["synthetic|clock|09:00"]\n', encoding="utf-8")
    monkeypatch.setattr(kb_doc_drift, "load_config_values", lambda: (COMMUNES, WEEKDAYS))

    tolerated, new = kb_doc_drift.summarize(kb_dir=tmp_path, baseline_path=baseline_path)

    assert [finding.key for finding in tolerated] == ["synthetic|clock|09:00"]
    assert new == []


def test_cli_runs_without_a_configured_database():
    """The control guards prose, not data: it must run on a bare checkout.

    Regression this pins: resolving the coverage names imports the app config,
    which is fail-fast about `database_url`, so the env-free run crashed instead
    of reporting.
    """
    import os
    import subprocess

    env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "kb_doc_drift.py")],
        cwd=SCRIPTS.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr
    assert "drift · tolerados:" in result.stdout


def test_the_shipped_kb_restates_no_configured_value():
    """S7: the shipped documents keep the policy, never the configured values.

    The values are answered from `settings` (see `configured_answers`), so a
    document that restates them is a second source of truth. `scripts/kb_doc_drift.py`
    stays the gate that consults the live configuration; this test pins the state
    the repository ships, against the default communes.
    """
    from app.services.settings import DEFAULT_COVERAGE_COMMUNES

    findings = kb_doc_drift.find_duplicated_values(
        kb_doc_drift.KB_DIR, communes=DEFAULT_COVERAGE_COMMUNES
    )

    assert [finding.key for finding in findings] == []


def test_the_shipped_baseline_is_empty():
    """Tolerance zero: with an empty baseline every finding fails the control."""
    assert kb_doc_drift.read_baseline(kb_doc_drift.BASELINE_PATH) == set()
