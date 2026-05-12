VENV_PYTHON ?= .venv/bin/python
ALEMBIC ?= .venv/bin/alembic

.PHONY: migrate-new migrate-up migrate-current migrate-history migrate-check

migrate-new:
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-new m='describe_change'"; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(m)"

migrate-up:
	$(ALEMBIC) upgrade head

migrate-current:
	$(ALEMBIC) current

migrate-history:
	$(ALEMBIC) history --verbose

migrate-check:
	$(VENV_PYTHON) scripts/check_migration_drift.py
