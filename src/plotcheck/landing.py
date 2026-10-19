"""The landing zone: raw API responses stored exactly as received, plus provenance.

Every record gets `_fetched_at` and `_source_query`, so any number in a report can be
traced back to the request that produced it. Files are written per partition and
overwritten on re-run, which makes each partition idempotent.

The base URL can be a local folder (default) or Azure Blob Storage, e.g.
`abfs://landing@<account>.dfs.core.windows.net` (needs the `adlfs` package).
"""

from __future__ import annotations

import gzip
import json
import posixpath
import re
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import Any

from fsspec.core import url_to_fs


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def partition_url(base: str, kind: str, council: str, period: str) -> str:
    """e.g. data/landing/planit/backfill/council=edinburgh/period=2026-09/applications.jsonl.gz"""
    return (
        f"{base.rstrip('/')}/planit/{kind}/council={slug(council)}/period={period}"
        "/applications.jsonl.gz"
    )


def write_jsonl(records: Iterable[dict[str, Any]], url: str, source_query: dict[str, Any]) -> int:
    fs, path = url_to_fs(url)
    fs.makedirs(posixpath.dirname(path), exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat(timespec="seconds")
    query = json.dumps(source_query, sort_keys=True)
    count = 0
    with fs.open(path, "wb") as raw, gzip.open(raw, "wt", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps({**record, "_fetched_at": fetched_at, "_source_query": query}))
            out.write("\n")
            count += 1
    return count


def read_jsonl(url: str) -> Iterator[dict[str, Any]]:
    fs, path = url_to_fs(url)
    with fs.open(path, "rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as src:
        for line in src:
            if line.strip():
                yield json.loads(line)
