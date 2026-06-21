from fastapi import Header, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from config import CONFIG


def verify_bearer_token(authorization: str = Header(None)):
    """Verify the Bearer token, unless ACCESS_MODE=tailscale.

    When ACCESS_MODE is "tailscale", the API is assumed to be reachable only
    through the Tailscale tailnet, which is already the access perimeter, so
    the token check is skipped. When ACCESS_MODE is "public" (default), the
    API may be reachable from the public Internet (e.g. behind Caddy) and a
    valid Bearer token is required on every request.
    """
    if CONFIG["ACCESS_MODE"] == "tailscale":
        return None

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authorization token",
        )

    token = authorization.split(" ", 1)[1]
    if token != CONFIG["API_TOKEN"]:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return token
