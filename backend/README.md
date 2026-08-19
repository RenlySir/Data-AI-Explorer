# Data AI Explorer backend MVP

Python/FastAPI demo backend for the first product slice. It uses deterministic in-memory data so it can be started without a database, queue, or model service.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

OpenAPI is available at http://localhost:8000/docs. The API is prefixed with `/api/v1`; CORS allows local frontend development origins.

## Demo flow

1. `GET /api/v1/workbench/summary` loads the dashboard.
2. `POST /api/v1/query/conversations` submits a natural-language question and returns an operation id.
3. `GET /api/v1/query/operations/{operation_id}` reads the generated SQL, answer and evidence.
4. Browse `GET /api/v1/incidents` and `GET /api/v1/assets` for operations and governance views.
