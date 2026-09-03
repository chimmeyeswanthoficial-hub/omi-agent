# OmiAgent server image: builds the UI, ships Python app + static assets.
# ── stage 1: UI ───────────────────────────────────────────────────────────
FROM node:20-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install --no-fund --no-audit
COPY ui .
RUN npm run build

# ── stage 2: app ───────────────────────────────────────────────────────────
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ripgrep ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY configs ./configs
RUN pip install --no-cache-dir .
COPY --from=ui /ui/dist /app/static
ENV OMI_STATIC_DIR=/app/static OMI_HOST=0.0.0.0 OMI_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import httpx;httpx.get('http://127.0.0.1:8000/healthz',timeout=2)" || exit 1
CMD ["omiagent", "serve"]
