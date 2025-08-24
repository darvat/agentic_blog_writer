# Configuration and Deployment

## Overview

This guide documents how the application is configured and deployed across local development, containers, and Kubernetes. It is written from an SRE/production operations perspective and emphasizes safe defaults, clear precedence, and security.

---

### Configuration surfaces and precedence

The application currently loads configuration from environment variables. A `.env` file can be used for local development; it is read automatically via `python-dotenv` at import time by `app/core/config.py`.

- **Primary source**: environment variables
- **Local development**: values from a local `.env` file at the project root
- **YAML/TOML**: not consumed at runtime today

**Precedence**
1. Process environment (e.g., injected by Docker Compose, Kubernetes, or the shell)
2. `.env` file (loaded by `dotenv.load_dotenv()`)
3. Code defaults (where provided; e.g., `RESEARCH_STRATEGY="individual"`, `RESEARCH_MAX_RETRIES=2`)

Note: The loader does not overwrite existing environment variables with `.env` values. Runtime-provided environment always wins over `.env`.

**Validation behavior**
- `app/core/config.py` constructs a global `Config()` instance on import and validates required settings.
- Missing required keys cause a `ValueError` during startup:
  - Required: `OPENAI_API_KEY`, `GEMINI_API_KEY`
- Optional (examples): `FIRECRAWL_API_KEY`, model and logging settings, research settings

This fail-fast behavior is desirable in all environments. Your container/pod will crash immediately if a required key is missing.

**Known configuration keys**

| Variable | Required | Default | Description |
|---|---|---:|---|
| `OPENAI_API_KEY` | yes | — | API key for OpenAI/Agents SDK |
| `GEMINI_API_KEY` | yes | — | API key for Gemini |
| `FIRECRAWL_API_KEY` | no | — | API key for Firecrawl (if used) |
| `LARGE_REASONING_MODEL` | no | — | Model id for large reasoning tasks |
| `SMALL_REASONING_MODEL` | no | — | Model id for small reasoning tasks |
| `SMALL_FAST_MODEL` | no | — | Model id for small fast tasks |
| `LARGE_FAST_MODEL` | no | — | Model id for large fast tasks |
| `IMAGE_GENERATION_MODEL` | no | — | Model id for image generation |
| `GEMINI_FLASH_MODEL` | no | — | Gemini flash model id |
| `GEMINI_FLASH_PRO_MODEL` | no | — | Gemini flash pro model id |
| `LOGGING_LEVEL` | no | — | Logging level (e.g., `INFO`, `DEBUG`) |
| `RESEARCH_STRATEGY` | no | `individual` | Research coordination strategy |
| `RESEARCH_MAX_RETRIES` | no | `2` | Retry attempts for research operations |

**Example `.env.example`**

Create a `.env` file for local development using the following template. Do not commit the real `.env`.

```dotenv
# Required
OPENAI_API_KEY="your_openai_api_key"
GEMINI_API_KEY="your_gemini_api_key"

# Optional providers
FIRECRAWL_API_KEY=""

# Models (set to your preferred/allowed values)
LARGE_REASONING_MODEL="gpt-4o"
SMALL_REASONING_MODEL="gpt-4o-mini"
SMALL_FAST_MODEL="gpt-4o-mini"
LARGE_FAST_MODEL="gpt-4o"
IMAGE_GENERATION_MODEL="gpt-image-1"
GEMINI_FLASH_MODEL="gemini-2.0-flash"
GEMINI_FLASH_PRO_MODEL="gemini-2.0-flash-thinking"

# Logging & research
LOGGING_LEVEL="INFO"
RESEARCH_STRATEGY="individual"
RESEARCH_MAX_RETRIES="2"
```

---

### Secrets management

- **Least privilege**: scope API keys to the minimal products/projects needed. Avoid organization-wide keys.
- **Key rotation**: rotate keys on a schedule and immediately when exposure is suspected. Prefer platform-level rotation primitives.
- **No secrets in git**: never commit real `.env`. Keep an up-to-date `.env.example` only.
- **Secret stores**: use a managed secret store (e.g., 1Password, Vault, GCP Secret Manager, AWS Secrets Manager) and inject at runtime via CI/CD or orchestrator.
- **Runtime logs**: do not log secrets or full request payloads; scrub/redact where necessary.
- **Access boundaries**: lock down image registries, CI/CD secrets, and Kubernetes RBAC. Use dedicated service accounts.

Docker Compose and Kubernetes examples below demonstrate safe injection patterns.

---

### Local development

#### Using uv (preferred)

Prerequisites: Python 3.10+, `uv`, and `git`.

```bash
# create and sync virtual environment from pyproject
uv sync --dev

# copy template and fill in your keys
cp .env.example .env

# run lint and tests
uv run ruff check .
uv run pytest -q

# run an interactive workflow (adjust command to your use case)
uv run python app/workflows/article_creation_workflow.py
```

Notes:
- The app reads `.env` automatically at import time via `python-dotenv`.
- If you need to override a value, export it in your shell before running `uv run`.

