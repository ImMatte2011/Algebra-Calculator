from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .math_engine.engine import solve_expression
from .utils.logger import info
from .utils.validators import verify_bearer_token

app = FastAPI(title="Algebra Calculator API")


class SolveRequest(BaseModel):
    expression: str
    type: str
    action: Optional[str] = None


class SolveResponse(BaseModel):
    ok: bool
    result: str


class HealthResponse(BaseModel):
    status: str


@app.on_event("startup")
def startup_event():
    info("Starting Algebra Calculator API")


@app.on_event("shutdown")
def shutdown_event():
    info("Stopping Algebra Calculator API")


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest, token: str = Depends(verify_bearer_token)):
    result = solve_expression(
        request.expression,
        request.type,
        request.action
    )

    if result is None or result.startswith("error:"):
        raise HTTPException(
            status_code=400,
            detail=result or "Unable to solve expression"
        )

    return SolveResponse(ok=True, result=result)


@app.get("/status", response_model=HealthResponse)
def status(token: str = Depends(verify_bearer_token)):
    """Health check. Returns ok if the server is running."""
    return HealthResponse(status="ok")
