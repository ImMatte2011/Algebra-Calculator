# FastAPI server — Calc Algebraica (backend_rpi4)

Server FastAPI che riceve un'espressione/equazione/disequazione e restituisce
il risultato calcolato con SymPy. Pensato per girare su Raspberry Pi 4 dietro
un reverse proxy HTTPS (vedi [deploy.md](deploy.md) e [network.md](network.md)).

## Installazione

Consigliato dentro un virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configurazione

Copia il file di esempio e modifica i valori:

```bash
cp .env.example .env
# poi modifica .env: API_TOKEN, ACCESS_MODE, API_HOST, API_PORT, LOG_LEVEL
```

Per i dispositivi ESP32, copia invece `.env.esp32.example` e segui
[esp32_settings.md](esp32_settings.md).

Il server legge la configurazione dalle variabili d'ambiente tramite
`python-dotenv` (vedi `backend_rpi4/config.py`): non serve modificare il
codice a mano.

`ACCESS_MODE` (`public` di default, oppure `tailscale`) decide se il Bearer
token è obbligatorio — dettagli in [deploy.md](deploy.md#accesso-pubblico-vs-tailscale).
In produzione (`ENV=production`) con `ACCESS_MODE=public`, l'avvio fallisce
volutamente se `API_TOKEN` non è stato cambiato dal valore di default.

## Avvio (sviluppo)

```bash
uvicorn backend_rpi4.main:app --reload --host 127.0.0.1 --port 8000
```

## API

- `POST /solve` — body:
  ```json
  { "expression": "x^2-1=0", "type": "equation", "action": null }
  ```
  - `type`: `"expression"`, `"equation"` or `"inequality"`
  - `action` (only for `type: "expression"`): `"simplify"`, `"expand"` or `"factor"`
- `GET /status` — returns `{ "status": "ok" }`

Both endpoints require the `Authorization: Bearer <token>` header when
`ACCESS_MODE=public` (default). When `ACCESS_MODE=tailscale`, the token check
is skipped.

## Note sul motore matematico

Il motore (`backend_rpi4/math_engine/`) **non gestisce integrali o
derivate**: le richieste che li contengono restituiscono un errore.

## Test

```bash
pytest backend_rpi4/tests -q
```

oppure, usando la configurazione del repo:

```bash
pytest -q
```