#### Alternative: venv or poetry

```bash
# venv
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

# poetry (if you prefer)
poetry install --with dev
poetry run python app/workflows/article_creation_workflow.py
```

---

### Container images

A minimal, production-leaning Dockerfile example for building the application image. Adjust the `CMD` to your primary entrypoint (interactive workflows may not be suitable for production containers; consider a CLI wrapper or API server).

```dockerfile
# syntax=docker/dockerfile:1.7-labs
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /sbin/nologin appuser
WORKDIR /app

# Install app dependencies
COPY pyproject.toml /app/
RUN pip install --upgrade pip \
 && pip install .  # uses hatchling to build and install package

# Copy source
COPY app /app/app
COPY docs /app/docs

USER appuser

# Default command (override in compose/k8s)
CMD ["python", "app/workflows/article_creation_workflow.py"]
```

Security notes:
- Non-root user (`appuser`) is used by default.
- Prefer distroless or slim images in production and pin the base image digest.
- Keep the image small; avoid dev tooling in the runtime layer.

#### SBOM and vulnerability scanning

- Generate an SBOM for the built image and store it with your artifacts:

```bash
docker build -t agentic-blog-writer:local .
docker sbom agentic-blog-writer:local -o cyclonedx-json > sbom.json  # or use syft
```

- Scan the image in CI (examples: Trivy, Grype) and enforce policies.
- Consider signing images with Cosign and verifying at deploy time.

---

### Docker Compose (example)

When using Compose, prefer `.env` for non-sensitive defaults and inject sensitive values via environment or Docker Secrets (if available).

```yaml
version: "3.9"
services:
  blog-writer:
    build: .
    image: agentic-blog-writer:local
    env_file:
      - .env  # local defaults; overridden by explicit environment below
    environment:
      # Explicitly surface only the vars you need; they override .env
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      LOGGING_LEVEL: ${LOGGING_LEVEL:-INFO}
      RESEARCH_STRATEGY: ${RESEARCH_STRATEGY:-individual}
      RESEARCH_MAX_RETRIES: ${RESEARCH_MAX_RETRIES:-2}
    command: ["python", "app/workflows/article_creation_workflow.py"]
    user: "1000:1000"  # run as non-root
    read_only: true
    tmpfs:
      - /tmp:size=128m,mode=1777
    restart: "no"  # change to unless-stopped for long-running services
```

Notes:
- Secrets: Prefer Docker Secrets or an external secrets store; avoid committing `.env`.
- For long-running services (e.g., API server), change the `command` accordingly and set a suitable restart policy.

---

### Kubernetes manifests (examples)

Use Kubernetes Secrets to provide credentials, and set tight security contexts on Pods. Consider an External Secrets operator for cloud secret managers.

#### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: blog-writer-secrets
  namespace: default
type: Opaque
stringData:
  OPENAI_API_KEY: "YOUR_OPENAI_API_KEY"
  GEMINI_API_KEY: "YOUR_GEMINI_API_KEY"
```

#### Deployment (long-running)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-writer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-writer
  template:
    metadata:
      labels:
        app: blog-writer
    spec:
      serviceAccountName: blog-writer
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
      containers:
        - name: app
          image: your-registry/agentic-blog-writer:TAG
          imagePullPolicy: IfNotPresent
          command: ["python", "app/workflows/article_creation_workflow.py"]
          env:
            - name: LOGGING_LEVEL
              value: "INFO"
          envFrom:
            - secretRef:
                name: blog-writer-secrets
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: { medium: Memory, sizeLimit: 128Mi }
```

#### Job (batch/one-off)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: blog-writer-job
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: app
          image: your-registry/agentic-blog-writer:TAG
          command: ["python", "app/workflows/article_creation_workflow.py"]
          envFrom:
            - secretRef:
                name: blog-writer-secrets
```

#### RBAC (least privilege)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-writer
```

Notes:
- Use dedicated `ServiceAccount`; bind RBAC narrowly if the app needs K8s API access (most workloads here likely do not).
- Enforce `runAsNonRoot`, `readOnlyRootFilesystem`, and resource requests/limits.
- Prefer external secrets tooling for rotation and audit.

---

### Production hardening checklist

- Environment configuration precedence documented and validated at startup
- Secrets injected via orchestrator, not baked into images
- Non-root containers; read-only filesystem; minimal base images
- SBOM generated and stored; image scanning in CI; optional image signing
- Auto-restarts and readiness probes for long-running services (if applicable)
- Observability: set `LOGGING_LEVEL` appropriately and route logs to your platform

---

### Troubleshooting

- Startup fails with `ValueError: Missing required environment variables` → ensure `OPENAI_API_KEY` and `GEMINI_API_KEY` are set at runtime (Compose/K8s).
- Local dev does not see new env values → re-source your shell or restart the process; remember that OS env overrides `.env`.
- Container exits immediately → if using an interactive workflow, consider wrapping with a non-interactive entrypoint or use a Kubernetes `Job`.


