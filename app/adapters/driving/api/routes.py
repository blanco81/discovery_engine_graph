from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.services.inference_service import InferenceService
from app.adapters.db.state_adapter import InternalStateAdapter

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

@router.post("/api/v1/baseline/reset")
async def reset_baseline(request: DiscoveryRequest):
    """Resetea la línea base del motor para una base de datos específica."""
    state_adapter = InternalStateAdapter()
    await state_adapter.init_db()
    await state_adapter.reset_state(request.db_url)
    return {"message": f"Línea base reseteada exitosamente para {request.db_url}. El sistema aprenderá una nueva normalidad en la próxima ejecución."}

