"""Work-type classification: the regex baseline.

Week 3 compares this against an LLM with structured output on ~300 hand-labelled
descriptions. Keep the baseline honest: rules are checked in order, first match wins,
and anything unmatched is `other` rather than a guess.
"""

from __future__ import annotations

import re

WORK_TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("dormer", re.compile(r"\bdormers?\b")),
    ("loft_conversion", re.compile(r"\bloft\b|\broof ?lights?\b|\bvelux\b")),
    (
        "new_dwellings",
        re.compile(r"\berect\w*\b.{0,40}\b(dwelling\w*|houses?|flats?)\b|\bnew build\b"),
    ),
    ("two_storey_extension", re.compile(r"\b(two|2|double)[- ]stor(e)?y\b.{0,30}\bextension")),
    (
        "single_storey_extension",
        re.compile(r"\b(single|one|1)[- ]stor(e)?y\b.{0,30}\bextension|\brear extension\b"),
    ),
    # After the extensions ("extension following demolition of..." is an extension),
    # before outbuildings ("demolition of garage" is a demolition).
    ("demolition", re.compile(r"\bdemoli")),
    ("conservatory_porch", re.compile(r"\bconservatory\b|\bporch\b|\bsun ?room\b")),
    ("change_of_use", re.compile(r"\bchange of use\b|\bshort[- ]term let\b|\bstl\b")),
    ("solar", re.compile(r"\bsolar\b|\bphotovoltaic\b|\bpv panels?\b")),
    (
        "windows_doors",
        re.compile(r"\b(replace\w*|new|install\w*)\b.{0,30}\b(windows?|doors?)\b|\bwindows\b"),
    ),
    (
        "outbuilding",
        re.compile(r"\b(garage|outbuilding|summer ?house|garden (room|office)|shed|annexe)\b"),
    ),
    ("advertising", re.compile(r"\badvert\w*\b|\bsignage\b|\billuminated signs?\b")),
    ("trees", re.compile(r"\btrees?\b|\btpo\b|\bfell(ing)?\b|\bhedge\b")),
]

LABELS = [label for label, _ in WORK_TYPES] + ["other"]


def classify(description: str | None) -> str:
    text = " ".join((description or "").lower().split())
    for label, pattern in WORK_TYPES:
        if pattern.search(text):
            return label
    return "other"
