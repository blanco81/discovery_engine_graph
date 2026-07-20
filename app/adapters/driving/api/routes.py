# app/adapters/driving/api/routes.py
from fastapi import APIRouter
from app.core.services.inference_service import InferenceService

router = APIRouter()

@router.get("/")
def read_root():
    return {"status": "online", "message": "Motor de Descubrimiento de Complejidad operativo."}

@router.post("/api/v1/discovery/run")
def run_discovery():
    """
    Ejecuta el pipeline completo de descubrimiento sobre el Pozo Relacional.
    """
    service = InferenceService()
    result = service.run_discovery_pipeline()
    return {
        "message": "Pipeline completado",
        "data": result
    }