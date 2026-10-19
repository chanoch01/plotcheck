"""Point-in-time comparables: the leakage rule, in one place.

A comparable for an application must have been *decided before the application was
submitted*. Using anything decided later lets the model see the future, which looks
great in testing and fails in production. The dbt model `int_comparable_pairs`
implements the same rule in SQL, and a dbt test checks it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class Application:
    application_id: str
    submitted_on: date
    lat: float
    lng: float
    work_type: str
    decided_on: date | None = None
    approved: bool | None = None  # None = withdrawn, undecided or unknown


def distance_m(a: Application, b: Application) -> float:
    """Great-circle distance in metres (haversine)."""
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def comparables(
    target: Application,
    history: list[Application],
    *,
    radius_m: float = 500,
    same_work_type: bool = True,
) -> list[Application]:
    return [
        h
        for h in history
        if h.application_id != target.application_id
        and h.decided_on is not None
        and h.decided_on < target.submitted_on  # the point-in-time rule
        and h.approved is not None
        and (not same_work_type or h.work_type == target.work_type)
        and distance_m(target, h) <= radius_m
    ]


def approval_summary(comps: list[Application], *, min_count: int = 5) -> dict[str, object]:
    """Summarise comparables, declining to estimate when there are too few."""
    n = len(comps)
    if n < min_count:
        return {"n": n, "approval_rate": None, "reason": f"fewer than {min_count} comparables"}
    approved = sum(1 for c in comps if c.approved)
    return {"n": n, "approval_rate": approved / n, "reason": None}
