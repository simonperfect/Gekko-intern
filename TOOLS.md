| Tool or source | Use | Files materially influenced |
|---|---|---|
| Gemini | Assisted with multi-container Docker configuration, resolving Nginx syntax and proxy routing issues (`nginx.conf`), and troubleshooting the end-to-end smoke test script. | `q3_deploy/nginx.conf`, `q3_deploy/docker-compose.yml`, `scripts/smoke_test.sh` |
| Nginx Official Documentation | Referenced for syntax rules regarding `events`, `http`, and `server` blocks, as well as `proxy_pass` and payload size limits (`client_max_body_size`). | `q3_deploy/nginx.conf` |
| Docker & Docker Compose Documentation | Referenced for container health checks, dependency ordering (`depends_on`), and volume binding paths. | `q3_deploy/docker-compose.yml` |
| FastAPI Documentation | Referenced for API routing, middleware setup, and asynchronous request handling. | `q1_api/` |