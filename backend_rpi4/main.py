from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from math_engine.engine import solve_expression
from utils.logger import info

app = FastAPI(title="Calc Algebraica API")

is_active = True


class SolveRequest(BaseModel):
    expression: str
    type: str
    action: Optional[str] = None


class ToggleRequest(BaseModel):
    active: bool


class StatusResponse(BaseModel):
    is_active: bool


class SolveResponse(BaseModel):
    ok: bool
    result: str


@app.on_event("startup")
def startup_event():
    info("Starting RPi calculator API")


@app.on_event("shutdown")
def shutdown_event():
    info("Stopping RPi calculator API")


@app.post("/solve", response_model=SolveResponse)
def solve(request: SolveRequest):
    if not is_active:
        raise HTTPException(status_code=403, detail="Service is inactive")

    result = solve_expression(
        request.expression,
        request.type,
        request.action
    )
    
    if result is None or result.startswith("error:"):
        raise HTTPException(status_code=400, detail=result or "Unable to solve expression")

    return SolveResponse(ok=True, result=result)


@app.post("/toggle", response_model=StatusResponse)
def toggle(request: ToggleRequest):
    global is_active
    is_active = request.active
    return StatusResponse(is_active=is_active)


@app.get("/status", response_model=StatusResponse)
def status():
    return StatusResponse(is_active=is_active)
