FastAPI server for Calc Algebraica

Install (recommended inside a virtualenv):

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Configuration:
- Copy the example `.env` and edit values:

```bash
cp .env.example .env
# then edit .env and set API_TOKEN, API_HOST, API_PORT as needed
```
- For ESP32 devices, copy `.env.esp32.example` to a file you will upload to the device or use when building firmware.

The server reads configuration from environment variables (via `python-dotenv`) so you no longer need to edit `rpi4/config.py` directly.

Run server (development):

```bash
uvicorn rpi4.main:app --reload --host 127.0.0.1 --port 8000
```

API:
- POST /solve — body: `{ "expr": "<expression>" }` (requires `Authorization: Bearer <token>` header)

Notes:
- The math engine will NOT process integrals or derivatives; requests containing them return an error.
- Tests: `python -m pytest -q` (requires `pytest` installed)
