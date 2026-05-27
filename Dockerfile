# =============================================================================
#  AI Database Optimizer — Production Dockerfile
#  Deploy to: Render · Railway · Fly.io · Cloud Run · any Docker host
# =============================================================================
#  Build:  docker build -t ai-db-optimizer .
#  Run:    docker run -p 8501:8501 -e GEMINI_API_KEY=xxx ai-db-optimizer
# =============================================================================

# ── Stage: lightweight Python runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Install only the minimal OS packages needed by psycopg2-binary
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── App directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies first (layer caching) ────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy the full project (respects .dockerignore) ────────────────────────
COPY . .

# ── Ensure the optimization_artifacts directory exists ────────────────────
RUN mkdir -p /app/optimization_artifacts && \
    mkdir -p /app/prisma

# ── Expose Streamlit default port ─────────────────────────────────────────
EXPOSE 8501

# ── Health check ──────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Streamlit configuration ──────────────────────────────────────────────
# Disable Streamlit's telemetry and email prompt in production
RUN mkdir -p /root/.streamlit && \
    echo '[server]'                          >  /root/.streamlit/config.toml && \
    echo 'headless = true'                   >> /root/.streamlit/config.toml && \
    echo 'enableCORS = false'                >> /root/.streamlit/config.toml && \
    echo 'enableXsrfProtection = false'      >> /root/.streamlit/config.toml && \
    echo ''                                  >> /root/.streamlit/config.toml && \
    echo '[browser]'                         >> /root/.streamlit/config.toml && \
    echo 'gatherUsageStats = false'          >> /root/.streamlit/config.toml

# ── Entrypoint ────────────────────────────────────────────────────────────
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
