import sys, os
sys.path.insert(0, os.path.abspath('./app'))

import networkx as nx
import logging
from app.core.domain.emergence import EmergenceEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def create_base_graph():
    """Crea el grafo base validado (Etapa 3)"""
    G = nx.DiGraph()
    G.add_edge("observations", "patients", weight=0.98)
    G.add_edge("patients", "cities", weight=1.0)
    return G

def main():
    print("--- INICIO DEL PIPELINE (ETAPA 4: EMERGENCIA) ---")
    engine = EmergenceEngine()
    
    # Estado normal del sistema (t0)
    G_t0 = create_base_graph()
    sig_t0 = engine.calculate_spectral_signature(G_t0)
    
    # Historial de índices de emergencia
    emergence_history = []
    threshold_theta = 0.15  # Umbral de emergencia
    
    # Simulamos 5 pasos temporales
    for t in range(1, 6):
        print(f"\n--- Tiempo t={t} ---")
        G_t = create_base_graph() # Copiamos el grafo base
        
        if t == 2:
            # ANOMALÍA TRANSITORIA: Añadimos una arista temporal por error
            print("⚠️ Evento: Ruido transitorio detectado (Arista espuria)")
            G_t.add_edge("inventory", "patients", weight=0.99)
            
        elif t >= 3:
            # PATRÓN EMERGENTE: Una nueva tabla/community se integra permanentemente
            print("🌐 Evento: Nueva estructura macroscópica emergiendo (Nueva tabla 'labs')")
            G_t.add_node("labs")
            G_t.add_edge("labs", "patients", weight=0.95) # Laboratorios apuntan a pacientes
            
        # 1. Calcular firma espectral actual
        sig_t = engine.calculate_spectral_signature(G_t)
        
        # 2. Calcular Índice de Emergencia E(P,t) comparando con t0
        e_p_t = engine.calculate_emergence_index(sig_t, sig_t0)
        emergence_history.append(e_p_t)
        print(f"Índice de Emergencia E(P,t): {e_p_t:.4f} (Umbral θ = {threshold_theta})")
        
        # 3. Validar Persistencia
        is_emergence = engine.validate_persistence(emergence_history, threshold=threshold_theta, window=3)
        
        if is_emergence:
            print("🚨 ALERTA DE PATRÓN EMERGENTE PERSISTENTE DETECTADA 🚨")
            print("   -> El sistema ha cambiado de régimen estructural.")
        elif e_p_t > threshold_theta:
            print("⏳ Anomalía detectada, esperando persistencia temporal...")
        else:
            print("✅ Sistema estable. Sin desviaciones significativas.")

if __name__ == "__main__":
    main()