# Security Policy

## Overview

Algebra-Calculator is a personal project consisting of three components:
a FastAPI backend on Raspberry Pi 4, an Android bridge app, and ESP32
firmware. This document describes how security is handled, what the
known risks are, and how to report vulnerabilities.

## Supported Versions

This project has no stable release yet. Only the current `main` branch
is actively maintained and considered for fixes.

## Reporting a Vulnerability

If you find a security issue, **do not open a public GitHub Issue**.

Contact directly via the email listed on the GitHub profile, or open a
[private security advisory](../../security/advisories/new) on GitHub.

Include:
- Description of the issue and affected component (backend, app, firmware)
- Steps to reproduce
- Potential impact in your assessment
- Suggested fix if you have one

You will receive a response within 7 days. Since this is a personal
project, there is no bug bounty program.

## Security Model

### Network access to the backend

The backend supports two mutually exclusive access modes, set via
`ACCESS_MODE` in `.env`:

| Mode | How the Pi is reached | Token enforced |
|---|---|---|
| `public` *(default)* | Public internet via Caddy HTTPS on `:443` | Yes — `API_TOKEN` on every request |
| `tailscale` | Tailscale tailnet only | No — tailnet is the perimeter |

In `public` mode, all three endpoints (`/solve`, `/status`) require a
valid `Authorization: Bearer <token>` header. The token is validated in
`backend_rpi4/utils/validators.py`. Starting the server in production
(`ENV=production`) with a default or empty token raises an error at
startup.

In `tailscale` mode, traffic is encrypted end-to-end by Tailscale and
only reachable by authenticated devices in the tailnet. The bearer token
is not checked, but the perimeter is the tailnet access control.

### API input validation

The `/solve` endpoint accepts a mathematical expression string and passes
it through SymPy's parser (`backend_rpi4/math_engine/parser.py`). The
parser uses SymPy's `parse_expr` with explicit transformation rules — it
does **not** use `eval()` or `exec()`. Arbitrary code execution via the
expression field is not possible through this path.

Known limitations:
- Very long or deeply nested expressions can cause high CPU usage on the
  Pi (SymPy is not bounded in time). Rate limiting at the proxy level
  (Caddy middleware or `slowapi`) is recommended before exposing this
  publicly.
- The parser only handles single-variable expressions in `x`. Expressions
  with other variable names or multi-variable inputs return an error.

### BLE communication (ESP32 ↔ Android)

Bluetooth Low Energy is used only on the local link between the ESP32
and the Android phone. This channel:
- Is not encrypted at the application layer — BLE pairing/bonding
  provides the link-layer security.
- Does not carry any authentication token (the token lives only in the
  Android app's SharedPreferences and is sent only over HTTPS).
- Is short-range by nature (~10m). The threat of a remote attacker
  intercepting BLE traffic is low in typical use.

### Android app secrets

The API token and server URL are stored in Android `SharedPreferences`
(encrypted by default on Android 6+, via `EncryptedSharedPreferences`
if explicitly used). They are **never hardcoded in the source code**.

The app uses HTTPS for all communication with the backend. The logging
interceptor is set to `BASIC` level to avoid logging request/response
bodies (which would expose the token in Logcat).

### Secrets in this repository

- `.env` files with real tokens are excluded by `.gitignore` and must
  never be committed.
- `local.properties` (Android SDK path) is excluded by `.gitignore`.
- Keystore files (`*.jks`, `*.keystore`) must never be committed.
- `docs/temp/` is excluded from Git tracking and must not contain real
  IP addresses, hostnames, or SSH key paths.

## Known Non-Issues

The following are acknowledged design choices, not vulnerabilities:

- **`_pending_result = [None]` in ESP32 firmware**: MicroPython is
  single-threaded; a mutable list is the idiomatic way to pass data from
  an IRQ handler to the main loop without a real queue.
- **No rate limiting in FastAPI itself**: Rate limiting is delegated to
  the reverse proxy (Caddy). Implementing it at the application level is
  planned but not yet done.
- **BLE not bonded**: The ESP32 does not enforce BLE bonding/pairing with
  a specific phone. In a home network this is acceptable. If you use this
  in a public or shared environment, bonding should be added.

## Changelog

Security-relevant changes are noted in [CHANGELOG.md](CHANGELOG.md)
(to be added when the project reaches a stable release).