import os
from dotenv import load_dotenv
from pathlib import Path

# Subir dos niveles: desde app/config/ hacia la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """
    Configuración central del Motor de Descubrimiento.
    Lee las variables de entorno cargadas por python-dotenv.
    """
    
    # --- Fase A: Pozo Relacional (RDBMS) ---
    #RDBMS_URL: str = os.getenv("RDBMS_URL", "sqlite:///./default.db")
    
    # --- Fase B: Grafo Dinámico (Neo4j) ---
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "intergraf2024")
    
    # --- Fase C: Orquestación de Agentes (LLM) ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant") # <--- CAMBIA ESTO
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
    
    # --- API ---
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))

# Instancia global de configuración
settings = Settings()
