# Multi-Stage Production Dockerfile for AI Financial Stress Early Warning System

# --- Stage 1: Build & Dependency Wheel Builder ---
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Minimal Production Runtime ---
FROM python:3.11-slim as runtime

WORKDIR /app

# Create non-root user for container security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/models /app/reports /app/data && \
    chown -R appuser:appuser /app

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy source code and UI
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser ui/ /app/ui/
COPY --chown=appuser:appuser README.md /app/

USER appuser

EXPOSE 8000 8501

# Default command starts FastAPI service
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
