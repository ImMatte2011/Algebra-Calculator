from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from rpi4.api.schemas import ExpressionRequest, SolveResponse
from rpi4.services.calculator_service import CalculatorService
from rpi4.utils.validators import verify_bearer_token

router = APIRouter()
service = CalculatorService()


@router.post("/solve", response_model=SolveResponse)
def solve_expression(request: ExpressionRequest, token: str = Depends(verify_bearer_token)):
    result = service.solve(request.expr)
    if result is None:
        raise HTTPException(status_code=400, detail="Unable to solve expression")
    return SolveResponse(ok=True, result=result)
