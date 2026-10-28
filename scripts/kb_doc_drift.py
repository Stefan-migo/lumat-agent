"""Static guard for configuration-owned values repeated in customer KB prose."""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
KB_DIR = _REPO_ROOT / "docs" / "kb"
BASELINE_PATH = KB_DIR / "drift-baseline.json"

WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_CLOCK = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)")
_PRICE = re.compile(r"\$\s*\d+(?:[.,]\d{3})*(?:[.,]\d+)?")
_DURATION = re.compile(
    r"(?<![:\d])\b(\d+(?:\s+(?:y|o)\s+\d+)*)\s+(minutos?|horas?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class Finding:
    source_id: str
    kind: str
    value: str
    line: int

    @property
    def key(self) -> str:
        return f"{self.source_id}|{self.kind}|{self.value}"


def _fold_with_positions(text: str) -> tuple[str, list[int]]:
    folded: list[str] = []
    positions: list[int] = []
    for index, character in enumerate(text):
        normalized = unicodedata.normalize("NFKD", character.casefold())
        for part in normalized:
            if not unicodedata.combining(part):
                folded.append(part)
                positions.append(index)
    return "".join(folded), positions


def _commune_matches(line: str, communes: Iterable[str]) -> list[str]:
    folded_line, positions = _fold_with_positions(line)
    matches: list[tuple[int, int, str]] = []
    for commune in sorted(set(communes), key=len, reverse=True):
        folded_commune, _ = _fold_with_positions(commune.strip())
        if not folded_commune:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(folded_commune)}(?!\w)")
        for match in pattern.finditer(folded_line):
            start = positions[match.start()]
            end = positions[match.end() - 1] + 1
            matches.append((start, end, line[start:end]))
    # Prefer the longest configured name where entries overlap (e.g. a name
    # containing another commune), while retaining repeated independent mentions.
    selected: list[tuple[int, int, str]] = []
    for candidate in sorted(matches, key=lambda item: (item[0], -(item[1] - item[0]))):
        if selected and candidate[0] < selected[-1][1]:
            continue
        selected.append(candidate)
    return [value for _, _, value in selected]


def find_duplicated_values(
    kb_dir: Path,
    *,
    communes: Iterable[str],
    weekdays: Iterable[str] = WEEKDAYS,
) -> list[Finding]:
    """Find configuration-like values in each top-level Markdown KB document."""
    weekday_names = tuple(weekdays)
    range_pattern = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(day) for day in sorted(weekday_names, key=len, reverse=True))
        + r")\s+(?:a|hasta)\s+(" + "|".join(re.escape(day) for day in sorted(weekday_names, key=len, reverse=True))
        + r")(?!\w)",
        re.IGNORECASE,
    )
    findings: list[Finding] = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        source_id = path.stem
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            candidates: list[tuple[str, str]] = [("communes", value) for value in _commune_matches(line, communes)]
            candidates.extend(("clock", match.group()) for match in _CLOCK.finditer(line))
            candidates.extend(("price", match.group()) for match in _PRICE.finditer(line))
            for match in _DURATION.finditer(line):
                unit = match.group(2)
                candidates.extend(
                    ("duration", f"{number} {unit}")
                    for number in re.findall(r"\d+", match.group(1))
                )
            candidates.extend(("weekday_range", match.group()) for match in range_pattern.finditer(line))
            findings.extend(Finding(source_id, kind, value, line_number) for kind, value in candidates)
    return sorted(findings)


def split_findings(
    findings: Iterable[Finding], baseline: set[str]
) -> tuple[list[Finding], list[Finding]]:
    """Return tolerated findings and findings whose keys are absent from baseline."""
    tolerated: list[Finding] = []
    new: list[Finding] = []
    for finding in findings:
        (tolerated if finding.key in baseline else new).append(finding)
    return tolerated, new


def finding_keys(findings: Iterable[Finding]) -> list[str]:
    return sorted({finding.key for finding in findings})


def load_config_values() -> tuple[list[str], tuple[str, ...]]:
    """Resolve the coverage names the documents must not restate.

    The names come from `app.services.settings` and from nowhere else: a local
    copy would be the very duplication this control exists to catch, and it
    would go stale the day the owner adds a commune.

    The app config is fail-fast, so importing it needs a `database_url` even
    though reading a constant opens no connection. When the caller has none, an
    inert placeholder stands in (the same device `tests/unit/conftest.py` uses)
    and the built-in defaults are the answer; a real one is queried, so the check
    can never disagree with the deployed configuration.
    """
    configured_url = os.environ.get("DATABASE_URL")
    os.environ.setdefault("DATABASE_URL", "sqlite://")

    from seed_kb_docs import ensure_dev_env

    ensure_dev_env()
    from app.services.settings import DEFAULT_COVERAGE_COMMUNES, get_coverage_communes

    if configured_url:
        from app.db import session_scope

        with session_scope() as session:
            return get_coverage_communes(session), WEEKDAYS
    return list(DEFAULT_COVERAGE_COMMUNES), WEEKDAYS


def read_baseline(path: Path) -> set[str]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"invalid drift baseline: {path}")
    return set(values)


def summarize(
    *,
    kb_dir: Path = KB_DIR,
    baseline_path: Path = BASELINE_PATH,
) -> tuple[list[Finding], list[Finding]]:
    """Findings this repository tolerates and findings it does not, in one call.

    The seed report and the CLI share this seam so neither can drift from the
    other's idea of what the baseline means.
    """
    communes, weekdays = load_config_values()
    findings = find_duplicated_values(kb_dir, communes=communes, weekdays=weekdays)
    baseline = read_baseline(baseline_path) if baseline_path.exists() else set()
    return split_findings(findings, baseline)


def _print_findings(findings: Iterable[Finding]) -> None:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.source_id].append(finding)
    for source_id in sorted(grouped):
        print(f"{source_id}:")
        for finding in grouped[source_id]:
            print(f"  {finding.kind} · {finding.value} · línea {finding.line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check configuration-owned values duplicated in docs/kb.")
    parser.add_argument("--update-baseline", action="store_true", help="replace the accepted-finding baseline")
    args = parser.parse_args(argv)

    communes, weekdays = load_config_values()
    findings = find_duplicated_values(KB_DIR, communes=communes, weekdays=weekdays)
    if args.update_baseline:
        BASELINE_PATH.write_text(
            json.dumps(finding_keys(findings), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    baseline = read_baseline(BASELINE_PATH) if BASELINE_PATH.exists() else set()
    tolerated, new = split_findings(findings, baseline)
    keys = len({finding.key for finding in tolerated})
    print(f"drift · tolerados: {len(tolerated)} hallazgos ({keys} claves) · nuevos: {len(new)}")
    if tolerated:
        print("drift · hallazgos tolerados:")
        _print_findings(tolerated)
    if new:
        print("drift · hallazgos nuevos:")
        _print_findings(new)
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
