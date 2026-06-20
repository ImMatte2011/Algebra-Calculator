import requests
from typing import Optional


def solve(expr: str, url: str, token: Optional[str] = None, timeout: int = 5) -> dict:
    """Call the Calc Algebraica API `/solve` endpoint and return parsed JSON.

    Args:
        expr: expression string to send
        url: full URL to the `/solve` endpoint (e.g. http://127.0.0.1:8000/solve)
        token: optional bearer token
        timeout: request timeout seconds

    Returns:
        parsed JSON response as dict
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"expr": expr}
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
