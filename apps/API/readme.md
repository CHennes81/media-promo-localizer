# Media Promo Localizer - Backend API

FastAPI backend for the Media Promo Localizer application.

## Setup

1. Install dependencies:

```bash
cd apps/api
pip install -r requirements.txt
```

2. Set environment variables (optional, defaults are provided):

```bash
export LOCALIZATION_MODE=mock
export MAX_UPLOAD_MB=20
export LOG_LEVEL=INFO
```

## Running

Start the development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

## Testing

Run tests from the repo root:

```bash
pytest apps/api/tests/
```

Or from the `apps/api` directory:

```bash
pytest
```

## Endpoints

- `GET /health` - Health check
- `POST /v1/localization-jobs` - Create a new localization job
- `GET /v1/localization-jobs/{jobId}` - Get job status and result

See `artifacts/API_Definition.md` for detailed API documentation.

## Sprint 2 Status

This backend implements Sprint 2 with a **mock localization pipeline**. All processing is simulated - no real OCR, translation, or inpainting is performed. The API contract matches the specification exactly, ready for Sprint 3 integration of live providers.
