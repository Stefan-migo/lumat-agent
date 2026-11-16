#!/usr/bin/env python3
"""Build the street-master extract the address validator reads.

Source: the Instituto Nacional de Estadísticas (INE) publishes the *Maestro de
Calles* as a public ArcGIS feature service — the official street axes with the
numbering each block actually carries (`INI_IZQ`, `INI_DER`, `TER_IZQ`,
`TER_DER`). It is the same layer IDE Chile hands out as a shapefile, so the
extract is reproducible without paying a geocoder and without an API key.

The script fetches only the communes this business services (by default
`coverage.communes`: the owner can configure it, and a commune the master does
not cover simply yields no reference — it must never read as "street does not
exist"), keeps the numbering ranges, drops the geometry (validation needs the
range, not the shape), and writes a gzipped JSON keyed by commune and
normalised street name.

Usage:
    python scripts/build_callejero.py                 # fetch and write
    python scripts/build_callejero.py --dry-run       # report, write nothing

The output is committed because the validator runs offline and its tests must
be deterministic. Regenerate it when the owner adds a commune to coverage.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "app" / "data" / "callejero" / "maestro.json.gz"

SERVICE = (
    "https://services5.arcgis.com/hUyD8u3TeZLKPe4T/arcgis/rest/services"
    "/Maestro_Calles/FeatureServer/0"
)
SOURCE_TITLE = "Maestro de Calles — Instituto Nacional de Estadísticas (INE) de Chile"
SOURCE_LICENSE = "Creative Commons Atribución 4.0 Internacional (CC BY 4.0)"
SOURCE_URL = "https://www.ine.gob.cl/herramientas/portal-de-mapas/geodatos-abiertos"

FIELDS = ("COMUNA", "NOMBRE_MAESTRO", "INI_IZQ", "INI_DER", "TER_IZQ", "TER_DER")
PAGE_SIZE = 2000
_RETRIES = 3

# The shipped default, duplicated on purpose: importing `app.services.settings`
# pulls `app.config`, which demands the whole runtime environment (database URL,
# Meta token, panel secret) and would make this build step unrunnable outside a
# configured instance. `tests/unit/test_callejero.py` asserts this tuple equals
# `DEFAULT_COVERAGE_COMMUNES`, so the duplication cannot drift unnoticed.
DEFAULT_COMMUNES = [
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
]


def normalize_street(name: str) -> str:
    """Uppercase, accent-free, single-spaced street key.

    The same normalization the validator uses, kept byte-identical on purpose:
    if these two drift, every street lookup misses. `app/services/callejero.py`
    owns the runtime copy and `tests/unit/test_callejero.py` pins the two
    together.
    """
    folded = unicodedata.normalize("NFD", name)
    plain = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    cleaned = plain.upper().replace(".", " ").replace(",", " ")
    return " ".join(cleaned.split())


def _fetch_page(where: str, offset: int) -> dict:
    params = {
        "where": where,
        "outFields": ",".join(FIELDS),
        "returnGeometry": "false",
        "orderByFields": "OBJECTID",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
        "f": "json",
    }
    url = f"{SERVICE}/query?{urllib.parse.urlencode(params)}"
    last: Exception | None = None
    for attempt in range(1, _RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(f"service error: {payload['error']}")
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last = error
            if attempt < _RETRIES:
                time.sleep(2 * attempt)
    raise SystemExit(f"could not read the street master: {last}")


def _ranges(attributes: dict) -> list[list[int]]:
    """The numbering ranges a block carries, left and right side together.

    A side whose `INI` equals its `TER` is a single door, and a side whose
    `TER` is 0 carries no numbering at all (the master leaves it empty). Both
    are dropped: the first adds nothing to a range check, the second would
    wrongly claim every number on that side.
    """
    found: list[list[int]] = []
    for start_key, end_key in (("INI_IZQ", "TER_IZQ"), ("INI_DER", "TER_DER")):
        start = attributes.get(start_key) or 0
        end = attributes.get(end_key) or 0
        if start > 0 and end >= start and end - start >= 1:
            found.append([int(start), int(end)])
    return found


def _communes_in_service(communes: list[str]) -> list[str]:
    """The communes the master really covers, spelled the way it spells them.

    The service names communes in uppercase with accents (`ÑUÑOA`,
    `PEÑALOLÉN`), so the query is built from the master's own spelling. A
    commune missing from the master is reported, never guessed: inventing a
    spelling would return zero rows and read as "no streets here".
    """
    params = {
        "where": "1=1",
        "outFields": "COMUNA",
        "returnGeometry": "false",
        "returnDistinctValues": "true",
        "f": "json",
    }
    url = f"{SERVICE}/query?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    available = {
        (feature["attributes"].get("COMUNA") or "")
        for feature in payload.get("features", [])
    }
    by_key = {normalize_street(name): name for name in available}
    resolved: list[str] = []
    for name in communes:
        spelled = by_key.get(normalize_street(name))
        if spelled is not None:
            resolved.append(spelled)
    return resolved


def build(communes: list[str], *, dry_run: bool) -> dict:
    covered = _communes_in_service(communes)
    wanted = {normalize_street(name) for name in covered}
    where = " OR ".join(f"COMUNA='{name}'" for name in covered)
    if not covered:
        raise SystemExit("the master covers none of the requested communes")

    streets: dict[str, dict[str, dict]] = {name: {} for name in covered}
    seen_comunas: set[str] = set()
    segments = 0
    offset = 0
    while True:
        page = _fetch_page(where, offset)
        features = page.get("features", [])
        if not features:
            break
        for feature in features:
            attributes = feature["attributes"]
            comuna = attributes.get("COMUNA") or ""
            if normalize_street(comuna) not in wanted:
                continue
            seen_comunas.add(comuna)
            name = (attributes.get("NOMBRE_MAESTRO") or "").strip()
            key = normalize_street(name)
            if not key:
                continue
            segments += 1
            found = _ranges(attributes)
            if not found:
                # The street exists in this commune even without numbering:
                # that is a fact the validator needs, separate from the number.
                streets[comuna].setdefault(key, {"name": name, "ranges": []})
                continue
            entry = streets[comuna].setdefault(key, {"name": name, "ranges": []})
            for pair in found:
                if pair not in entry["ranges"]:
                    entry["ranges"].append(pair)
        offset += len(features)
        if not page.get("exceededTransferLimit", True) and len(features) < PAGE_SIZE:
            break
        if offset > 400_000:
            raise SystemExit("the master returned more rows than expected; aborting")

    for entry_map in streets.values():
        for entry in entry_map.values():
            entry["ranges"].sort()

    seen_keys = {normalize_street(name) for name in seen_comunas}
    missing = [name for name in communes if normalize_street(name) not in seen_keys]
    return {
        "generated_at": date.today().isoformat(),
        "source": {"title": SOURCE_TITLE, "url": SOURCE_URL, "license": SOURCE_LICENSE},
        "communes_requested": communes,
        "communes_covered": sorted(seen_comunas),
        "communes_without_reference": missing,
        "segments": segments,
        "streets": streets,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--communes",
        nargs="*",
        default=None,
        help="communes to extract (default: coverage.communes defaults)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    # The shipped default is the extract's baseline; the owner's runtime
    # `coverage.communes` may be wider, and the script says so instead of
    # silently shipping a narrower index than the bot accepts.
    communes = args.communes or list(DEFAULT_COMMUNES)
    payload = build(communes, dry_run=args.dry_run)

    print(f"communes requested : {len(payload['communes_requested'])}")
    print(f"communes covered   : {', '.join(payload['communes_covered']) or '(none)'}")
    print(f"without reference  : {', '.join(payload['communes_without_reference']) or '(none)'}")
    print(f"segments with data : {payload['segments']}")
    print(f"streets per commune: { {k: len(v) for k, v in payload['streets'].items()} }")

    if args.dry_run:
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with gzip.open(args.output, "wt", encoding="utf-8", compresslevel=9) as handle:
        handle.write(raw)
    print(f"written            : {args.output.relative_to(REPO_ROOT)} ({len(raw)} bytes raw)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
