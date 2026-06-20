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
  - `type`: `"expression"`, `"equation"` o `"inequality"`
  - `action` (solo per `type: "expression"`): `"simplify"`, `"expand"` o `"factor"`
- `POST /toggle` — body: `{ "active": true|false }`, abilita/disabilita il servizio
- `GET /status` — restituisce `{ "is_active": true|false }`

Tutti e tre richiedono l'header `Authorization: Bearer <token>` quando
`ACCESS_MODE=public` (default). Quando `ACCESS_MODE=tailscale` il controllo
viene saltato.

> Nota: `is_active` è uno stato **globale**, condiviso da tutti i client —
> disattivare il servizio lo disattiva per chiunque lo usi, non solo per chi
> ha chiamato `/toggle`. Va bene per uso personale; se in futuro il
> servizio diventa multi-utente andrà reso per-utente/per-token.

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
