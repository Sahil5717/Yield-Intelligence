FROM python:3.12-slim

WORKDIR /app

# System dependencies for scientific Python stack.
#   build-essential + gfortran: required by PyTensor (PyMC), Prophet (CmdStan)
#   libopenblas-dev:             BLAS backend for NumPy/SciPy
#   pkg-config:                  required by several pip builds
#   curl:                        healthcheck convenience
# Cleaning apt lists after install trims ~30MB from the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        libopenblas-dev \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements FIRST so pip layer caches across code changes.
# Using --no-cache-dir keeps the image lean; ~450MB final vs ~1.2GB without.
#
# Key change from the previous Dockerfile: we no longer wrap the pymc/prophet
# installs in `|| echo "[SKIP]"`. That pattern silently allowed a broken image
# to ship where the Bayesian MMM path would permanently fall back. If a
# dependency install fails now, the build fails — which is the point.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Verify the critical imports actually work AFTER install. This catches
# environments where pip thinks it installed something but the native
# libraries are broken (common with pymc/prophet on ARM or non-standard
# base images). Fails the build if any of these go missing.
RUN python -c "import numpy, pandas, scipy, sklearn, statsmodels, fastapi; print('[OK] core stack')"
RUN python -c "import pymc, arviz; print(f'[OK] pymc {pymc.__version__}, arviz {arviz.__version__}')"
RUN python -c "import prophet; print(f'[OK] prophet {prophet.__version__}')"

# Application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY templates/ ./templates/
COPY docs/ ./docs/
COPY LICENSE ./

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
