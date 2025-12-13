from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

class Constraint:
    """Clase que representa una restricción en el sistema."""
    
    # Tipos de restricciones
    CONSTRAINT_TYPES = ['co_requirement', 'mutual_exclusion', 'capacity']
    
    # Tipos de reglas
    RULE_TYPES = ['requires', 'excludes', 'max_capacity', 'min_quantity']
    
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        constraint_type: str = "",
        description: str = "",
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        rules: List[Dict[str, Any]] = None  # Lista de reglas de esta restricción
    ):
        self.id = id
        self.name = name
        self.constraint_type = constraint_type
        self.description = description
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.rules = rules or []
        
        self._validate()
    
    def _validate(self):
        """Valida los datos de la restricción."""
        if not self.name.strip():
            raise ValueError("El nombre de la restricción no puede estar vacío")
        
        if self.constraint_type not in self.CONSTRAINT_TYPES:
            raise ValueError(f"Tipo de restricción inválido. Debe ser: {', '.join(self.CONSTRAINT_TYPES)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la restricción a diccionario."""
        return {
            'id': self.id,
            'name': self.name,
            'constraint_type': self.constraint_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rules': self.rules,
            'rules_count': len(self.rules)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Constraint':
        """Crea una Constraint desde un diccionario."""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            constraint_type=data.get('constraint_type', ''),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            created_at=created_at,
            rules=data.get('rules', [])
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Constraint':
        """Crea una Constraint desde una fila de la base de datos."""
        return cls(
            id=row.get('id'),
            name=row.get('name', ''),
            constraint_type=row.get('constraint_type', ''),
            description=row.get('description', ''),
            is_active=bool(row.get('is_active', True)),
            created_at=row.get('created_at')
        )
    
    def __repr__(self) -> str:
        return f"Constraint(id={self.id}, name='{self.name}', type='{self.constraint_type}')"
    
    def __str__(self) -> str:
        status = "✅ Activa" if self.is_active else "⛔ Inactiva"
        return f"{self.name} [{self.constraint_type}] - {len(self.rules)} reglas {status}"
    
    def add_rule(
        self,
        resource_id: int,
        rule_type: str,
        related_resource_id: Optional[int] = None,
        value: Optional[int] = None
    ) -> Dict[str, Any]:
        """Añade una regla a la restricción."""
        if rule_type not in self.RULE_TYPES:
            raise ValueError(f"Tipo de regla inválido. Debe ser: {', '.join(self.RULE_TYPES)}")
        
        rule = {
            'resource_id': resource_id,
            'rule_type': rule_type,
            'related_resource_id': related_resource_id,
            'value': value
        }
        
        self.rules.append(rule)
        return rule
    
    def get_rules_for_resource(self, resource_id: int) -> List[Dict[str, Any]]:
        return [rule for rule in self.rules if rule['resource_id'] == resource_id]
    
    def get_required_resources(self, resource_id: int) -> List[int]:
        required = []
        for rule in self.get_rules_for_resource(resource_id):
            if rule['rule_type'] == 'requires' and rule['related_resource_id']:
                required.append(rule['related_resource_id'])
        return required
    
    def get_excluded_resources(self, resource_id: int) -> List[int]:
        excluded = []
        for rule in self.get_rules_for_resource(resource_id):
            if rule['rule_type'] == 'excludes' and rule['related_resource_id']:
                excluded.append(rule['related_resource_id'])
        return excluded
    
    def get_capacity_limit(self, resource_id: int) -> Optional[int]:
        for rule in self.get_rules_for_resource(resource_id):
            if rule['rule_type'] == 'max_capacity':
                return rule['value']
        return None
    
    def check_violation(self, resource_ids: List[int]) -> Tuple[bool, str]:
        """Verifica si una combinación de recursos viola esta restricción."""
        if not self.is_active:
            return False, "Restricción inactiva"
        
        for resource_id in resource_ids:
            # Verificar requisitos
            for required_id in self.get_required_resources(resource_id):
                if required_id not in resource_ids:
                    return True, f"El recurso {resource_id} requiere el recurso {required_id}"
            
            # Verificar exclusiones
            for excluded_id in self.get_excluded_resources(resource_id):
                if excluded_id in resource_ids:
                    return True, f"El recurso {resource_id} excluye el recurso {excluded_id}"
            
        return False, "OK"