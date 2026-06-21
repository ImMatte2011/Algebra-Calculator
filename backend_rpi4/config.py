import os
from dotenv import load_dotenv

load_dotenv()

# ACCESS_MODE controls how the API is meant to be reached and therefore
# whether the Bearer token is enforced:
#   - "public":    API is reachable from the public Internet (e.g. behind
#                   Caddy on :443). Bearer token is REQUIRED on every request.
#   - "tailscale": API is only reachable through a Tailscale tailnet, which
#                   already acts as the access perimeter. Bearer token check
#                   is skipped.
#
# Default is "public" on purpose (fail-safe): if this is left unset, the API
# behaves as if it could be exposed to anyone, and requires a token rather
# than silently trusting the network.
ACCESS_MODE = os.getenv("ACCESS_MODE", "public").strip().lower()
if ACCESS_MODE not in ("public", "tailscale"):
    raise RuntimeError(
        f"Invalid ACCESS_MODE '{ACCESS_MODE}': must be 'public' or 'tailscale'"
    )

CONFIG = {
    "API_HOST": os.getenv("API_HOST", "127.0.0.1"),
    "API_PORT": int(os.getenv("API_PORT", "8000")),
    "API_TOKEN": os.getenv("API_TOKEN", "replace_with_secure_token"),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    "ACCESS_MODE": ACCESS_MODE,
}

# Validation: in production, a non-default API token is required whenever
# the API could be reached without the Tailscale perimeter (i.e. ACCESS_MODE
# == "public"). When ACCESS_MODE == "tailscale" we don't enforce a strong
# token, since the tailnet itself is the access control.
ENV = os.getenv("ENV", "development").lower()
if ENV == "production" and ACCESS_MODE == "public":
    token = CONFIG.get("API_TOKEN")
    if not token or token == "replace_with_secure_token":
        raise RuntimeError(
            "API_TOKEN must be set to a secure value in production when "
            "ACCESS_MODE=public"
        )
