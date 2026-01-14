# Visual Math Solver - Backend

FastAPI backend for Visual Math Solver.

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env with your MegaLLM API key

# Run development server
uvicorn app.main:app --reload
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Structure

```
be/
├── app/
│   ├── main.py          # FastAPI app entry
│   ├── config.py        # Settings management
│   ├── routers/         # API endpoints
│   ├── services/        # Business logic
│   └── schemas/         # Pydantic models
├── requirements.txt
└── .env.example
```
