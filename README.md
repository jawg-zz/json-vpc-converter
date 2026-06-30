# project-skeleton

**Production-ready FastAPI skeleton with CI/CD pipeline.**

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Docker

```bash
docker compose up --build
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application, routes, middleware
│   └── config.py        # Pydantic settings from .env
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## CI/CD Pipeline

On every push to `main`:

1. **Build & Test** — GitHub Actions builds the Docker image and runs tests.
2. **Push to GHCR** — The image is tagged and pushed to GitHub Container Registry.
3. **Deploy to Dokploy** — The workflow calls the Dokploy API to trigger a redeploy.

The pipeline is defined in `.github/workflows/`.

### Required GitHub Secrets

| Secret                    | Description                         |
|---------------------------|-------------------------------------|
| `DOKPLOY_URL`             | Your Dokploy instance URL           |
| `DOKPLOY_API_KEY`         | Dokploy API key for authentication  |
| `DOKPLOY_APPLICATION_ID`  | Application ID in Dokploy           |

### Manual Deploy

To trigger a deploy manually, run:

```bash
curl -X POST "${DOKPLOY_URL%/}/api/application.deploy" \
  -H "x-api-key: $DOKPLOY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"applicationId": "'"$DOKPLOY_APPLICATION_ID"'"}'
```

## Environment Variables

| Variable       | Default                       | Description        |
|----------------|-------------------------------|--------------------|
| `APP_ENV`      | `development`                 | Application env    |
| `DEBUG`        | `true`                        | Debug mode         |
| `SECRET_KEY`   | `change-me-to-a-random-string`| Secret key         |
| `DATABASE_URL` | —                             | Postgres DSN       |
| `REDIS_URL`    | —                             | Redis DSN          |

Copy `.env.example` to `.env` and adjust values.

## Creating a New Project from This Template

```bash
gh repo create my-new-project --template project-skeleton --public --clone
cd my-new-project
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
```

Replace the `project` name in `pyproject.toml` and `app/main.py` as needed.
