from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import get_flag_service
from app.schemas import AuditEventOut, FlagCreate, FlagOut, FlagUpdate
from app.services.flag_service import FlagService

router = APIRouter(prefix="/api/v1", tags=["flags"])


@router.get("/flags", response_model=list[FlagOut])
def list_flags(service: FlagService = Depends(get_flag_service)):
    return service.list_flags()


@router.post("/flags", response_model=FlagOut, status_code=status.HTTP_201_CREATED)
def create_flag(payload: FlagCreate, service: FlagService = Depends(get_flag_service)):
    return service.create_flag(payload)


@router.get("/flags/{key}", response_model=FlagOut)
def get_flag(key: str, service: FlagService = Depends(get_flag_service)):
    return service.get_flag(key)


@router.patch("/flags/{key}", response_model=FlagOut)
def update_flag(key: str, payload: FlagUpdate, service: FlagService = Depends(get_flag_service)):
    return service.update_flag(key, payload)


@router.post("/flags/{key}/toggle", response_model=FlagOut)
def toggle_flag(key: str, service: FlagService = Depends(get_flag_service)):
    return service.toggle_flag(key)


@router.delete("/flags/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flag(key: str, service: FlagService = Depends(get_flag_service)):
    service.delete_flag(key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit", response_model=list[AuditEventOut])
def list_audit(
    flag_key: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    service: FlagService = Depends(get_flag_service),
):
    return service.list_audit(flag_key, limit)
