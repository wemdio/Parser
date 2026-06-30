# Merged single-app image for the Telegram parser:
# build the React (CRA) admin frontend, then serve it from the FastAPI backend.
# This is the image Timeweb App 126707 builds (root Dockerfile, default path).
# Build context = repo root.

# ── Stage 1: build the React frontend ────────────────────────────────────
FROM node:18-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci --only=production --ignore-scripts
COPY frontend/public/ ./public/
COPY frontend/src/ ./src/
# REACT_APP_API_URL intentionally unset → config.js uses same-origin "/api".
RUN npm run build

# ── Stage 2: FastAPI backend that also serves the built frontend ─────────
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Built frontend from stage 1 → FastAPI serves it at "/" (see backend/main.py).
COPY --from=frontend /fe/build ./frontend_build

# Session files live here (also restored from Supabase on boot).
RUN mkdir -p sessions

EXPOSE 8000
CMD ["python", "run_backend.py"]
