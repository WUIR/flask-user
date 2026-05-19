# ── Build stage ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

# ── Runtime stage ───────────────────────────────────────────────
FROM python:3.12-slim

RUN groupadd -r flask && useradd -r -g flask flask

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

RUN mkdir -p instance && chown -R flask:flask /app

USER flask

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "manage:app"]
