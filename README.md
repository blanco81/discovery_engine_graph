# Motor de Descubrimiento de Complejidad
Detección de Patrones Emergentes en Grafos Dinámicos de Perfiles Multi-Fuente: una aproximación basada en firmas históricas dinámicas.

Este proyecto implementa un sistema autónomo de descubrimiento e inferencia diseñado para conectarse "a ciegas" a bases de datos transaccionales (RDBMS) opacas. Sin conocimiento previo de la semántica de negocio, el sistema infiere matemáticamente el grafo dinámico oculto en las tablas relacionales, calcula firmas históricas multidimensionales y detecta Patrones Emergentes Persistentes diferenciándolos de simples anomalías transitorias.

# Marco Teórico y Matemático

La investigación se sustenta en cuatro pilares fundamentales que integran el **Data Profiling**, el análisis de redes dinámicas y la teoría de la complejidad, proporcionando una base teórica y matemática para la detección de patrones emergentes en perfiles históricos.

## Pilar 1. Inferencia Ciega de Grafos

Este pilar se fundamenta en el descubrimiento automático de relaciones entre entidades mediante **Dependencias de Inclusión Parciales (Partial Inclusion Dependencies – pINDs)**, inspirado en los algoritmos **BINDER** y **SPIND** propuestos por Papenbrock et al.

El objetivo es inferir aristas probabilísticas entre conjuntos de atributos sin requerir conocimiento previo del esquema de datos, permitiendo tolerancia al ruido mediante un umbral de inclusión parcial.

La relación matemática se expresa como:

$$
r_1[X] \subseteq_{\rho} r_2[Y], \qquad 0 < \rho \leq 1
$$

donde:

- $r_1$ y $r_2$ representan relaciones o tablas de datos.
- $X$ y $Y$ corresponden a conjuntos de atributos.
- $\rho$ expresa el grado mínimo de inclusión aceptado, permitiendo manejar datos incompletos, inconsistentes o provenientes de múltiples fuentes.

---

## Pilar 2. Firmas Históricas 4D

Cada perfil histórico se representa mediante una firma multidimensional que integra información estructural, temporal y semántica.

### Firma estructural ($F_s$)

Se calculan vectores **NetSimile**, los cuales describen la topología local del grafo mediante características agregadas independientes de su tamaño, permitiendo comparar redes heterogéneas.

### Firma temporal ($F_t$)

La evolución histórica se modela mediante *kernels* de influencia temporal, inspirados en Rossi et al., donde los estados pasados contribuyen con diferentes pesos al estado actual.

Su formulación es:

$$
\Phi(t)=\sum_{k=0}^{T}\omega(k)\, s(G_{t-k})
$$

donde:

- $G_{t-k}$ representa el estado histórico del grafo.
- $s(G)$ corresponde a la función que extrae la firma estructural.
- $\omega(k)$ es el peso asignado a cada instante temporal.

### Firma semántica ($F_m$)

Los cambios conceptuales (*Concept Drift*) son identificados mediante la distancia de **Jensen-Shannon** entre distribuciones categóricas observadas en distintos períodos temporales, permitiendo detectar variaciones significativas en el significado o comportamiento de los perfiles.

---

## Pilar 3. Detección de Emergencia y Persistencia

Este pilar se apoya en la teoría de sistemas complejos, especialmente en los trabajos de Stephen Wolfram y Yaneer Bar-Yam.

La detección de patrones emergentes requiere no solo identificar desviaciones significativas respecto al comportamiento histórico, sino también comprobar que dichas variaciones persistan a lo largo del tiempo.

Para ello se emplea la descomposición espectral del Laplaciano del grafo, utilizando la estabilidad de sus autovalores como indicador de coherencia estructural temporal.

Un fenómeno será considerado un **Patrón Emergente** únicamente cuando cumpla simultáneamente dos condiciones:

- superar un umbral de significancia $\theta$;
- mantenerse estable durante múltiples ventanas temporales consecutivas.

Este criterio reduce significativamente los falsos positivos generados por anomalías transitorias.

---

## Pilar 4. Orquestación Multi-Agente

El procesamiento analítico se organiza mediante flujos de trabajo cíclicos implementados en **LangGraph**, donde múltiples agentes colaboran para validar hipótesis y reducir errores de inferencia.

La arquitectura incorpora un mecanismo de debate socrático entre dos agentes especializados:

- **Agente Proponente**, encargado de generar hipótesis y posibles patrones emergentes.
- **Agente Crítico**, responsable de cuestionar, verificar y contrastar dichas hipótesis utilizando evidencia proveniente de múltiples fuentes de información.

Este proceso iterativo permite realizar una validación *cross-source*, mejorar la consistencia de las inferencias y minimizar las alucinaciones propias de los modelos de lenguaje, incrementando la confiabilidad de los patrones emergentes detectados.

