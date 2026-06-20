# Deploy e sicurezza

## Accesso: pubblico vs Tailscale

Il server supporta due modalità di esposizione **alternative**, scelte con
la variabile `ACCESS_MODE` in `.env` (vedi `backend_rpi4/config.py` e
`backend_rpi4/utils/validators.py`):

| `ACCESS_MODE` | Come si raggiunge il Pi | Bearer token (`API_TOKEN`) |
|---|---|---|
| `public` *(default)* | Internet, dietro Caddy su `:443` | **Obbligatorio** su ogni richiesta |
| `tailscale` | Solo dalla tua tailnet Tailscale | Non verificato (la tailnet è già il perimetro) |

Il default è `public` volutamente (fail-safe): se qualcuno dimentica di
impostare la variabile, l'API richiede comunque un token invece di fidarsi
implicitamente della rete.

In produzione (`ENV=production`) con `ACCESS_MODE=public`, l'avvio fallisce
se `API_TOKEN` è ancora il valore di default — vedi `backend_rpi4/config.py`.

## 1) Environment e segreti

- Non mettere mai segreti nel codice sorgente. Usa `.env` in locale e un
  secrets manager in produzione.
- In Docker, preferisci `env_file` o Docker secrets (per Swarm/Kubernetes
  usa i secrets nativi).
- In produzione imposta `ENV=production` e un `API_TOKEN` forte se usi
  `ACCESS_MODE=public`.

## 2) Docker Compose

Esempio (vedi `docker-compose.yml` nella root): build context sulla root del
repo (il `Dockerfile` copia `requirements.txt` e `backend_rpi4/` da lì),
segreti passati via `env_file` invece che hard-coded:

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

## 3) TLS / Reverse proxy (Caddy)

Metti l'API dietro un reverse proxy (Caddy, Traefik, Nginx) che ottiene e
rinnova i certificati TLS automaticamente. Caddy è la scelta usata in questo
progetto, soprattutto in combinazione con `ACCESS_MODE=public`.

`caddy/Caddyfile`:

```
mio-dominio.duckdns.org {
    reverse_proxy 127.0.0.1:8000
}
```

Note:
- Esponi verso l'esterno **solo** la porta `443/tcp`.
- FastAPI resta in ascolto solo su `127.0.0.1:8000`, mai su `0.0.0.0:8000`,
  così da Internet si vede solo Caddy.
- Se il tuo IP di casa cambia, usa un DNS dinamico come DuckDNS.

Se invece usi `ACCESS_MODE=tailscale`, Caddy/TLS pubblico non sono
necessari: la tailnet fa già da canale cifrato e autenticato.

## 4) Hardening

- Bearer token richiesto in `ACCESS_MODE=public` (vedi sopra — collegato a
  `/solve`, `/toggle`, `/status` in `backend_rpi4/main.py`).
- Limita il rate sugli endpoint (middleware o API gateway) — SymPy su input
  arbitrari può essere un vettore di DoS.
- Valida e sanitizza l'input su `/solve`.
- Esegui l'app come utente non-root nei container.

## 5) Logging e monitoring

- Invia i log a un sistema centralizzato (ELK, Promtail + Loki) o usa
  logging cloud.
- Aggiungi endpoint di health/metrics; raccogli con Prometheus se
  disponibile.

## 6) CI/CD

- La CI (`.github/workflows/ci.yml`) builda ed esegue i test
  (`pytest backend_rpi4 -q`) ad ogni push/PR su `main`.
- Inietta i segreti dalla piattaforma (GitHub Actions secrets, Vault, ecc.),
  mai hard-coded.

## 7) Backup e rollback

- Versiona le immagini Docker e mantieni i rollback semplici: usa tag e
  rideploya il tag precedente in caso di problemi.

## 8) Dati sensibili nel repository

Verifica che `docs/` non contenga file con IP reali, hostname, percorsi di
chiavi SSH o altri dati identificativi prima di pubblicare o condividere il
repository. Se file simili sono già stati committati, vanno rimossi anche
dalla cronologia Git (`git filter-repo` + force-push), non solo cancellati
nell'ultimo commit.
