# Use a Python image with Manim dependencies
FROM manimcommunity/manim:latest

USER root
WORKDIR /app

# Install system dependencies for LaTeX and FFmpeg (already in manim image but for safety)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    texlive \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
