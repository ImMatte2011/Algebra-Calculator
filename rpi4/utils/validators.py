from fastapi import Depends, Header, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from rpi4.config import CONFIG


def verify_bearer_token(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing authorization token")

    token = authorization.split(" ", 1)[1]
    if token != CONFIG["API_TOKEN"]:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return token
