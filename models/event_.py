# Representacion del modelo de evento, con fecha de inicio y fin(Incluye las horas)

from datetime import datetime
from typing import Optional, Dict, Any, List
import re

class Event:
     pass
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
        resource_ids: List[int] = None
    ):
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

        self._validate()


# Valida los datos de inicio del evento
def _validate(self):
        
        if not self.title.strip():
            raise ValueError("El título del evento no puede estar vacío")
        
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Estado inválido. Debe ser: {', '.join(self.VALID_STATUSES)}")
        
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("La hora de fin debe ser posterior a la hora de inicio")

def to_dict(self) -> Dict[str, Any]:
    # COnvierte el evento en un diccionario obviamente
    
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
         
    def parse_datetime(value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                    
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
        updated_at=parse_datetime(data.get('updated_at')),            resource_ids=data.get('resource_ids', [])
    )



  