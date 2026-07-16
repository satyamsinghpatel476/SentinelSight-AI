FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN python -m playwright install --with-deps chromium

COPY backend /app/backend
COPY scripts /app/scripts
COPY --from=frontend-build /app/frontend/dist /app/backend/app/static

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && if [ \"${AUTO_SEED_DEMO_USERS:-false}\" = \"true\" ]; then python /app/scripts/seed_demo_users.py; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
