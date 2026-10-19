"""Command line entry points, for running steps without Dagster.

plotcheck extract --council Edinburgh --month 2026-09          # land one month
plotcheck extract --council Edinburgh --month 2026-09 --load   # ...and merge into Postgres
plotcheck load-file tests/fixtures/sample_applications.jsonl.gz
plotcheck classify "Erection of dormer to rear roof slope"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from plotcheck import landing, worktypes
from plotcheck.planit import PlanItClient


def _settings() -> tuple[str, str]:
    user_agent = os.environ.get("PLOTCHECK_USER_AGENT", "")
    landing_url = os.environ.get("PLOTCHECK_LANDING_URL", "data/landing")
    return user_agent, landing_url


def cmd_extract(args: argparse.Namespace) -> int:
    from plotcheck import warehouse

    user_agent, base = _settings()
    year, month = (int(p) for p in args.month.split("-"))
    query = {"auth": args.council, "month": args.month}
    url = landing.partition_url(base, "backfill", args.council, args.month)
    with PlanItClient(user_agent) as client:
        n = landing.write_jsonl(
            client.applications_started_in_month(args.council, year, month), url, query
        )
    print(f"Landed {n} applications -> {url}")
    if args.load:
        print(warehouse.load_records(landing.read_jsonl(url)))
    return 0


def cmd_load_file(args: argparse.Namespace) -> int:
    from plotcheck import warehouse

    print(warehouse.load_records(landing.read_jsonl(args.path)))
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    print(worktypes.classify(args.description))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="plotcheck")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("extract", help="Land one council-month from PlanIt")
    p.add_argument("--council", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--load", action="store_true", help="Also merge into Postgres")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("load-file", help="Merge a landed .jsonl.gz file into Postgres")
    p.add_argument("path")
    p.set_defaults(func=cmd_load_file)

    p = sub.add_parser("classify", help="Classify a planning description by work type")
    p.add_argument("description")
    p.set_defaults(func=cmd_classify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
