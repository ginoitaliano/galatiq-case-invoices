# ── Stage 1: dependency install ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.2

WORKDIR /app

# Copy only dependency files first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# Install deps into a local venv inside the image (no system-wide install)
RUN poetry config virtualenvs.in-project true \
 && poetry install --no-root --no-interaction --no-ansi

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Tesseract OCR (optional — needed for scanned PDF extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the venv built in stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY backend/ ./backend/
COPY data/    ./data/
COPY main.py  ./

# Make sure the venv's bin is on PATH
ENV PATH="/app/.venv/bin:$PATH"

# FastAPI runs on 8000
EXPOSE 8000

# Initialise the inventory DB, then start Uvicorn
CMD ["sh", "-c", "python data/setup_inventory.py && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
