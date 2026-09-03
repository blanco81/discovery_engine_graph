# app/adapters/driving/api/routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from app.core.services.inference_service import InferenceService

router = APIRouter()

# Modelo de entrada para la API
class DiscoveryRequest(BaseModel):
    db_url: str
    rho_threshold: Optional[float] = 0.90
    domain: Optional[str] = "auto"
    language: Optional[str] = "es"

@router.get("/")
async def read_root():
    return {"status": "online", "message": "Motor de Descubrimiento de Complejidad operativo."}

@router.post("/api/v1/discovery/run")
async def run_discovery(request: DiscoveryRequest):
    """
    Ejecuta el pipeline de descubrimiento sobre un RDBMS externo.
    Soporta SQLite, MySQL/MariaDB y PostgreSQL.
    """
    service = InferenceService()
    
    try:
        result = await service.run_discovery_pipeline(
            db_url=request.db_url,
            rho_threshold=request.rho_threshold,
            domain=request.domain,
            language=request.language
        )
        return {
            "message": "Pipeline completado",
            "data": result
        }
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/api/v1/baseline/reset")
async def reset_baseline(request: DiscoveryRequest):
    """Activa la bandera de reset. El sistema asimilará la nueva normalidad en la próxima ejecución manteniendo el historial."""
    from app.adapters.db.state_adapter import InternalStateAdapter
    state_adapter = InternalStateAdapter()
    await state_adapter.init_db()
    await state_adapter.request_reset(request.db_url)
    return {"message": "Reset solicitado. El sistema aprenderá la nueva normalidad en la próxima ejecución manteniendo el historial gráfico."}


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Motor de Descubrimiento de Complejidad</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.27.0/cytoscape.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
        <style>
            body { font-family: 'Inter', sans-serif; }
            #cy { height: 500px; width: 100%; background-color: #f8fafc; border-radius: 0.5rem; border: 1px solid #e2e8f0; }
        </style>
    </head>
    <body class="bg-gray-100 text-gray-800">

        <div class="container mx-auto p-6">
            <!-- Cabecera -->
            <div class="flex flex-wrap justify-between items-center mb-6 gap-4">
                <h1 class="text-3xl font-bold text-indigo-900">🧠 Motor de Descubrimiento de Complejidad</h1>
                <div class="flex gap-2 items-center">
                    <input id="dbUrl" type="text" placeholder="postgresql://user:pass@localhost:5432/db" class="border p-2 rounded w-80 text-sm">
                    <select id="domainSelect" class="border p-2 rounded text-sm bg-white">
                        <option value="auto">Auto Domain</option>
                        <option value="education">Education</option>
                        <option value="ecommerce">E-commerce</option>
                        <option value="salud">Salud</option>
                        <option value="hospitalar">Hospitalar</option>
                        <option value="agronegocios">Agronegocios</option>
                        <option value="agricultura">Agricultura</option>
                        <option value="legal">Legal</option>
                        <option value="farmacologia">Farmacología</option>
                        <option value="logistica">Logística</option>
                        <option value="transporte">Transporte</option>
                        <option value="construccion">Construcción</option>
                        <option value="empresarial">Empresarial</option>
                        <option value="gestion_documental">Gestión Doc.</option>
                        <option value="financiero">Financiero</option>
                        <option value="contabilidad">Contabilidad</option>
                        <option value="bancario">Bancario</option>
                        <option value="policial">Policial</option>
                    </select>
                    <select id="langSelect" class="border p-2 rounded text-sm bg-white">
                        <option value="es">Español</option>
                        <option value="en">English</option>
                        <option value="pt">Português</option>
                    </select>
                    <button onclick="runDiscovery()" class="bg-indigo-600 text-white px-4 py-2 rounded font-bold hover:bg-indigo-700 text-sm">Ejecutar</button>
                    <button onclick="resetBaseline()" class="bg-gray-500 text-white px-4 py-2 rounded font-bold hover:bg-gray-600 text-sm">Resetear</button>
                </div>
            </div>

            <!-- Semáforo de Alerta -->
            <div id="alertBox" class="bg-green-100 text-green-800 p-4 rounded-lg mb-2 text-center font-bold text-xl transition-all">
                ✅ Sistema Estable - Esperando ejecución...
            </div>
            
            <!-- Alerta de Mismatch de Dominio (NUEVO) -->
            <div id="domainWarningBox" class="bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 p-3 rounded mb-6 text-sm hidden">
                <span id="domainWarningText"></span>
            </div>

            <!-- Cuadrantes (Layout 2 Columnas Igualadas) -->
            <div class="grid grid-cols-2 gap-6 mb-6">
                <!-- Grafo -->
                <div class="bg-white p-4 rounded-lg shadow border">
                    <h2 class="text-xl font-semibold mb-2 text-gray-700">Grafo de Conocimiento (Ontología Emergente)</h2>
                    <div id="cy"></div>
                </div>
                <!-- Serie Temporal Ampliada -->
                <div class="bg-white p-4 rounded-lg shadow border">
                    <div class="flex justify-between items-center mb-2">
                        <h2 class="text-xl font-semibold text-gray-700">Serie Temporal de Emergencia</h2>
                        <button onclick="resetZoom()" class="text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 px-2 py-1 rounded">Restablecer Zoom</button>
                    </div>
                    <p class="text-xs text-gray-400 mb-2">💡 Rueda del ratón: Zoom. Clic y arrastrar: Desplazar.</p>
                    <div style="height: 430px;">
                        <canvas id="emergenceChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Evidencia y Reporte -->
            <div class="grid grid-cols-3 gap-6">
                <!-- Métricas -->
                <div class="bg-white p-4 rounded-lg shadow border">
                    <h2 class="text-xl font-semibold mb-2 text-gray-700">Métricas del Sistema</h2>
                    <div id="metrics" class="text-sm space-y-2 text-gray-600">
                        <p>Ejecuta el motor para ver las métricas.</p>
                    </div>
                </div>
                <!-- Reporte IA -->
                <div class="col-span-2 bg-white p-4 rounded-lg shadow border">
                    <h2 class="text-xl font-semibold mb-2 text-gray-700">Informe Ejecutivo IA</h2>
                    <div id="report" class="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded border max-h-96 overflow-y-auto">
                        El informe aparecerá aquí...
                    </div>
                </div>
            </div>
        </div>

        <script>
            let chart;
            const ctx = document.getElementById('emergenceChart').getContext('2d');
            
            if (window.ChartZoom) {
                Chart.register(ChartZoom);
            }
            
            function initChart(historyData = []) {
                if(chart) chart.destroy();
                
                let labels = historyData.map((_, i) => `t=${i}`);
                let data = historyData;
                let thresholdData = new Array(data.length).fill(0.15);
                
                chart = new Chart(ctx, {
                    type: 'line',
                    data: { 
                        labels: labels, 
                        datasets: [
                            { 
                                label: 'E(P,t) - Índice de Emergencia', 
                                data: data, 
                                borderColor: 'rgb(79, 70, 229)', 
                                backgroundColor: 'rgba(79, 70, 229, 0.2)',
                                tension: 0.3, 
                                fill: true,
                                borderWidth: 3,
                                pointRadius: 4
                            },
                            {
                                label: 'Umbral θ (0.15)',
                                data: thresholdData,
                                borderColor: 'rgb(220, 38, 38)',
                                borderDash: [5, 5],
                                fill: false,
                                pointRadius: 0,
                                borderWidth: 2
                            }
                        ] 
                    },
                    options: { 
                        maintainAspectRatio: false,
                        scales: { 
                            x: { title: { display: true, text: 'Iteración (Tiempo)' } },
                            y: { beginAtZero: true, suggestedMax: 0.3, title: { display: true, text: 'Magnitud de Emergencia' } }
                        },
                        plugins: {
                            legend: { display: true, position: 'bottom', labels: { font: { size: 10 } } },
                            zoom: {
                                pan: { enabled: true, mode: 'x' },
                                zoom: { wheel: { enabled: true, speed: 0.1 }, pinch: { enabled: true }, mode: 'x' }
                            }
                        }
                    }
                });
            }
            
            function resetZoom() {
                if(chart) chart.resetZoom();
            }

            initChart();

            async function runDiscovery() {
                const dbUrl = document.getElementById('dbUrl').value;
                if(!dbUrl) return alert("Por favor ingresa la URL de la BD");
                
                const domain = document.getElementById('domainSelect').value;
                const lang = document.getElementById('langSelect').value;
                
                document.getElementById('alertBox').textContent = "⏳ Procesando pipeline matemático y agentes IA...";
                document.getElementById('alertBox').className = "bg-yellow-100 text-yellow-800 p-4 rounded-lg mb-2 text-center font-bold text-xl animate-pulse";
                document.getElementById('domainWarningBox').classList.add('hidden');

                try {
                    const res = await fetch('/api/v1/discovery/run', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ db_url: dbUrl, rho_threshold: 0.9, domain: domain, language: lang })
                    });
                    const data = await res.json();
                    if(!res.ok) throw new Error(data.detail || "Error en la API");
                    
                    renderData(data.data);
                } catch (e) {
                    document.getElementById('alertBox').textContent = "❌ Error: " + e.message;
                    document.getElementById('alertBox').className = "bg-red-100 text-red-800 p-4 rounded-lg mb-2 text-center font-bold text-xl";
                }
            }

            async function resetBaseline() {
                const dbUrl = document.getElementById('dbUrl').value;
                if(!dbUrl) return alert("Por favor ingresa la URL de la BD");
                
                const res = await fetch('/api/v1/baseline/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ db_url: dbUrl })
                });
                alert("Reset solicitado. En la próxima ejecución, el sistema asimilará la nueva normalidad y la gráfica caerá a 0 manteniendo el historial.");
            }

            function renderData(data) {
                // 1. Semáforo
                const ept = data.emergence_index;
                const isEm = data.is_emergence;
                const alert = document.getElementById('alertBox');
                
                if(isEm) {
                    alert.textContent = `🚨 ALERTA: Cambio de Régimen Detectado | E(P,t): ${ept.toFixed(4)}`;
                    alert.className = "bg-red-100 text-red-800 p-4 rounded-lg mb-2 text-center font-bold text-xl animate-pulse";
                } else if(ept > 0.05) {
                    alert.textContent = `⏳ Anomalía Detectada (Esperando Persistencia) | E(P,t): ${ept.toFixed(4)}`;
                    alert.className = "bg-orange-100 text-orange-800 p-4 rounded-lg mb-2 text-center font-bold text-xl";
                } else {
                    alert.textContent = `✅ Sistema Estable | E(P,t): ${ept.toFixed(4)}`;
                    alert.className = "bg-green-100 text-green-800 p-4 rounded-lg mb-2 text-center font-bold text-xl";
                }

                // 1.5 Alerta de Dominio (NUEVO)
                if(data.domain_warning) {
                    document.getElementById('domainWarningText').innerText = data.domain_warning;
                    document.getElementById('domainWarningBox').classList.remove('hidden');
                } else {
                    document.getElementById('domainWarningBox').classList.add('hidden');
                }

                // 2. Métricas
                document.getElementById('metrics').innerHTML = `
                    <p><b>Relaciones Matemáticas (pINDs):</b> ${data.total_raw_pinds}</p>
                    <p><b>Relaciones Validadas (IA):</b> ${data.total_validated_pinds}</p>
                    <p><b>Índice de Emergencia Actual:</b> ${ept.toFixed(4)}</p>
                    <p><b>Umbral (θ):</b> 0.1500</p>
                    <p><b>Dominio Aplicado:</b> ${data.domain_used || 'N/A'}</p>
                `;

                // 3. Reporte
                document.getElementById('report').innerText = data.executive_report;

                // 4. Grafo (Cytoscape)
                const elements = [];
                const nodes = new Set();
                data.validated_relationships.forEach(rel => {
                    const match = rel.match(/(\\w+)\\.\\w+ -\\[(\\w+)\\]-> (\\w+)\\.\\w+.*/);
                    if(match) {
                        const [_, t1, label, t2] = match;
                        if(!nodes.has(t1)) { nodes.add(t1); elements.push({ data: { id: t1, label: t1 } }); }
                        if(!nodes.has(t2)) { nodes.add(t2); elements.push({ data: { id: t2, label: t2 } }); }
                        elements.push({ data: { source: t1, target: t2, label: label } });
                    }
                });

                cytoscape({
                    container: document.getElementById('cy'),
                    elements: elements,
                    style: [
                        { selector: 'node', style: { 'background-color': '#4f46e5', 'label': 'data(label)', 'color': '#1e293b', 'text-valign': 'bottom', 'text-halign': 'center', 'font-size': '10px', 'font-weight': 'bold', 'width': 25, 'height': 25 } },
                        { selector: 'edge', style: { 'width': 2, 'line-color': '#94a3b8', 'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'label': 'data(label)', 'font-size': '8px', 'color': '#64748b', 'text-rotation': 'autorotate', 'text-background-color': '#ffffff', 'text-background-opacity': 0.8, 'text-background-padding': '1px' } }
                    ],
                    layout: { name: 'cose' }
                });

                // 5. Gráfico (Chart.js) 
                let hist = data.emergence_history || [];
                initChart(hist);
            }
        </script>
    </body>
    </html>
    """