from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.services.inference_service import InferenceService

router = APIRouter()

class DiscoveryRequest(BaseModel):
    db_url: str
    rho_threshold: Optional[float] = 0.90

@router.get("/")
async def read_root():
    return {"status": "online", "message": "Motor de Descubrimiento de Complejidad operativo."}

@router.post("/api/v1/discovery/run")
async def run_discovery(request: DiscoveryRequest):
    service = InferenceService()
    try:
        # Ahora esperamos (await) la ejecución asíncrona
        result = await service.run_discovery_pipeline(
            db_url=request.db_url,
            rho_threshold=request.rho_threshold
        )
        return {"message": "Pipeline completado", "data": result}
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")