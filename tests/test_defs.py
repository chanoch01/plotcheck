from __future__ import annotations

import pytest

dg = pytest.importorskip("dagster")


def test_definitions_load_and_partitions_cover_both_councils():
    from plotcheck.defs import backfill_partitions, defs

    assert defs.resolve_job_def("nightly_changes") is not None
    keys = backfill_partitions.get_partition_keys()
    councils = {k.keys_by_dimension["council"] for k in keys}
    assert councils == {"Edinburgh", "Glasgow"}
