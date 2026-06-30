# project-skeleton

**Universal CI/CD shell.** Tiny nginx image that builds on push → pushes to GHCR → triggers Dokploy deploy. Swap the code for any language/framework with `opencode run`.

## Quick start

```bash
# Create a new project from this template
gh repo create my-project --template jawg-zz/project-skeleton --clone
cd my-project

# Build whatever you want (OpenCode rewrites Dockerfile, compose, and app)
opencode run "build a Go API with PostgreSQL and Redis"

# Push — triggers ARM64 build → GHCR → Dokploy deploy
git add -A && git commit -m "first app" && git push origin main
```

## Local dev

```bash
docker compose up --build
# → http://localhost:80  (nginx serves index.html)
```

## CI/CD pipeline

On every push to `main`:

1. **Build** — ARM64 Docker image via GitHub Actions
2. **Push** — to `ghcr.io/jawg-zz/<repo-name>:latest`
3. **Deploy** — Dokploy pulls and restarts the container

### Required GitHub secrets (set once per project)

| Secret | Description |
|--------|-------------|
| `DOKPLOY_URL` | Your Dokploy instance URL |
| `DOKPLOY_API_KEY` | Dokploy API key |
| `DOKPLOY_APPLICATION_ID` | Application ID from Dokploy |

## Files

```
.
├── Dockerfile              # nginx:alpine — swap for your stack
├── nginx.conf              # nginx config with /health endpoint
├── index.html              # Placeholder page — your app replaces this
├── docker-compose.yml      # Local dev compose
├── .github/workflows/
│   └── docker-publish.yml  # ARM64 build → GHCR → Dokploy trigger
├── .env.example
└── README.md
```

## Stack-agnostic design

The template is intentionally minimal — just an nginx serving a static page. This ensures:

- **First push builds successfully** — no framework code to compile
- **Clean slate for OpenCode** — no Python/Node/Go files to conflict with
- **Pipeline stays the same** — GHCR build + Dokploy deploy never changes

OpenCode will rewrite `Dockerfile`, `docker-compose.yml`, and add your app code when you `run "build a ..."`.
