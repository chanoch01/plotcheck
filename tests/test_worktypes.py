from __future__ import annotations

import pytest

from plotcheck.worktypes import LABELS, classify


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Formation of dormer to rear roof slope", "dormer"),
        ("Loft conversion with dormer windows", "dormer"),  # dormer outranks loft
        ("Loft conversion including 3 rooflights", "loft_conversion"),
        ("Erection of two-storey side extension", "two_storey_extension"),
        ("Proposed single storey rear extension", "single_storey_extension"),
        ("Erection of 12 dwellinghouses and associated works", "new_dwellings"),
        ("Change of use from shop to short term let", "change_of_use"),
        ("Installation of solar photovoltaic panels", "solar"),
        ("Replacement windows to front elevation", "windows_doors"),
        ("Erection of garden room", "outbuilding"),
        ("Demolition of existing garage", "demolition"),  # demolition is the work
        ("Rear extension following demolition of conservatory", "single_storey_extension"),
        ("Display of illuminated signage", "advertising"),
        ("Fell two trees covered by TPO", "trees"),
        ("Alterations to shopfront", "other"),
        ("", "other"),
        (None, "other"),
    ],
)
def test_classify(description, expected):
    assert classify(description) == expected


def test_every_label_is_known():
    assert classify("anything at all") in LABELS
