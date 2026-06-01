from pydantic import BaseModel


class ExpressionRequest(BaseModel):
    expr: str


class SolveResponse(BaseModel):
    ok: bool
    result: str


class ErrorResponse(BaseModel):
    ok: bool = False
    detail: str
