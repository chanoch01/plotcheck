"""Load landed records into Postgres (`raw.planit_applications`) with dlt.

Records are merged on PlanIt's nationally unique `name`, so re-loading a partition
updates rows instead of duplicating them. dlt flattens `other_fields` into columns
such as `other_fields__decision`.

Credentials come from the environment, e.g.
DESTINATION__POSTGRES__CREDENTIALS=postgresql://plotcheck:plotcheck@localhost:5432/plotcheck
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

# GeoJSON `location` duplicates location_x / location_y and would become a child table.
DROP_FIELDS = {"location"}

# dlt only creates a column once it sees a non-null value. A quiet day where nothing was
# decided would then leave `decided_date` missing and break dbt staging, so every column
# the staging model reads is declared up front.
TEXT_COLUMNS = """
    uid reference area_name address postcode description app_type app_state app_size
    start_date decided_date consulted_date link url last_different last_scraped
    _fetched_at _source_query other_fields__decision other_fields__status other_fields__ward_name
""".split()  # noqa: SIM905  (easier to scan than a 21-line list)

COLUMN_HINTS: dict[str, dict[str, str]] = {
    **{name: {"data_type": "text"} for name in TEXT_COLUMNS},
    "location_x": {"data_type": "double"},
    "location_y": {"data_type": "double"},
}


def prepare(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in DROP_FIELDS}


def load_records(
    records: Iterable[dict[str, Any]],
    *,
    pipeline_name: str = "plotcheck",
    dataset_name: str = "raw",
    destination: str = "postgres",
):
    import dlt  # imported lazily so the core package works without the pipeline extra

    @dlt.resource(
        name="planit_applications",
        write_disposition="merge",
        primary_key="name",
        columns=COLUMN_HINTS,
    )
    def planit_applications():
        for record in records:
            yield prepare(record)

    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name, destination=destination, dataset_name=dataset_name
    )
    return pipeline.run(planit_applications())
