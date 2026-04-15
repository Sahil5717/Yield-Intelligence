FROM python:3.12

WORKDIR /app

# System deps for scipy/pymc/prophet compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gfortran libopenblas-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Core deps (must succeed)
RUN pip install --no-cache-dir \
    numpy pandas scipy scikit-learn fastapi uvicorn \
    python-multipart openpyxl statsmodels \
    python-jose passlib bcrypt==4.0.1

# Scientific stack (fallback-safe)
RUN pip install --no-cache-dir prophet 2>/dev/null || echo "[SKIP] Prophet — linear fallback active"
RUN pip install --no-cache-dir pymc arviz 2>/dev/null || echo "[SKIP] PyMC — MLE/OLS fallback active"

# Export libs
RUN pip install --no-cache-dir reportlab python-pptx 2>/dev/null || echo "[SKIP] Export libs"

# Copy application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY templates/ ./templates/
COPY docs/ ./docs/
COPY LICENSE ./

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
