from __future__ import annotations

import json

from plotcheck import landing


def test_partition_url_is_stable_and_slugged():
    url = landing.partition_url("data/landing/", "backfill", "City of Edinburgh", "2026-09")
    assert url == (
        "data/landing/planit/backfill/council=city-of-edinburgh/period=2026-09"
        "/applications.jsonl.gz"
    )


def test_roundtrip_adds_provenance(tmp_path):
    url = str(tmp_path / "a" / "b" / "applications.jsonl.gz")
    records = [{"name": "Edinburgh/1", "description": "Dormer"}, {"name": "Edinburgh/2"}]
    n = landing.write_jsonl(records, url, {"auth": "Edinburgh", "month": "2026-09"})

    back = list(landing.read_jsonl(url))
    assert n == 2 and [r["name"] for r in back] == ["Edinburgh/1", "Edinburgh/2"]
    assert all(r["_fetched_at"] for r in back)
    assert json.loads(back[0]["_source_query"]) == {"auth": "Edinburgh", "month": "2026-09"}


def test_rewriting_a_partition_replaces_it(tmp_path):
    url = str(tmp_path / "applications.jsonl.gz")
    landing.write_jsonl([{"name": "a"}, {"name": "b"}], url, {})
    landing.write_jsonl([{"name": "a"}], url, {})
    assert [r["name"] for r in landing.read_jsonl(url)] == ["a"]
