"""A polite client for the PlanIt planning applications API.

PlanIt (https://www.planit.org.uk/) is a free, volunteer-run aggregator of UK council
planning registers. Its API docs (https://www.planit.org.uk/api/) ask for:

* a real User-Agent (an invalid one gets HTTP 403),
* respecting rate limits (HTTP 429 with a Retry-After header),
* small pages fetched one after another rather than one huge request
  (hard limits: 5000 records and 1000 kB per request).

This client does all three, and pages until it has the `total` the API reports.
"""

from __future__ import annotations

import calendar
import logging
import time
from collections.abc import Callable, Iterator
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

BASE_URL = "https://www.planit.org.uk"
SEARCH_PATH = "/api/applics/json"
HARD_RECORD_LIMIT = 5000

log = logging.getLogger(__name__)


class PlanItError(RuntimeError):
    """The API refused a request in a way retrying will not fix."""


class PlanItClient:
    def __init__(
        self,
        user_agent: str,
        *,
        page_size: int = 100,
        min_interval_s: float = 1.0,
        max_retries: int = 5,
        base_url: str = BASE_URL,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not user_agent or "PlotCheck" not in user_agent:
            raise ValueError(
                "Set a descriptive User-Agent, e.g. 'PlotCheck/0.1 (+https://github.com/you/plotcheck)'"
            )
        self.page_size = page_size
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None
        self._http = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(60.0),
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PlanItClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- low level -------------------------------------------------------------------------

    def _wait_for_slot(self) -> None:
        """Keep at least `min_interval_s` between requests."""
        if self._last_request_at is not None:
            elapsed = self._clock() - self._last_request_at
            if elapsed < self.min_interval_s:
                self._sleep(self.min_interval_s - elapsed)
        self._last_request_at = self._clock()

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            self._wait_for_slot()
            try:
                resp = self._http.get(SEARCH_PATH, params=params)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise
                wait = 2**attempt
                log.warning("Network error (%s); retrying in %ss", exc, wait)
                self._sleep(wait)
                continue

            if resp.status_code == 200:
                payload = resp.json()
                if "error" in payload:
                    raise PlanItError(payload["error"])
                return payload
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    break
                wait = _retry_after_seconds(resp, default=2**attempt * 5)
                log.warning("HTTP %s from PlanIt; waiting %ss", resp.status_code, wait)
                self._sleep(wait)
                continue
            if resp.status_code == 403:
                raise PlanItError(
                    "403 Forbidden: check the User-Agent and that your IP is not blocked"
                )
            raise PlanItError(f"HTTP {resp.status_code}: {_error_message(resp)}")
        raise PlanItError(f"Gave up after {self.max_retries} retries: {params}")

    # ---- searches --------------------------------------------------------------------------

    def search(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Yield every record matching `params`, one page at a time.

        A stable sort is always applied so paging cannot skip or repeat records.
        """
        params = {"compress": "on", "sort": "start_date,name", **params, "pg_sz": self.page_size}
        page, fetched = 1, 0
        while True:
            payload = self._get({**params, "page": page})
            records = payload.get("records") or []
            total = payload.get("total")
            if page == 1 and total and total > HARD_RECORD_LIMIT:
                log.warning("%s records match %s; consider a narrower window", total, params)
            yield from records
            fetched += len(records)
            if not records or len(records) < self.page_size:
                return
            if isinstance(total, int) and fetched >= total:
                return
            page += 1

    def applications_started_in_month(
        self, council: str, year: int, month: int
    ) -> Iterator[dict[str, Any]]:
        """Applications submitted to `council` in a calendar month (used for backfills)."""
        first, last = month_bounds(year, month)
        yield from self.search(
            auth=council, start_date=first.isoformat(), end_date=last.isoformat()
        )

    def applications_changed_on(self, council: str, day: date) -> Iterator[dict[str, Any]]:
        """Applications whose council record changed on `day` (used for nightly updates).

        Uses `different_*` (source changed on the council site) rather than `changed_*`,
        which also moves whenever PlanIt re-derives fields across its whole database.
        """
        yield from self.search(
            auth=council, different_start=day.isoformat(), different_end=day.isoformat()
        )


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _retry_after_seconds(resp: httpx.Response, default: float) -> float:
    value = resp.headers.get("Retry-After")
    if not value:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
        return max(0.0, (when - datetime.now(when.tzinfo)).total_seconds())
    except (TypeError, ValueError):
        return default


def _error_message(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("error", resp.text[:200]))
    except ValueError:
        return resp.text[:200]