# Arquitectura del Sistema
El proyecto utiliza una Arquitectura Hexagonal (Ports and Adapters) para mantener el núcleo matemático aislado de las tecnologías de infraestructura.

- **Fase A (Pozo Relacional):** Conexión agnóstica mediante SQLAlchemy.
- **Fase B (Motor de Descubrimiento):** Orquestación en LangGraph y cálculos matemáticos (NetworkX, SciPy).
- **Fase C (Explicabilidad):** Generación de informes en lenguaje natural mediante LLM.

# Stack Tecnológico
- **API / Microservicios:** FastAPI, Uvicorn.
- **Persistencia Grafo:** Neo4j.
- **Acceso a Datos:** SQLAlchemy (Inferencia a ciegas por reflection).
- **Orquestación IA:** LangGraph, LangChain.
- **Motor LLM:** Llama 3.3 70B (vía API de Groq).
- **Cálculo Científico:** NumPy, SciPy, NetworkX, scikit-learn.

# Estructura del Proyecto
discovery_engine_graph/
├── app/
│   ├── adapters/                  # Adaptadores de infraestructura
│   │   ├── agents/                # Adaptadores de LLM (LangGraph)
│   │   │   └── langgraph_adapter.py
│   │   ├── db/                    # Adaptadores de base de datos
│   │   │   ├── sqlalchemy_adapter.py
│   │   │   └── neo4j_adapter.py
│   │   └── driving/               # Adaptadores de entrada (API)
│   │       └── api/
│   │           └── routes.py
│   ├── core/                      # NÚCLEO DE LA APLICACIÓN (Puro)
│   │   ├── domain/                # Entidades y matemáticas
│   │   │   ├── emergence.py       # Motor espectral y persistencia
│   │   │   ├── metrics.py         # NetSimile y Jensen-Shannon
│   │   │   └── models.py          # Perfil Dinámico, pINDs
│   │   ├── ports/                 # Interfaces (Contratos)
│   │   └── services/              # Casos de uso (Orquestación)
│   ├── config/                    # Carga de entorno (.env)
│   └── main.py                    # Punto de entrada FastAPI
├── tests/
├── .env
└── requirements.txt

# Guía de Instalación y Ejecución
# 1. Requisitos Previos
Python 3.10+
Una instancia de Neo4j (local o Docker).
Una API Key de Groq (para el LLM Llama 3.3).

# 2. Configuración
Clona el repositorio y crea un entorno virtual:
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt

Configura tu archivo .env en la raíz del proyecto:
# --- Fase A: Pozo Relacional (RDBMS) ---
RDBMS_URL=sqlite:///./test_blind.db

# --- Fase B: Grafo Dinámico (Neo4j) ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password

# --- Fase C: Orquestación de Agentes (LLM) ---
LLM_PROVIDER=groq
LLM_MODEL_NAME=llama-3.3-70b-versatile
LLM_API_KEY=gsk_tu_api_key_de_groq_aqui

# --- API ---
APP_HOST=0.0.0.0
APP_PORT=8000

# 3. Ejecución de Pruebas Unitarias
Hemos desarrollado scripts de prueba para validar cada etapa del pipeline:

Generar Base de Datos de Prueba:
-**python setup_test_db.py**

Probar Inferencia y Debate Socrático (Etapas 1 y 3):
Ejecuta el descubrimiento a ciegas y mira cómo los agentes debaten sobre la direccionalidad de las claves foráneas.
-**python test_etapa3.py**

Probar la Detección de Emergencia (Etapa 4):
Simula el paso del tiempo y la inyección de ruido vs. estructuras emergentes reales.
-**python test_etapa4.py**

# 4. Despliegue del Microservicio (Etapa 5)
Levanta la API documentada en FastAPI:

-**uvicorn app.main:app --reload --host 0.0.0.0 --port 8000**

Accede a la documentación interactiva (Swagger UI) en:
👉 http://127.0.0.1:8000/docs


# Notas para Entorno de Producción
Durante el desarrollo se identificaron las siguientes consideraciones para escalar el sistema:
-**Límites de Tasa (Rate Limits):** Al evaluar cientos de pINDs de forma secuencial, las APIs gratuitas de LLM (como Groq) devuelven errores 429 Too Many Requests.

--**Solución a implementar:** Procesamiento asíncrono por lotes (Batches) utilizando asyncio y la inclusión de retardos dinámicos (time.sleep) para mantenerse por debajo de los límites gratuitos.

--**Escalabilidad del Pozo Relacional:** Para bases de datos corporativas grandes (MySQL/PostgreSQL con miles de tablas), el algoritmo de pINDs requiere optimización de consultas (chunking horizontal y particionado por hash) para evitar cuellos de botella de E/S.