from datetime import datetime
from typing import Optional, Dict, Any, List
import re

class Event:
    """Clase que representa un evento en el sistema."""
    
    # Estados válidos para un evento
    VALID_STATUSES = ['scheduled', 'cancelled', 'completed']
    
    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "",
        description: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: str = "scheduled",
        created_by: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        resource_ids: List[int] = None  # IDs de recursos asignados
    ):
        """
        Inicializa un nuevo evento.
        
        Args:
            id: ID único del evento (None para nuevo)
            title: Título del evento
            description: Descripción detallada
            start_time: Fecha y hora de inicio
            end_time: Fecha y hora de fin
            status: Estado (scheduled, cancelled, completed)
            created_by: Usuario que creó el evento
            created_at: Fecha de creación
            updated_at: Fecha de última actualización
            resource_ids: Lista de IDs de recursos asignados
        """
        self.id = id
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.resource_ids = resource_ids or []
        
        # Validaciones
        self._validate()
    
    def _validate(self):
        """Valida los datos del evento."""
        if not self.title.strip():
            raise ValueError("El título del evento no puede estar vacío")
        
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Estado inválido. Debe ser: {', '.join(self.VALID_STATUSES)}")
        
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el evento a diccionario.
        
        Returns:
            Dict con los atributos del evento
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resource_ids': self.resource_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        Crea un Evento desde un diccionario.
        
        Args:
            data: Diccionario con datos del evento
        
        Returns:
            Instancia de Event
        """
        # Función helper para convertir strings a datetime
        def parse_datetime(value):
            if isinstance(value, str):
                # Manejar diferentes formatos de fecha
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    # Intentar otros formatos comunes
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M']:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"No se pudo parsear la fecha: {value}")
            return value
        
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            start_time=parse_datetime(data.get('start_time')),
            end_time=parse_datetime(data.get('end_time')),
            status=data.get('status', 'scheduled'),
            created_by=data.get('created_by', ''),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            resource_ids=data.get('resource_ids', [])
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Event':
        """
        Crea un Evento desde una fila de la base de datos.
        
        Args:
            row: Diccionario con datos de la fila DB
        
        Returns:
            Instancia de Event
        """
        return cls(
            id=row.get('id'),
            title=row.get('title', ''),
            description=row.get('description', ''),
            start_time=row.get('start_time'),
            end_time=row.get('end_time'),
            status=row.get('status', 'scheduled'),
            created_by=row.get('created_by', ''),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    
    def __repr__(self) -> str:
        """Representación en string del evento."""
        return f"Event(id={self.id}, title='{self.title[:20]}...', start={self.start_time})"
    
    def __str__(self) -> str:
        """Representación legible del evento."""
        start_str = self.start_time.strftime('%d/%m/%Y %H:%M') if self.start_time else 'N/A'
        end_str = self.end_time.strftime('%H:%M') if self.end_time else 'N/A'
        return f"{self.title} - {start_str} a {end_str} [{self.status}]"
    
    def duration_minutes(self) -> Optional[int]:
        """
        Calcula la duración del evento en minutos.
        
        Returns:
            Duración en minutos o None si no hay fechas
        """
        if self.start_time and self.end_time:
            diff = self.end_time - self.start_time
            return int(diff.total_seconds() / 60)
        return None
    
    def is_active(self) -> bool:
        """
        Verifica si el evento está activo (programado).
        
        Returns:
            True si el evento está scheduled
        """
        return self.status == 'scheduled'
    
    def is_past(self) -> bool:
        """
        Verifica si el evento ya pasó.
        
        Returns:
            True si el evento ya terminó
        """
        if self.end_time:
            return self.end_time < datetime.now()
        return False
    
    def is_ongoing(self) -> bool:
        """
        Verifica si el evento está en curso ahora.
        
        Returns:
            True si el evento está ocurriendo ahora
        """
        now = datetime.now()
        if self.start_time and self.end_time:
            return self.start_time <= now <= self.end_time
        return False
    
    def add_resource(self, resource_id: int):
        """Añade un recurso al evento."""
        if resource_id not in self.resource_ids:
            self.resource_ids.append(resource_id)
    
    def remove_resource(self, resource_id: int):
        """Elimina un recurso del evento."""
        if resource_id in self.resource_ids:
            self.resource_ids.remove(resource_id)
    
    def has_resources(self) -> bool:
        """Verifica si el evento tiene recursos asignados."""
        return len(self.resource_ids) > 0

# Prueba del modelo
if __name__ == "__main__":
    print("🧪 Probando modelo Event...")
    
    # Crear evento de prueba
    test_event = Event(
        title="Reunión de Planificación",
        description="Reunión inicial para planificar el proyecto",
        start_time=datetime(2024, 1, 15, 10, 0),
        end_time=datetime(2024, 1, 15, 11, 30),
        status="scheduled",
        created_by="admin",
        resource_ids=[1, 3, 5]
    )
    
    print(f"✅ Evento creado: {test_event}")
    print(f"📏 Duración: {test_event.duration_minutes()} minutos")
    print(f"🎯 Activo: {test_event.is_active()}")
    print(f"⏳ Pasado: {test_event.is_past()}")
    print(f"🔧 En curso: {test_event.is_ongoing()}")
    print(f"📦 Recursos: {test_event.resource_ids}")
    print(f"📊 Tiene recursos: {test_event.has_resources()}")
    
    # Probar conversión a dict y de vuelta
    event_dict = test_event.to_dict()
    print(f"\n📋 Convertido a dict: {list(event_dict.keys())}")
    
    event_from_dict = Event.from_dict(event_dict)
    print(f"🔄 Recreado desde dict: {event_from_dict}")
    
    print("\n🎉 ¡Modelo Event probado exitosamente!")