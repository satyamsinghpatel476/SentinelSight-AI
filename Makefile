.PHONY: backend-test backend-lint backend-format frontend-install frontend-build run-backend run-frontend

backend-test:
	cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/pytest

backend-lint:
	.venv/bin/ruff check --config backend/pyproject.toml backend/app backend/tests backend/alembic scripts/seed_demo_users.py demo-target/app

backend-format:
	.venv/bin/black backend/app backend/tests backend/alembic scripts/seed_demo_users.py demo-target/app
	.venv/bin/ruff check --config backend/pyproject.toml backend/app backend/tests backend/alembic scripts/seed_demo_users.py demo-target/app --fix

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

seed-demo-users:
	.venv/bin/python scripts/seed_demo_users.py

run-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0
