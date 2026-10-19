-include .env
export

COUNCIL ?= Edinburgh
MONTH ?= 2026-09

.PHONY: setup db test lint fixture load-fixture dbt-build demo extract dagster clean

setup:            ## Install everything into the active virtualenv
	pip install -e ".[dev,pipeline,dbt]"

db:               ## Start PostGIS and wait until it is healthy
	docker compose up -d --wait db

test:             ## Unit tests (no database needed)
	pytest

lint:
	ruff check . && ruff format --check .

fixture:          ## Regenerate the synthetic test fixture
	python scripts/make_fixture.py

load-fixture:     ## Load the synthetic fixture into Postgres
	plotcheck load-file tests/fixtures/sample_applications.jsonl.gz

dbt-build:        ## Build and test every dbt model, test and snapshot
	cd dbt && DBT_PROFILES_DIR=. dbt build

demo: db load-fixture dbt-build   ## Whole pipeline on synthetic data, no API calls

extract:          ## Land + load one real month: make extract COUNCIL=Glasgow MONTH=2026-08
	plotcheck extract --council "$(COUNCIL)" --month $(MONTH) --load

dagster:          ## Dagster UI on http://localhost:3000
	dagster dev

clean:
	docker compose down -v
	rm -rf data dbt/target dbt/logs
