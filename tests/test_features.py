from __future__ import annotations

from datetime import date

from plotcheck.features import Application, approval_summary, comparables, distance_m

TARGET = Application("T", date(2026, 3, 1), 55.9533, -3.1883, "dormer")


def app(app_id, decided, approved=True, d_lat=0.0, work_type="dormer"):
    return Application(
        app_id, date(2025, 6, 1), 55.9533 + d_lat, -3.1883, work_type, decided, approved
    )


def test_only_decisions_before_submission_count():
    history = [
        app("before", date(2026, 2, 28)),
        app("same_day", date(2026, 3, 1)),  # decided the day it was submitted: not knowable
        app("after", date(2026, 4, 1)),
    ]
    assert [c.application_id for c in comparables(TARGET, history)] == ["before"]


def test_excludes_far_undecided_withdrawn_other_types_and_itself():
    history = [
        app("near", date(2025, 9, 1)),
        app("far", date(2025, 9, 1), d_lat=0.01),  # about 1.1 km north
        app("undecided", None, approved=None),
        app("withdrawn", date(2025, 9, 1), approved=None),
        app("solar", date(2025, 9, 1), work_type="solar"),
        Application("T", date(2025, 1, 1), 55.9533, -3.1883, "dormer", date(2025, 2, 1), True),
    ]
    assert [c.application_id for c in comparables(TARGET, history)] == ["near"]
    assert len(comparables(TARGET, history, same_work_type=False)) == 2


def test_distance_is_roughly_right():
    north = Application("N", date(2026, 1, 1), 55.9533 + 0.01, -3.1883, "dormer")
    assert 1100 < distance_m(TARGET, north) < 1125


def test_summary_declines_below_minimum():
    few = [app(str(i), date(2025, 1, 1)) for i in range(3)]
    assert approval_summary(few)["approval_rate"] is None

    many = few + [app(f"r{i}", date(2025, 1, 1), approved=False) for i in range(2)]
    summary = approval_summary(many)
    assert summary["n"] == 5 and summary["approval_rate"] == 0.6
