from datetime import datetime
from typing import Optional, Dict, Any, List

class Resource:
    """Clase que representa un recurso en el sistema."""
    
    # Tipos de recursos predefinidos
    RESOURCE_TYPES = ['room', 'equipment', 'person', 'vehicle', 'other']
    
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        resource_type: str = "",
        quantity: int = 1,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        current_usage: int = 0  # Cuántas unidades están en uso actualmente
    ):
        self.id = id
        self.name = name
        self.description = description
        self.resource_type = resource_type.lower() if resource_type else ""
        self.quantity = quantity
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.current_usage = current_usage
        
        self._validate()
    
    def _validate(self):
        """Valida los datos del recurso."""
        if not self.name.strip():
            raise ValueError("El nombre del recurso no puede estar vacío")
        
        if self.resource_type and self.resource_type not in self.RESOURCE_TYPES:
            raise ValueError(f"Tipo de recurso inválido. Debe ser: {', '.join(self.RESOURCE_TYPES)}")
        
        if self.quantity < 0:
            raise ValueError("La cantidad no puede ser negativa")
        
        if self.current_usage < 0:
            raise ValueError("El uso actual no puede ser negativo")
        
        if self.current_usage > self.quantity:
            raise ValueError("El uso actual no puede exceder la cantidad total")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el recurso a diccionario."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'resource_type': self.resource_type,
            'quantity': self.quantity,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'current_usage': self.current_usage,
            'available': self.available_quantity()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Resource':
        """Crea un Recurso desde un diccionario."""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            resource_type=data.get('resource_type', ''),
            quantity=data.get('quantity', 1),
            is_active=data.get('is_active', True),
            created_at=created_at,
            current_usage=data.get('current_usage', 0)
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Resource':
        """Crea un Recurso desde una fila de la base de datos."""
        return cls(
            id=row.get('id'),
            name=row.get('name', ''),
            description=row.get('description', ''),
            resource_type=row.get('resource_type', ''),
            quantity=row.get('quantity', 1),
            is_active=bool(row.get('is_active', True)),
            created_at=row.get('created_at'),
            current_usage=row.get('current_usage', 0)
        )
    
    def __repr__(self) -> str:
        return f"Resource(id={self.id}, name='{self.name}', type='{self.resource_type}', qty={self.quantity})"
    
    def __str__(self) -> str:
        status = "✅ Activo" if self.is_active else "⛔ Inactivo"
        return f"{self.name} [{self.resource_type}] - {self.available_quantity()}/{self.quantity} disponibles {status}"
    
    def available_quantity(self) -> int:
        """Calcula la cantidad disponible del recurso."""
        if not self.is_active:
            return 0
        return max(0, self.quantity - self.current_usage)
    
    def is_available(self, required_quantity: int = 1) -> bool:
        """Verifica si hay suficiente cantidad del recurso."""
        return self.is_active and self.available_quantity() >= required_quantity
    
    def use(self, quantity: int = 1) -> bool:
        """Intenta usar una cantidad del recurso."""
        if self.is_available(quantity):
            self.current_usage += quantity
            return True
        return False
    
    def release(self, quantity: int = 1):
        """Libera una cantidad del recurso."""
        self.current_usage = max(0, self.current_usage - quantity)
    
    def utilization_percentage(self) -> float:
        """Calcula el porcentaje de uso del recurso."""
        if self.quantity == 0:
            return 0.0
        return (self.current_usage / self.quantity) * 100