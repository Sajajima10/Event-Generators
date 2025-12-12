"""
ConstraintService - Servicio CRUD para manejar restricciones en el gestor de eventos.
Maneja restricciones entre recursos (co-requisitos, exclusiones, etc.)
"""
import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging

# ========== CONFIGURAR IMPORTS ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from models.constraint import Constraint
    from database.db_connection import DatabaseConnection
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    IMPORT_SUCCESS = False

# ========== CLASE PRINCIPAL ==========
if IMPORT_SUCCESS:
    logger = logging.getLogger(__name__)
    
    class ConstraintService:
        """Servicio para operaciones CRUD con restricciones."""
        
        def __init__(self, db_connection: Optional[DatabaseConnection] = None):
            self.db = db_connection or DatabaseConnection()
            logger.info("✅ ConstraintService inicializado")
        
        def create_constraint(self, constraint: Constraint) -> Optional[Constraint]:
            """Crea una nueva restricción."""
            try:
                logger.info(f"Creando restricción: {constraint.name}")
                
                query = """
                    INSERT INTO constraints (name, constraint_type, description, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                params = (
                    constraint.name,
                    constraint.constraint_type,
                    constraint.description,
                    constraint.is_active,
                    constraint.created_at or datetime.now()
                )
                
                constraint_id = self.db.execute_query(query, params)
                
                if constraint_id:
                    constraint.id = constraint_id
                    
                    # Crear reglas si hay
                    for rule in constraint.rules:
                        self.add_rule_to_constraint(constraint_id, rule)
                    
                    logger.info(f"✅ Restricción creada con ID: {constraint_id}")
                    return constraint
                
                return None
                
            except Exception as e:
                logger.error(f"❌ Error al crear restricción: {e}")
                return None
        
        def get_constraint(self, constraint_id: int) -> Optional[Constraint]:
            """Obtiene una restricción por ID."""
            try:
                query = "SELECT * FROM constraints WHERE id = %s"
                result = self.db.execute_query(query, (constraint_id,), fetch=True)
                
                if result:
                    constraint_data = result[0]
                    constraint = Constraint.from_db_row(constraint_data)
                    
                    # Obtener reglas
                    rules_query = """
                        SELECT * FROM constraint_rules 
                        WHERE constraint_id = %s
                    """
                    rules_result = self.db.execute_query(rules_query, (constraint_id,), fetch=True)
                    constraint.rules = rules_result if rules_result else []
                    
                    return constraint
                
                return None
                
            except Exception as e:
                logger.error(f"❌ Error al obtener restricción: {e}")
                return None
        
        def add_rule_to_constraint(self, constraint_id: int, rule: Dict[str, Any]) -> bool:
            """Añade una regla a una restricción."""
            try:
                query = """
                    INSERT INTO constraint_rules 
                    (constraint_id, resource_id, rule_type, related_resource_id, value)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                params = (
                    constraint_id,
                    rule['resource_id'],
                    rule['rule_type'],
                    rule.get('related_resource_id'),
                    rule.get('value')
                )
                
                result = self.db.execute_query(query, params)
                return result is not None
                
            except Exception as e:
                logger.error(f"❌ Error al añadir regla: {e}")
                return False
        
        def validate_resources(self, resource_ids: List[int]) -> List[Dict[str, Any]]:
            """
            Valida si una combinación de recursos viola alguna restricción.
            
            Returns:
                Lista de violaciones encontradas
            """
            violations = []
            
            try:
                # Obtener todas las restricciones activas
                query = """
                    SELECT c.*, cr.* 
                    FROM constraints c
                    JOIN constraint_rules cr ON c.id = cr.constraint_id
                    WHERE c.is_active = TRUE
                    ORDER BY c.id
                """
                
                results = self.db.execute_query(query, fetch=True)
                if not results:
                    return violations
                
                # Procesar cada restricción
                current_constraint = None
                rules = []
                
                for row in results:
                    if current_constraint != row['constraint_id']:
                        if current_constraint and rules:
                            # Validar con las reglas acumuladas
                            constraint_violations = self._validate_with_rules(resource_ids, rules)
                            if constraint_violations:
                                violations.extend(constraint_violations)
                        
                        current_constraint = row['constraint_id']
                        rules = []
                    
                    rules.append({
                        'resource_id': row['resource_id'],
                        'rule_type': row['rule_type'],
                        'related_resource_id': row['related_resource_id'],
                        'value': row['value']
                    })
                
                # Validar última restricción
                if rules:
                    constraint_violations = self._validate_with_rules(resource_ids, rules)
                    if constraint_violations:
                        violations.extend(constraint_violations)
                
                return violations
                
            except Exception as e:
                logger.error(f"❌ Error al validar recursos: {e}")
                return violations
        
        def _validate_with_rules(self, resource_ids: List[int], rules: List[Dict]) -> List[Dict]:
            """Valida recursos contra un conjunto de reglas."""
            violations = []
            
            for resource_id in resource_ids:
                # Encontrar reglas que aplican a este recurso
                resource_rules = [r for r in rules if r['resource_id'] == resource_id]
                
                for rule in resource_rules:
                    if rule['rule_type'] == 'requires':
                        related_id = rule['related_resource_id']
                        if related_id and related_id not in resource_ids:
                            violations.append({
                                'type': 'missing_requirement',
                                'message': f'El recurso {resource_id} requiere el recurso {related_id}',
                                'resource_id': resource_id,
                                'related_resource_id': related_id
                            })
                    
                    elif rule['rule_type'] == 'excludes':
                        related_id = rule['related_resource_id']
                        if related_id and related_id in resource_ids:
                            violations.append({
                                'type': 'mutual_exclusion',
                                'message': f'El recurso {resource_id} excluye el recurso {related_id}',
                                'resource_id': resource_id,
                                'related_resource_id': related_id
                            })
            
            return violations

    # ===== PRUEBAS =====
    if __name__ == "__main__":
        print("\n🧪 Probando ConstraintService...")
        
        try:
            service = ConstraintService()
            print("✅ ConstraintService creado")
            
            # Aquí irían pruebas específicas
            print("🎯 Servicio listo para usar")
            
        except Exception as e:
            print(f"❌ Error: {e}")