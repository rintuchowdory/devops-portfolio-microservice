from fastapi import APIRouter, HTTPException

from app.models.schemas import K8sNamespace, K8sResponse
from app.services.store import get_kubernetes

router = APIRouter()


@router.get("/kubernetes", response_model=K8sResponse, summary="Kubernetes cluster overview")
async def kubernetes_overview():
    return get_kubernetes()


@router.get("/kubernetes/{namespace_id}", response_model=K8sNamespace, summary="Single namespace")
async def get_namespace(namespace_id: str):
    data = get_kubernetes()
    for ns in data.namespaces:
        if ns.id == namespace_id:
            return ns
    raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
