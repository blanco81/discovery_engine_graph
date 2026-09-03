# app/core/services/domain_router.py
import logging
from typing import List, Dict
from app.core.domain.models import Column

logger = logging.getLogger(__name__)

class DomainRouter:
    PROFILES = {
        "education": {
            "keywords": ["student", "course", "room", "professor", "grade", "campus", "enrollment", "estudiante", "curso", "sala", "profesor", "nota", "campus", "matricula", "aluno", "estudante", "sala", "professor", "nota", "campus", "matricula"],
            "rules": ["Student/Estudiante/Aluno ID always points to the main student table.", "Room/Sala ID always points to the rooms table.", "A grade/nota column should NOT point to a student ID."],
            "verbs": ["ENROLLED_IN", "LOCATED_IN", "TAUGHT_BY", "OWNS"],
            "context": "Education / Educación / Educação Superior."
        },
        "ecommerce": {
            "keywords": ["order", "product", "customer", "payment", "shipment", "cart", "invoice", "orden", "producto", "cliente", "pago", "envio", "carrito", "factura", "pedido", "produto", "cliente", "pagamento", "envio", "carrinho", "fatura"],
            "rules": ["Order/Pedido/Orden ID always points to the orders table.", "Customer/Cliente ID always points to the customers table.", "Product/Producto/Produto ID always points to the products table."],
            "verbs": ["PLACED_BY", "CONTAINS", "PAID_FOR", "SHIPPED_TO"],
            "context": "E-commerce / Comercio Electrónico / Comércio Eletrônico."
        },
        "salud": {
            "keywords": ["patient", "diagnosis", "doctor", "medical", "clinic", "appointment", "paciente", "diagnostico", "doctor", "medico", "clinica", "cita", "paciente", "diagnostico", "medico", "clinica", "consulta"],
            "rules": ["Patient/Paciente ID always points to the patients table.", "Doctor/Medico ID always points to the doctors/staff table.", "Diagnosis code should not point to a patient ID."],
            "verbs": ["TREATED_BY", "DIAGNOSED_WITH", "SCHEDULED_FOR", "PERFORMED_BY"],
            "context": "Salud Pública y Privada. Gestión clínica, pacientes y citas médicas."
        },
        "hospitalar": {
            "keywords": ["hospital", "bed", "admission", "discharge", "ward", "emergency", "hospital", "cama", "ingreso", "alta", "sala", "emergencia", "hospital", "leito", "internacao", "alta", "enfermaria", "emergencia"],
            "rules": ["Bed/Cama/Leito ID always points to the hospital beds table.", "Admission/Ingreso/Internacao ID always points to the admissions table.", "Ward/Sala/Enfermaria is a location, not a patient."],
            "verbs": ["ADMITTED_TO", "LOCATED_IN", "MANAGED_BY", "ASSIGNED_TO"],
            "context": "Gestión Hospitalaria. Admisiones, camas, enfermería y emergencias."
        },
        "agronegocios": {
            "keywords": ["farm", "crop", "harvest", "cattle", "livestock", "soil", "finca", "cultivo", "cosecha", "ganado", "ganaderia", "suelo", "fazenda", "cultura", "colheita", "gado", "pecuaria", "solo"],
            "rules": ["Farm/Finca/Fazenda ID always points to the farms table.", "Crop/Cultivo/Cultura ID always points to the crops table.", "Harvest/Cosecha/Colheita ID points to the harvest table."],
            "verbs": ["GROWN_ON", "HARVESTED_IN", "MANAGED_BY", "LOCATED_IN"],
            "context": "Agronegocios. Gestión de fincas, cultivos, cosecha y maquinaria agrícola."
        },
        "agricultura": {
            "keywords": ["field", "planting", "irrigation", "seed", "fertilizer", "tractor", "campo", "siembra", "riego", "semilla", "fertilizante", "tractor", "campo", "plantio", "irrigacao", "semente", "fertilizante", "trator"],
            "rules": ["Field/Campo ID always points to the fields table.", "Irrigation/Riego ID always points to the irrigation systems table.", "Seed/Semilla ID always points to the seeds inventory."],
            "verbs": ["PLANTED_IN", "IRRIGATED_BY", "LOCATED_IN", "MANAGED_BY"],
            "context": "Agricultura. Siembra, riego, manejo de suelos y inventario agrícola."
        },
        "legal": {
            "keywords": ["case", "lawsuit", "attorney", "court", "client", "hearing", "lawyer", "caso", "demanda", "abogado", "juez", "cliente", "audiencia", "juicio", "processo", "advogado", "juiz", "cliente", "audiencia", "tribunal"],
            "rules": ["Case/Caso/Processo ID always points to the cases table.", "Client/Cliente ID always points to the clients table.", "Attorney/Abogado/Advogado ID always points to the lawyers table."],
            "verbs": ["REPRESENTED_BY", "FILED_IN", "ASSIGNED_TO", "MANAGED_BY"],
            "context": "Derecho Legal. Gestión de casos, demandas, audiencias y clientes legales."
        },
        "farmacologia": {
            "keywords": ["drug", "medication", "prescription", "trial", "pharmacy", "dosage", "medicamento", "receta", "medicamento", "ensayo", "farmacia", "dosis", "medicamento", "receita", "medicamento", "ensaio", "farmacia", "dose"],
            "rules": ["Drug/Medicamento ID always points to the drugs table.", "Prescription/Receta/Receita ID always points to the prescriptions table.", "Trial/Ensayo ID always points to the clinical trials table."],
            "verbs": ["PRESCRIBED_FOR", "TESTED_IN", "MANUFACTURED_BY", "DISPENSED_BY"],
            "context": "Farmacología. Medicamentos, recetas, ensayos clínicos y farmacias."
        },
        "logistica": {
            "keywords": ["warehouse", "route", "freight", "supply", "chain", "inventory", "almacen", "ruta", "carga", "suministro", "cadena", "inventario", "armazem", "rota", "carga", "suprimento", "cadeia", "inventario"],
            "rules": ["Warehouse/Almacen/Armazem ID always points to the warehouses table.", "Route/Ruta/Rota ID always points to the routes table.", "Freight/Carga ID always points to the shipments table."],
            "verbs": ["STORED_IN", "SHIPPED_VIA", "SUPPLIED_BY", "LOCATED_IN"],
            "context": "Logística. Almacenes, rutas de distribución, inventario y cadena de suministro."
        },
        "transporte": {
            "keywords": ["vehicle", "fleet", "trip", "driver", "passenger", "ticket", "vehiculo", "flota", "viaje", "conductor", "pasajero", "boleto", "veiculo", "frota", "viagem", "motorista", "passageiro", "passagem"],
            "rules": ["Vehicle/Vehiculo/Veiculo ID always points to the vehicles table.", "Driver/Conductor/Motorista ID always points to the drivers table.", "Trip/Viaje/Viagem ID always points to the trips table."],
            "verbs": ["DRIVEN_BY", "ASSIGNED_TO", "TRAVELED_ON", "MANAGED_BY"],
            "context": "Transporte. Gestión de flotas, conductores, viajes y pasajeros."
        },
        "construccion": {
            "keywords": ["site", "project", "contractor", "material", "equipment", "permit", "obra", "proyecto", "contratista", "material", "equipo", "permiso", "obra", "projeto", "contratado", "material", "equipamento", "permissao"],
            "rules": ["Site/Obra ID always points to the construction sites table.", "Project/Proyecto/Projeto ID always points to the projects table.", "Permit/Permiso/Permissao ID always points to the permits table."],
            "verbs": ["LOCATED_IN", "MANAGED_BY", "REQUIRED_FOR", "BUILT_ON"],
            "context": "Construcción. Obras, proyectos, permisos y gestión de materiales."
        },
        "empresarial": {
            "keywords": ["employee", "department", "hr", "payroll", "contract", "performance", "empleado", "departamento", "rrhh", "nomina", "contrato", "desempeno", "funcionario", "departamento", "rh", "folha", "contrato", "desempenho"],
            "rules": ["Employee/Empleado/Funcionario ID always points to the employees table.", "Department/Departamento ID always points to the departments table.", "Payroll/Nomina/Folha ID always points to the payroll table."],
            "verbs": ["WORKS_IN", "MANAGES", "ASSIGNED_TO", "REPORTS_TO"],
            "context": "Gestión Empresarial. Recursos humanos, nóminas, departamentos y contratos."
        },
        "gestion_documental": {
            "keywords": ["file", "record", "archive", "document", "folder", "author", "archivo", "registro", "archivo", "documento", "carpeta", "autor", "arquivo", "registro", "arquivo", "documento", "pasta", "autor"],
            "rules": ["File/File/Arquivo ID always points to the files table.", "Record/Registro ID always points to the records table.", "Author/Autor ID always points to the authors/users table."],
            "verbs": ["AUTHORED_BY", "STORED_IN", "CLASSIFIED_AS", "REFERENCES"],
            "context": "Gestión Documental. Archivos, registros, carpetas y control de versiones."
        },
        "financiero": {
            "keywords": ["transaction", "ledger", "budget", "expense", "revenue", "investment", "transaccion", "libro", "presupuesto", "gasto", "ingreso", "inversion", "transacao", "razao", "orcamento", "despesa", "receita", "investimento"],
            "rules": ["Transaction/Transaccion/Transacao ID always points to the transactions table.", "Budget/Presupuesto/Orcamento ID always points to the budgets table.", "Expense/Gasto/Despesa ID always points to the expenses table."],
            "verbs": ["RECORDED_IN", "ALLOCATED_TO", "GENERATED_BY", "MANAGED_BY"],
            "context": "Sector Financiero. Transacciones, presupuestos, gastos y inversiones."
        },
        "contabilidad": {
            "keywords": ["invoice", "journal", "balance", "account", "tax", "ledger", "factura", "diario", "balance", "cuenta", "impuesto", "libro", "fatura", "diario", "balanco", "conta", "imposto", "livro"],
            "rules": ["Invoice/Factura/Fatura ID always points to the invoices table.", "Account/Cuenta/Conta ID always points to the chart of accounts.", "Journal/Diario ID always points to the journal entries table."],
            "verbs": ["POSTED_TO", "BILLED_TO", "RECORDED_IN", "BALANCES_WITH"],
            "context": "Contabilidad. Facturas, asientos contables, cuentas y impuestos."
        },
        "bancario": {
            "keywords": ["account", "loan", "credit", "debit", "card", "transfer", "bank", "cuenta", "prestamo", "credito", "debito", "tarjeta", "transferencia", "banco", "conta", "emprestimo", "credito", "debito", "cartao", "transferencia", "banco"],
            "rules": ["Account/Cuenta/Conta ID always points to the bank accounts table.", "Loan/Prestamo/Emprestimo ID always points to the loans table.", "Card/Tarjeta/Cartao ID always points to the cards table."],
            "verbs": ["ISSUED_BY", "LINKED_TO", "TRANSFERRED_TO", "OWNS"],
            "context": "Sector Bancario. Cuentas, préstamos, tarjetas de crédito y transferencias."
        },
        "policial": {
            "keywords": [
                "identit", "operation", "meeting", "asset", "communication", "financial", "footprint", "weapon", "border", "vehicle", "crime", "suspect", "evidence", "investigation", "policia", "crimen", "sospechoso", "evidencia", "investigacao"
            ],
            "rules": [
                "Identity/Identidad ID always points to the main identities table.",
                "Operation/Operacion ID always points to the operations table.",
                "Asset/Vehiculo ID always points to the vehicles/asset table."
            ],
            "verbs": ["INVESTIGATED_BY", "PARTICIPATED_IN", "LOCATED_IN", "COMMUNICATED_WITH", "FINANCED_BY", "MANAGED_BY"],
            "context": "Seguridad Nacional e Inteligencia Policial. Gestión de identidades, operaciones, comunicaciones y movimientos."
        },
        "generic": {
            "keywords": [],
            "rules": ["The origin must be a logical attribute of the destination."],
            "verbs": ["BELONGS_TO", "ASSOCIATED_WITH", "REFERENCES"],
            "context": "General Information System / Sistema de Información General / Sistema de Informação Geral."
        }
    }

    def detect_domain(self, columns: List[Column]) -> str:
        text = " ".join([c.table_name.lower() for c in columns])
        scores = {}
        for domain, profile in self.PROFILES.items():
            if domain == "generic": continue
            score = sum(1 for kw in profile["keywords"] if kw in text)
            scores[domain] = score
        best_match = max(scores, key=scores.get) if scores else "generic"
        if scores.get(best_match, 0) > 0:
            logger.info(f"Dominio detectado: {best_match}")
            return best_match
        else:
            logger.info("Dominio no identificado. Usando perfil genérico.")
            return "generic"

    def get_profile(self, domain_name: str) -> Dict:
        return self.PROFILES.get(domain_name, self.PROFILES["generic"])