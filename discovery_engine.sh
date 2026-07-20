#!/bin/bash

# Nombre del directorio raíz del proyecto
PROJECT_NAME="discovery_engine"

echo "🚀 Inicializando estructura de proyecto para: $PROJECT_NAME"

# Crear directorios principales (Arquitectura Hexagonal)
mkdir -p $PROJECT_NAME/core/domain
mkdir -p $PROJECT_NAME/core/ports
mkdir -p $PROJECT_NAME/core/services
mkdir -p $PROJECT_NAME/adapters/driving/api
mkdir -p $PROJECT_NAME/adapters/db
mkdir -p $PROJECT_NAME/adapters/agents
mkdir -p $PROJECT_NAME/config
mkdir -p tests

# Crear archivos __init__.py para hacer módulos Python
touch $PROJECT_NAME/__init__.py
touch $PROJECT_NAME/core/__init__.py
touch $PROJECT_NAME/core/domain/__init__.py
touch $PROJECT_NAME/core/ports/__init__.py
touch $PROJECT_NAME/core/services/__init__.py
touch $PROJECT_NAME/adapters/__init__.py
touch $PROJECT_NAME/adapters/driving/__init__.py
touch $PROJECT_NAME/adapters/driving/api/__init__.py
touch $PROJECT_NAME/adapters/db/__init__.py
touch $PROJECT_NAME/adapters/agents/__init__.py
touch tests/__init__.py

# Crear archivos base del Núcleo (Core)
touch $PROJECT_NAME/core/domain/models.py
touch $PROJECT_NAME/core/domain/metrics.py
touch $PROJECT_NAME/core/ports/relational_port.py
touch $PROJECT_NAME/core/ports/graph_port.py
touch $PROJECT_NAME/core/ports/orchestrator_port.py
touch $PROJECT_NAME/core/services/inference_service.py
touch $PROJECT_NAME/core/services/signature_service.py
touch $PROJECT_NAME/core/services/emergence_service.py

# Crear archivos base de Adaptadores
touch $PROJECT_NAME/adapters/driving/api/routes.py
touch $PROJECT_NAME/adapters/db/sqlalchemy_adapter.py
touch $PROJECT_NAME/adapters/db/neo4j_adapter.py
touch $PROJECT_NAME/adapters/agents/langgraph_adapter.py

# Crear archivos de configuración y entrada
touch $PROJECT_NAME/main.py
touch $PROJECT_NAME/config/config.py
touch $PROJECT_NAME/.env
touch requirements.txt

echo "📄 Poblando archivos de configuración y dependencias..."

# Poblar el archivo .env (Agnóstico al LLM)
cat << 'EOF' > $PROJECT_NAME/.env
# ==========================================
# Configuración del Motor de Descubrimiento
# ==========================================

# --- Fase A: Pozo Relacional (RDBMS) ---
RDBMS_URL=postgresql://user:password@localhost:5432/blind_db

# --- Fase B: Grafo Dinámico (Neo4j) ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# --- Fase C: Orquestación de Agentes (LLM) ---
# Opciones de proveedor: "openai", "anthropic", "ollama", "azure"
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3
# LLM_API_KEY=tu-api-key-aqui  # Descomentar si usas openai/anthropic

# --- Configuración del Servidor (FastAPI) ---
APP_HOST=0.0.0.0
APP_PORT=8000
EOF

# Poblar el archivo config.py usando python-dotenv
cat << 'EOF' > $PROJECT_NAME/config/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Construir la ruta al archivo .env (asumiendo que está en la raíz del proyecto)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """
    Configuración central del Motor de Descubrimiento.
    Lee las variables de entorno cargadas por python-dotenv.
    """
    
    # --- Fase A: Pozo Relacional (RDBMS) ---
    RDBMS_URL: str = os.getenv("RDBMS_URL", "sqlite:///./default.db")
    
    # --- Fase B: Grafo Dinámico (Neo4j) ---
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # --- Fase C: Orquestación de Agentes (LLM) ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "llama3")
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY") # Opcional
    
    # --- API ---
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))

# Instancia global de configuración
settings = Settings()
EOF

# Poblar requirements.txt con las dependencias iniciales
cat << 'EOF' > requirements.txt
fastapi
uvicorn
sqlalchemy
neo4j
python-dotenv
langchain
langgraph
networkx
scipy
scikit-learn
pandas
EOF

echo "✅ Estructura creada y configurada exitosamente en: $PROJECT_NAME/"
echo "Para empezar a trabajar:"
echo "1. cd $PROJECT_NAME"
echo "2. pip install -r ../requirements.txt"