"""
ConstraintValidator - Validador para restricciones entre recursos.
"""
from typing import List, Dict, Any, Tuple
from services.constraint_service import ConstraintService

class ConstraintValidator:
    """Validador para restricciones entre recursos."""
    
    def __init__(self, constraint_service: ConstraintService):
        self.constraint_service = constraint_service
    
    def validate_resources(self, resource_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Valida una combinación de recursos contra todas las restricciones.
        
        Returns:
            Lista de violaciones encontradas
        """
        return self.constraint_service.validate_resources(resource_ids)
    
    def can_resources_be_used_together(self, resource_ids: List[int]) -> Tuple[bool, List[str]]:
        """
        Verifica si un conjunto de recursos puede usarse juntos.
        
        Returns:
            Tuple (can_use_together, error_messages)
        """
        violations = self.validate_resources(resource_ids)
        
        if not violations:
            return True, []
        
        error_messages = [v['message'] for v in violations]
        return False, error_messages