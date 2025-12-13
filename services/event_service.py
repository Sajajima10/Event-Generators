import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from models.event import Event
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class EventService:
    
    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        self.db = db_connection or DatabaseConnection()
        logger.info("EventService inicializado")
    
    def create_event(self, event: Event) -> Optional[Event]:
        try:
            logger.info(f"Creando evento: {event.title}")
            
            query = """
                INSERT INTO events (
                    title, description, start_time, end_time, 
                    status, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                event.title,
                event.description,
                event.start_time,
                event.end_time,
                event.status,
                event.created_by,
                event.created_at,
                event.updated_at
            )
            
            # fetch=True para obtener el ID insertado
            event_id = self.db.execute_query(query, params, fetch=True)
            
            if event_id:
                event.id = event_id
                
                if event.resource_ids:
                    self._assign_resources_to_event(event_id, event.resource_ids)
                
                self._log_event_action(event_id, "created", f"Evento '{event.title}' creado")
                return event
            
            return None
            
        except Exception as e:
            logger.error(f"Error al crear evento: {e}")
            return None

    def create_batch_events(self, events: List[Event]) -> int:
        """Crea múltiples eventos secuencialmente. Retorna la cantidad creada."""
        count = 0
        try:
            logger.info(f"Iniciando carga masiva de {len(events)} eventos")
            for event in events:
                created = self.create_event(event)
                if created:
                    count += 1
            
            logger.info(f"Carga masiva completada: {count}/{len(events)} creados")
            return count
        except Exception as e:
            logger.error(f"Error en creación por lotes: {e}")
            return count
    
    def get_event(self, event_id: int) -> Optional[Event]:
        try:
            query = "SELECT * FROM events WHERE id = %s"
            result = self.db.execute_query(query, (event_id,), fetch=True)
            
            if result:
                event_data = result[0]
                
                resources_query = "SELECT resource_id FROM event_resources WHERE event_id = %s"
                resources_result = self.db.execute_query(resources_query, (event_id,), fetch=True)
                
                resource_ids = [r['resource_id'] for r in resources_result] if resources_result else []
                
                event = Event.from_db_row(event_data)
                event.resource_ids = resource_ids
                return event
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener evento: {e}")
            return None
    
    def get_all_events(self, limit: int = 100, offset: int = 0) -> List[Event]:
        try:
            query = "SELECT * FROM events ORDER BY start_time DESC LIMIT %s OFFSET %s"
            results = self.db.execute_query(query, (limit, offset), fetch=True)
            events = []
            
            for row in results:
                event = Event.from_db_row(row)
                resources_query = "SELECT resource_id FROM event_resources WHERE event_id = %s"
                resources_result = self.db.execute_query(resources_query, (event.id,), fetch=True)
                event.resource_ids = [r['resource_id'] for r in resources_result] if resources_result else []
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error al obtener eventos: {e}")
            return []
    
    def update_event(self, event_id: int, updates: Dict[str, Any]) -> bool:
        try:
            current_event = self.get_event(event_id)
            if not current_event:
                return False
            
            set_clauses = []
            params = []
            allowed_fields = ['title', 'description', 'start_time', 'end_time', 'status']
            
            for field, value in updates.items():
                if field in allowed_fields and value is not None:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = %s")
            params.append(datetime.now())
            params.append(event_id)
            
            query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = %s"
            rows_affected = self.db.execute_query(query, tuple(params))
            
            if rows_affected > 0:
                if 'resource_ids' in updates:
                    self._update_event_resources(event_id, updates['resource_ids'])
                
                self._log_event_action(event_id, "updated", f"Datos actualizados: {list(updates.keys())}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error al actualizar evento: {e}")
            return False
    
    def cancel_event(self, event_id: int) -> bool:
        try:
            event = self.get_event(event_id)
            if not event:
                return False

            if event.status == 'cancelled':
                return True

            query = "UPDATE events SET status = 'cancelled', updated_at = NOW() WHERE id = %s"
            rows = self.db.execute_query(query, (event_id,))
            
            if rows > 0:
                self._log_event_action(event_id, "cancelled", "Cancelado por usuario")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error al cancelar evento: {e}")
            return False

    def assign_resource_to_event(self, event_id: int, resource_id: int, quantity: int = 1) -> bool:
        try:
            event = self.get_event(event_id)
            if not event:
                return False
            
            query = """
                INSERT INTO event_resources (event_id, resource_id, quantity_used)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity_used = %s
            """
            
            params = (event_id, resource_id, quantity, quantity)
            result = self.db.execute_query(query, params)
            
            if result is not None:
                if resource_id not in event.resource_ids:
                    event.resource_ids.append(resource_id)
                self._log_event_action(event_id, "resource_assigned", f"Recurso {resource_id} asignado")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error al asignar recurso: {e}")
            return False
    
    def remove_resource_from_event(self, event_id: int, resource_id: int) -> bool:
        try:
            query = "DELETE FROM event_resources WHERE event_id = %s AND resource_id = %s"
            rows_affected = self.db.execute_query(query, (event_id, resource_id))
            
            if rows_affected > 0:
                self._log_event_action(event_id, "resource_removed", f"Recurso {resource_id} removido")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error al remover recurso: {e}")
            return False
    
    def _assign_resources_to_event(self, event_id: int, resource_ids: List[int]):
        for resource_id in resource_ids:
            self.assign_resource_to_event(event_id, resource_id)
    
    def _update_event_resources(self, event_id: int, new_resource_ids: List[int]):
        current_query = "SELECT resource_id FROM event_resources WHERE event_id = %s"
        current_result = self.db.execute_query(current_query, (event_id,), fetch=True)
        current_ids = [r['resource_id'] for r in current_result] if current_result else []
        
        for resource_id in new_resource_ids:
            if resource_id not in current_ids:
                self.assign_resource_to_event(event_id, resource_id)
        
        for resource_id in current_ids:
            if resource_id not in new_resource_ids:
                self.remove_resource_from_event(event_id, resource_id)
    
    def _log_event_action(self, event_id: int, action: str, details: str):
        try:
            query = "INSERT INTO event_logs (event_id, action, details, performed_by) VALUES (%s, %s, %s, %s)"
            self.db.execute_query(query, (event_id, action, details, "system"))
        except Exception as e:
            logger.error(f"Error al registrar log: {e}")