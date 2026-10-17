# FastAPI Server — Algebra Calculator (backend_rpi4)

FastAPI server that receives mathematical requests and returns SymPy results.
It is designed to run on Raspberry Pi 4 behind an HTTPS reverse proxy (see
[deploy.md](deploy.md) and [network.md](network.md)).

## Installation

Recommended inside a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure `API_TOKEN`, `ACCESS_MODE`, and
`FUNCTIONS_FILE`. See [deploy.md](deploy.md) for access-mode guidance.
The server reads environment variables via `python-dotenv`.

`FUNCTIONS_FILE` defaults to `data/functions.json`. The Docker Compose
configuration mounts `./data` so saved user functions survive container
recreation. Back up this directory if you rely on custom functions.

## Start (development)

```bash
uvicorn backend_rpi4.main:app --reload --host 127.0.0.1 --port 8000
```

## API

- `POST /solve` — body:
  ```json
  {
    "expression": "x^2-1=0",
    "type": "equation",
    "action": null,
    "format": "plain",
    "steps": false
  }
  ```
  - `type` / `action`: `expression` (`simplify`, `expand`, `factor`), `equation`,
    `inequality`, `ineq_system`, `lin_system`, `number` (`primes`, `gcd`, `lcm`),
    `matrix` (`det`, `inv`, `trans`), or `function` (`define`, `list`, `delete`)
  - `format`: `plain` (default), `latex`, or `pretty`
  - `steps: true` adds solution steps to the response
  - Input is limited to 120 characters from lowercase letters, digits, and
    mathematical operators/delimiters
- Systems use `;` between equations/inequalities; number lists accept `,` or
  `;`; matrices use comma-separated cells and semicolon-separated rows.
- Define a stored function with an expression such as `f(x)=x^2+1`, then call
  it from later expressions; `function` actions also support `list` and
  `delete`.
- Responses contain `ok`, a `result` string prefixed with `result:`, and a
  `steps` array (empty unless requested).
- `GET /status` — returns `{ "status": "ok" }`

Both endpoints require the configured bearer token when `ACCESS_MODE=public`
(default). When `ACCESS_MODE=tailscale`, token checking is skipped.

## Math engine notes

Equations and inequalities are solved over the reals; linear systems are
limited to variables `x` and `y`. Integrals and derivatives are not supported.

## Tests

```bash
pytest backend_rpi4/tests -q
```

or, using the repo configuration:

```bash
pytest -q
```
