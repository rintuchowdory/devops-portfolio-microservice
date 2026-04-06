# devops-portfolio-microservice

FastAPI microservice built for a DevOps portfolio. Includes Docker and GitHub Actions CI that runs tests and publishes a container image to GHCR.

## Endpoints
- `GET /health` -> `{ "status": "ok" }`

## Run locally (Termux/Linux)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

## CI/CD
- GitHub Actions runs pytest on PRs and pushes
- On push to main (and version tags), a container image is published to GHCR:
  `ghcr.io/rintuchowdory/devops-portfolio-microservice:<tag>`
