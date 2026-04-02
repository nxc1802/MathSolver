# Use a Python image with Manim dependencies
FROM manimcommunity/manim:v0.18.0

USER root
WORKDIR /app
# Docker / HF: silence pip “running as root” noise (no venv in slim images)
ENV PIP_ROOT_USER_ACTION=ignore
# Base image runs as user `manim`; default pip cache dir may be unwritable → use /tmp
ENV PIP_CACHE_DIR=/tmp/pip-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    texlive \
    texlive-latex-extra \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements (manim CLI comes from the base image, not pip)
COPY requirements.txt .
RUN mkdir -p /tmp/pip-cache && chmod 1777 /tmp/pip-cache \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
