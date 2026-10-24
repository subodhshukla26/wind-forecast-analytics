# Backend

Minimal FastAPI backend for the UK Wind Forecast Analytics application.

## Local setup

From the repository root:

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the API

```powershell
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

Health check: `GET http://localhost:8000/api/health`
