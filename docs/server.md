# FastAPI Server — Calc Algebraica (backend_rpi4)

FastAPI server that receives an expression/equation/inequality and returns the result computed with SymPy. Designed to run on Raspberry Pi 4 behind an HTTPS reverse proxy (see [deploy.md](deploy.md) and [network.md](network.md)).

## Installation

Recommended inside a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy the example file and edit the values:

```bash
cp .env.example .env
# then edit .env: API_TOKEN, ACCESS_MODE, API_HOST, API_PORT, LOG_LEVEL
```

For ESP32 devices, copy `.env.esp32.example` instead and follow [esp32_settings.md](esp32_settings.md).

The server reads configuration from environment variables via `python-dotenv` (see `backend_rpi4/config.py`): no need to modify the code directly.

`ACCESS_MODE` (`public` by default, or `tailscale`) determines whether the Bearer token is required — details in [deploy.md](deploy.md#access-public-vs-tailscale). In production (`ENV=production`) with `ACCESS_MODE=public`, startup intentionally fails if `API_TOKEN` has not been changed from its default value.

## Start (development)

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
- `POST /toggle` — body: `{ "active": true|false }`, enables/disables the service
- `GET /status` — returns `{ "is_active": true|false }`

All three require the `Authorization: Bearer <token>` header when `ACCESS_MODE=public` (default). When `ACCESS_MODE=tailscale` the check is skipped.

> Note: `is_active` is a **global** state, shared by all clients — disabling the service disables it for everyone, not just the caller of `/toggle`. This is fine for personal use; if the service becomes multi-user in the future it will need to be made per-user/per-token.

## Notes on the Math Engine

The engine (`backend_rpi4/math_engine/`) **does not handle integrals or derivatives**: requests containing them return an error.

## Tests

```bash
pytest backend_rpi4/tests -q
```

or, using the repo configuration:

```bash
pytest -q
```