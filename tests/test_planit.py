from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from plotcheck.planit import PlanItClient, PlanItError, month_bounds

UA = "PlotCheck/0.1 (+https://github.com/example/plotcheck)"


def make_client(handler, **kwargs):
    sleeps: list[float] = []
    client = PlanItClient(
        UA,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        min_interval_s=0,
        **kwargs,
    )
    return client, sleeps


def qs(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}


def test_pages_until_total_with_stable_sort_and_user_agent():
    seen = []

    def handler(request):
        q = qs(request)
        seen.append(q)
        assert request.headers["User-Agent"] == UA
        page, size, total = int(q["page"]), int(q["pg_sz"]), 250
        start = (page - 1) * size
        records = [{"name": f"X/{i}"} for i in range(start, min(start + size, total))]
        return httpx.Response(200, json={"records": records, "total": total})

    client, _ = make_client(handler, page_size=100)
    names = [r["name"] for r in client.search(auth="Edinburgh")]

    assert len(names) == 250 and len(set(names)) == 250
    assert [q["page"] for q in seen] == ["1", "2", "3"]
    assert all(q["sort"] == "start_date,name" and q["auth"] == "Edinburgh" for q in seen)


def test_stops_on_exact_multiple_of_page_size():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json={"records": [{"name": "a"}, {"name": "b"}], "total": 2})

    client, _ = make_client(handler, page_size=2)
    assert len(list(client.search())) == 2
    assert len(calls) == 1


def test_429_waits_for_retry_after_then_succeeds():
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "7"}, json={"error": "slow down"}),
            httpx.Response(200, json={"records": [{"name": "a"}], "total": 1}),
        ]
    )
    client, sleeps = make_client(lambda request: next(responses))
    assert [r["name"] for r in client.search()] == ["a"]
    assert sleeps == [7.0]


def test_gives_up_after_max_retries():
    client, sleeps = make_client(lambda request: httpx.Response(503), max_retries=2)
    with pytest.raises(PlanItError, match="Gave up"):
        list(client.search())
    assert len(sleeps) == 2


@pytest.mark.parametrize("status", [400, 403])
def test_non_retryable_errors_raise(status):
    client, sleeps = make_client(lambda request: httpx.Response(status, json={"error": "bad"}))
    with pytest.raises(PlanItError):
        list(client.search())
    assert sleeps == []


def test_error_field_in_200_payload_raises():
    client, _ = make_client(lambda request: httpx.Response(200, json={"error": "query too slow"}))
    with pytest.raises(PlanItError, match="too slow"):
        list(client.search())


def test_requests_are_spaced_by_min_interval():
    now = [100.0]
    sleeps: list[float] = []

    def handler(request):
        page = int(qs(request)["page"])
        return httpx.Response(200, json={"records": [{"name": str(page)}], "total": 2})

    client = PlanItClient(
        UA,
        page_size=1,
        min_interval_s=1.5,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        clock=lambda: now[0],
    )
    list(client.search())
    assert sleeps == [1.5]


def test_month_window_parameters():
    seen = []

    def handler(request):
        seen.append(qs(request))
        return httpx.Response(200, json={"records": [], "total": 0})

    client, _ = make_client(handler)
    list(client.applications_started_in_month("Glasgow", 2024, 2))
    assert seen[0]["start_date"] == "2024-02-01" and seen[0]["end_date"] == "2024-02-29"

    list(client.applications_changed_on("Glasgow", date(2026, 10, 15)))
    assert seen[1]["different_start"] == seen[1]["different_end"] == "2026-10-15"


def test_month_bounds_december():
    assert month_bounds(2025, 12) == (date(2025, 12, 1), date(2025, 12, 31))


def test_rejects_anonymous_user_agent():
    with pytest.raises(ValueError):
        PlanItClient("python-httpx/0.28")
