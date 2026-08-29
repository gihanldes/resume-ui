# Proof: single-container image. Node builds the frontend, Python serves
# the API and the built app from one origin.

# --- Stage 1: frontend build ---
FROM node:22-slim AS ui
WORKDIR /ui
COPY resume-ui/resume-ui/package.json resume-ui/resume-ui/package-lock.json ./
RUN npm ci
COPY resume-ui/resume-ui/ ./
RUN npm run build

# --- Stage 2: runtime ---
FROM python:3.14-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY resume-backend/resume-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY resume-backend/resume-backend/app ./app
COPY --from=ui /ui/dist ./static
ENV STATIC_DIR=/srv/static

EXPOSE 8080
# Shell form so Cloud Run's PORT is honored; exec so signals reach uvicorn.
# --proxy-headers so client IPs (used by the rate limiter) survive the proxy.
CMD exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers
