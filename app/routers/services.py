from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Service, ServiceListResponse, ServiceStatus
from app.services.store import get_service, get_services

router = APIRouter()


@router.get("/services", response_model=ServiceListResponse, summary="List all services")
async def list_services(
    status: ServiceStatus | None = Query(None, description="Filter by status"),
    namespace: str | None = Query(None, description="Filter by K8s namespace"),
    tag: str | None = Query(None, description="Filter by tag"),
):
    data = get_services()
    svcs = data.services

    if status:
        svcs = [s for s in svcs if s.status == status]
    if namespace:
        svcs = [s for s in svcs if s.namespace == namespace]
    if tag:
        svcs = [s for s in svcs if tag in s.tags]

    return ServiceListResponse(
        total=len(svcs),
        up=sum(1 for s in svcs if s.status == ServiceStatus.UP),
        degraded=sum(1 for s in svcs if s.status == ServiceStatus.DEGRADED),
        down=sum(1 for s in svcs if s.status == ServiceStatus.DOWN),
        services=svcs,
    )


@router.get("/services/{service_id}", response_model=Service, summary="Get a single service")
async def get_single_service(service_id: str):
    svc = get_service(service_id)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return svc
