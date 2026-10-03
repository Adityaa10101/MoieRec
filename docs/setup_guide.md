# Local Setup & Verification Guide

## Prerequisites

- **Node.js**: >= 18 (Current environment: v24.18.1, npm 11.16.0)
- **Python**: >= 3.10 (Current environment: 3.14.6, pip 26.1.2)
- **Git**: Installed locally

---

## 1. Backend Setup

### Create and Activate Virtual Environment
```bash
# From repository root
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Start the FastAPI Server
```bash
# Option A: From root using python
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000

# Option B: Run main.py directly
cd backend
python app/main.py
```

The API will be available at: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

---

## 2. Frontend Setup

### Install Node Dependencies
```bash
cd frontend
npm install
```

### Start Vite Development Server
```bash
npm run dev
```

The frontend application will be served at `http://localhost:5173`.

---

## 3. Recommender Package

The recommender package (`recommender/`) is structured as an installable/importable Python package for ML experimentation.
Model training scripts and data processing pipelines will be executed via Python virtual environment.
