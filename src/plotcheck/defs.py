"""Dagster definitions: backfill by submission month, then nightly change capture.

* `planit_backfill`  council x month   history, by the month an application was submitted
* `planit_changes`   council x day     records whose council page changed that day
                                       (new applications, status updates, decisions)

Both land raw JSON first (provenance), then merge into Postgres on `name`.
Run locally with:  dagster dev

(No `from __future__ import annotations` here: Dagster inspects the real `context` type.)
"""

import os
from datetime import date

import dagster as dg

from plotcheck import landing, warehouse
from plotcheck.planit import PlanItClient

COUNCILS = ["Edinburgh", "Glasgow"]
HISTORY_START = "2021-01-01"

council_dim = dg.StaticPartitionsDefinition(COUNCILS)
backfill_partitions = dg.MultiPartitionsDefinition(
    {"council": council_dim, "month": dg.MonthlyPartitionsDefinition(start_date=HISTORY_START)}
)
change_partitions = dg.MultiPartitionsDefinition(
    {"council": council_dim, "day": dg.DailyPartitionsDefinition(start_date="2026-10-01")}
)


def _client() -> PlanItClient:
    return PlanItClient(os.environ["PLOTCHECK_USER_AGENT"])


def _landing_base() -> str:
    return os.environ.get("PLOTCHECK_LANDING_URL", "data/landing")


def _land_and_load(kind: str, council: str, period: str, records, query: dict) -> dict:
    url = landing.partition_url(_landing_base(), kind, council, period)
    n = landing.write_jsonl(records, url, query)
    meta: dict = {"records_landed": n, "landing_path": url}
    if n:
        info = warehouse.load_records(landing.read_jsonl(url))
        meta["load_ids"] = ", ".join(info.loads_ids)
    return meta


@dg.asset(
    partitions_def=backfill_partitions,
    group_name="ingest",
    kinds={"python", "postgres"},
    description="Applications submitted in one month, landed raw, then merged into Postgres.",
)
def planit_backfill(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    keys = context.partition_key.keys_by_dimension
    council, month_start = keys["council"], date.fromisoformat(keys["month"])
    period = month_start.strftime("%Y-%m")
    with _client() as client:
        records = client.applications_started_in_month(council, month_start.year, month_start.month)
        meta = _land_and_load(
            "backfill", council, period, records, {"auth": council, "month": period}
        )
    return dg.MaterializeResult(metadata=meta)


@dg.asset(
    partitions_def=change_partitions,
    group_name="ingest",
    kinds={"python", "postgres"},
    description="Applications whose council record changed on one day: new, updated or decided.",
)
def planit_changes(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    keys = context.partition_key.keys_by_dimension
    council, day = keys["council"], date.fromisoformat(keys["day"])
    with _client() as client:
        records = client.applications_changed_on(council, day)
        meta = _land_and_load(
            "changes", council, day.isoformat(), records, {"auth": council, "different": str(day)}
        )
    return dg.MaterializeResult(metadata=meta)


nightly_changes_job = dg.define_asset_job("nightly_changes", selection=[planit_changes])

defs = dg.Definitions(
    assets=[planit_backfill, planit_changes],
    jobs=[nightly_changes_job],
    schedules=[
        dg.build_schedule_from_partitioned_job(
            nightly_changes_job, hour_of_day=3, minute_of_hour=17
        )
    ],
)
