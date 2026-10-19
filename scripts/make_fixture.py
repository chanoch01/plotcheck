"""Generate a small SYNTHETIC fixture in PlanIt's record shape for tests and CI.

None of these applications are real. Addresses, references and descriptions are made up;
only the field names and value formats follow https://www.planit.org.uk/dictionary/.

    python scripts/make_fixture.py  ->  tests/fixtures/sample_applications.jsonl.gz
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_applications.jsonl.gz"

CENTRES = {"Edinburgh": (55.9533, -3.1883), "Glasgow": (55.8642, -4.2518)}
DESCRIPTIONS = [
    "Formation of dormer to rear roof slope (synthetic example)",
    "Erection of single storey rear extension (synthetic example)",
    "Erection of two storey side extension (synthetic example)",
    "Installation of solar PV panels on front roof (synthetic example)",
    "Replacement windows to front elevation (synthetic example)",
    "Change of use from retail to cafe (synthetic example)",
    "Erection of garden room in rear garden (synthetic example)",
    "Erection of 4 dwellinghouses with access road (synthetic example)",
]
STATES = ["Permitted", "Conditions", "Rejected", "Withdrawn", "Undecided"]
DECISION_TEXT = {
    "Permitted": "Granted",
    "Conditions": "Granted subject to conditions",
    "Rejected": "Refused",
    "Withdrawn": "Withdrawn",
}


def make(n: int = 120, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    records = []
    for i in range(n):
        council = "Edinburgh" if i % 3 else "Glasgow"
        lat0, lng0 = CENTRES[council]
        start = date(2024, 1, 1) + timedelta(days=rng.randrange(0, 900))
        state = rng.choices(STATES, weights=[3, 4, 2, 1, 1])[0]
        decided = None if state == "Undecided" else start + timedelta(days=rng.randrange(35, 160))
        lat = round(lat0 + rng.uniform(-0.006, 0.006), 6)
        lng = round(lng0 + rng.uniform(-0.01, 0.01), 6)
        ref = f"{start:%y}/{10000 + i:05d}/SYN"
        records.append(
            {
                "name": f"{council}/{ref}",
                "uid": ref,
                "reference": None,
                "area_name": council,
                "area_id": 1 if council == "Edinburgh" else 2,
                "address": f"{i + 1} Example Street, {council}",
                "postcode": "ZZ99 9ZZ",  # placeholder, not a real postcode
                "description": rng.choice(DESCRIPTIONS),
                "start_date": start.isoformat(),
                "decided_date": decided.isoformat() if decided else None,
                "consulted_date": (start + timedelta(days=21)).isoformat(),
                "app_state": state,
                "app_type": "Full",
                "app_size": "Small",
                "location": {"type": "Point", "coordinates": [lng, lat]},
                "location_x": lng,
                "location_y": lat,
                "link": f"https://www.planit.org.uk/planapplic/{council}/{ref}/",
                "url": "https://example.invalid/synthetic",
                "last_changed": f"{(decided or start).isoformat()} 06:00:00",
                "last_different": f"{(decided or start).isoformat()} 05:00:00",
                "last_scraped": "2026-10-15 04:00:00",
                "other_fields": {
                    "decision": DECISION_TEXT.get(state),
                    "status": "Decided" if decided else "Pending consideration",
                    "ward_name": "Synthetic Ward",
                    "date_validated": start.isoformat(),
                },
            }
        )
    return records


if __name__ == "__main__":
    from plotcheck.landing import write_jsonl

    # Written through the real landing step, so the fixture carries provenance fields too.
    n = write_jsonl(make(), str(OUT), {"fixture": "synthetic", "seed": 7})
    print(f"Wrote {n} synthetic records to {OUT}")
