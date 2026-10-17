from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .math_engine.engine import solve_detailed
from .utils.logger import info
from .utils.validators import verify_bearer_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    info("Starting Algebra Calculator API")
    yield
    info("Stopping Algebra Calculator API")


app = FastAPI(title="Algebra Calculator API", lifespan=lifespan)


class SolveRequest(BaseModel):
    expression: str
    type: str
    action: Optional[str] = None
    format: str = "plain"
    steps: bool = False
    x_value: Optional[float] = None


class SolveResponse(BaseModel):
    ok: bool
    result: str
    steps: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest, token: str = Depends(verify_bearer_token)):
    output = solve_detailed(
        request.expression,
        request.type,
        request.action,
        x_value=request.x_value,
        fmt=request.format,
        steps=request.steps,
    )
    if "error" in output:
        raise HTTPException(status_code=400, detail="error:{}".format(output["error"]))
    return SolveResponse(
        ok=True,
        result="result:{}".format(output["result"]),
        steps=output["steps"],
    )


@app.get("/status", response_model=HealthResponse)
def status(token: str = Depends(verify_bearer_token)):
    """Health check. Returns ok if the server is running."""
    return HealthResponse(status="ok")
