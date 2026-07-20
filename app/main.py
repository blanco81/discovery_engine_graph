# app/main.py
from fastapi import FastAPI
import logging
from app.adapters.driving.api.routes import router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

app = FastAPI(
    title="Motor de Descubrimiento de Complejidad",
    description="API para inferencia a ciegas, validación multi-agente y detección de patrones emergentes.",
    version="1.0.0"
)

app.include_router(router)