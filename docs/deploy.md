# Deploy and Security

## Access: Public vs Tailscale

The server supports two **alternative** exposure modes, chosen with the `ACCESS_MODE` variable in `.env` (see `backend_rpi4/config.py` and `backend_rpi4/utils/validators.py`):

| `ACCESS_MODE` | How the Pi is reached | Bearer token (`API_TOKEN`) |
|---|---|---|
| `public` *(default)* | Internet, behind Caddy on `:443` | **Required** on every request |
| `tailscale` | Only from your Tailscale tailnet | Not checked (the tailnet is already the perimeter) |

The default is `public` intentionally (fail-safe): if someone forgets to set the variable, the API still requires a token instead of implicitly trusting the network.

In production (`ENV=production`) with `ACCESS_MODE=public`, startup fails if `API_TOKEN` is still the default value — see `backend_rpi4/config.py`.

## 1) Environment and Secrets

- Never put secrets in source code. Use `.env` locally and a secrets manager in production.
- In Docker, prefer `env_file` or Docker secrets (for Swarm/Kubernetes use native secrets).
- In production, set `ENV=production` and a strong `API_TOKEN` if using `ACCESS_MODE=public`.

## 2) Docker Compose

Example (see `docker-compose.yml` in the root): build context at the repo root (the `Dockerfile` copies `requirements.txt` and `backend_rpi4/` from there), secrets passed via `env_file` instead of hardcoded:

```yaml
services:
  calculator-api:
    build:
      context: .
      dockerfile: backend_rpi4/Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
```

## 3) TLS / Reverse Proxy (Caddy)

Put the API behind a reverse proxy (Caddy, Traefik, Nginx) that automatically obtains and renews TLS certificates. Caddy is the choice used in this project, especially in combination with `ACCESS_MODE=public`.

`caddy/Caddyfile`:

```
my-domain.duckdns.org {
    reverse_proxy 127.0.0.1:8000
}
```

Notes:
- Expose **only** port `443/tcp` externally.
- FastAPI listens only on `127.0.0.1:8000`, never on `0.0.0.0:8000`, so only Caddy is visible from the internet.
- If your home IP changes, use dynamic DNS such as DuckDNS.

If using `ACCESS_MODE=tailscale`, Caddy/public TLS is not needed: the tailnet already acts as an encrypted and authenticated channel.

## 4) Hardening

- Bearer token required in `ACCESS_MODE=public` (see above — linked to `/solve`, `/toggle`, `/status` in `backend_rpi4/main.py`).
- Rate-limit the endpoints (middleware or API gateway) — SymPy on arbitrary input can be a DoS vector.
- Validate and sanitise input on `/solve`.
- Run the app as a non-root user in containers.

## 5) Logging and Monitoring

- Ship logs to a centralised system (ELK, Promtail + Loki) or use cloud logging.
- Add health/metrics endpoints; collect with Prometheus if available.

## 6) CI/CD

- CI (`.github/workflows/ci.yml`) builds and runs tests (`pytest backend_rpi4 -q`) on every push/PR to `main`.
- Inject secrets from the platform (GitHub Actions secrets, Vault, etc.), never hardcoded.

## 7) Backup and Rollback

- Version Docker images and keep rollbacks simple: use tags and redeploy the previous tag if something goes wrong.

## 8) Sensitive Data in the Repository

Verify that `docs/` does not contain files with real IPs, hostnames, SSH key paths, or other identifying data before publishing or sharing the repository. If such files have already been committed, they must be removed from Git history as well (`git filter-repo` + force-push), not just deleted in the latest commit.