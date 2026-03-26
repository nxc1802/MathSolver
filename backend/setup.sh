#!/bin/bash

# MathSolver v3.1 Setup Script for macOS

echo "🚀 Starting Environment Setup..."

# 1. System Dependencies (Homebrew)
if command -v brew >/dev/null 2>&1; then
    echo "📦 Installing system dependencies via Homebrew..."
    brew install pango pkg-config glib librsvg
else
    echo "⚠️ Homebrew not found. Please install it first: https://brew.sh/"
    exit 1
fi

# 2. Python SSL Certificates
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
CERT_FILE="/Applications/Python ${PYTHON_VERSION}/Install Certificates.command"

if [ -f "$CERT_FILE" ]; then
    echo "🔐 Installing Python SSL certificates..."
    sh "$CERT_FILE"
else
    echo "ℹ️ SSL certificate installer not found at $CERT_FILE. Skipping..."
fi

# 3. Virtual Environment
echo "🐍 Setting up Python Virtual Environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# 4. Pip packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Fix ManimPango (Crucial for macOS arm64)
echo "🛠️ Rebuilding ManimPango from source to ensure library linking..."
pip install --no-cache-dir --force-reinstall --no-binary manimpango manimpango

echo "✅ Setup Complete!"
echo "To start the backend, run: source venv/bin/activate && uvicorn app.main:app --reload"
