# Module 3: Deployment and operations

Complete the supplied deployment stubs to meet the [Module 3 requirements](../README.md#5-module-3-deployment-and-operations).

| File | Required content |
|---|---|
| `Dockerfile` | API image, dependencies, application files, and startup command |
| `docker-compose.yml` | Services, persistent storage, health checks, and startup dependencies |
| `nginx.conf` | API and OCR routing, request-body limit, and proxy timeouts |
| `.env.example` | Environment variable names and non-secret example values |
| `scripts/backup.sh` | Database backup and retention of the seven most recent files |
| `scripts/smoke_test.sh` | One batch through import, OCR, both reviews, export, and delivery |
| `RUNBOOK.md` | Tested startup, log access, OCR diagnosis, and restore instructions |

The Compose build context for the API is the repository root. Dockerfile `COPY` paths must use that context. Keep filenames and service names as specified in the [repository layout](../README.md#2-fixed-structure-and-naming).

## Configure and start

Run these commands from `q3_deploy/` after completing the deployment files:

```bash
cp .env.example .env
docker compose up --build
```

Set the database and service addresses in `.env` for the implemented configuration. Keep `.env` out of Git. Record the configuration steps and startup checks in [RUNBOOK.md](RUNBOOK.md).

After startup, run the smoke test in another terminal from `q3_deploy/`:

```bash
bash scripts/smoke_test.sh
```

## Configure nginx

Preserve `/ocr/parse` when forwarding OCR requests. A `proxy_pass` URI can change the forwarded path. Verify the received path against the [OCR endpoint](../mock_ocr/README.md#request-contract).

Set `client_max_body_size` for the expected upload sizes and test the limit. Set `proxy_read_timeout` to match the intended client-visible behavior during an upstream delay. Document the rationale for the chosen values.

Verify that `/api/*` reaches the API and `/ocr/*` reaches the mock OCR service through nginx.
