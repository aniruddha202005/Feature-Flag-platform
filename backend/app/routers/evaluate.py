from fastapi import APIRouter, Depends, Query

from app.deps import get_evaluation_service
from app.schemas import (
    BatchEvaluateRequest,
    BatchEvaluationResult,
    EvaluateRequest,
    EvaluationResult,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/v1", tags=["evaluate"])


@router.get("/evaluate", response_model=EvaluationResult)
def evaluate_get(
    flag_key: str = Query(min_length=1),
    user_id: str = Query(min_length=1, max_length=200),
    service: EvaluationService = Depends(get_evaluation_service),
):
    return service.evaluate(flag_key, user_id)


@router.post("/evaluate", response_model=EvaluationResult)
def evaluate_post(payload: EvaluateRequest, service: EvaluationService = Depends(get_evaluation_service)):
    return service.evaluate(payload.flag_key, payload.user_id, payload.attributes)


@router.post("/evaluate/batch", response_model=BatchEvaluationResult)
def evaluate_batch(
    payload: BatchEvaluateRequest, service: EvaluationService = Depends(get_evaluation_service)
):
    return service.evaluate_many(payload.flag_keys, payload.user_id, payload.attributes)
