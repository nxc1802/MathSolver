# Visual Math Solver — API container (Python 3.11 + Manim + OCR stack)
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    NO_ALBUMENTATIONS_UPDATE=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

WORKDIR /app
ENV PYTHONPATH=/app

# Runtime + *-dev: Manim/pycairo need pkg-config + cairo headers; libpango1.0-dev covers PangoCairo on Bookworm (no libpangocairo-*-dev package).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    pkg-config \
    cmake \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    python3-dev \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY . .

# Bake model weights and agent init into the image (YOLO, PaddleOCR, Pix2Tex, etc.)
RUN python scripts/prewarm_models.py

# Hugging Face Spaces defaults to 7860; docker-compose can set PORT=8000
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
