Secure deployment (brief)

1) Environment and secrets
- Never store secrets in source. Use `.env` (for local) and a secrets manager in production.
- In Docker, prefer `env_file` or Docker secrets (for Swarm/Kubernetes use secrets).
- Set `ENV=production` in production and ensure `API_TOKEN` is strong.

2) Docker-compose (example)
- Use an `.env` or `env_file` and avoid hard-coded tokens in `docker-compose.yml`:

```yaml
services:
  calculator-api:
    build: ./rpi4
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./rpi4:/app
```

3) TLS / Reverse proxy
- Put the API behind a reverse proxy (Caddy, Traefik, Nginx) that obtains and renews TLS certs automatically.
- Example: use Caddy with a simple Caddyfile to obtain Let's Encrypt certs and forward requests to the API service.

4) Hardening
- Require `API_TOKEN` in production (done).
- Rate-limit endpoints (use middleware or API gateway).
- Validate and sanitize inputs on `/solve` to avoid abuse.
- Run the app as a non-root user in containers.

5) Logging and monitoring
- Send logs to a centralized system (ELK, Promtail + Loki) or use cloud logging.
- Add health and metrics endpoints; scrape with Prometheus if available.

6) CI/CD
- Build images in CI, run tests, push images to registry, and deploy via controlled pipeline.
- Use a separate step to inject secrets from the platform (GitHub Actions secrets, Vault, etc.).

7) Backups and rollbacks
- Version your images and keep rollbacks simple: use tags and deploy previous tag on failure.

