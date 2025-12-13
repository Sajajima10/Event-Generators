from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from models.event import Event
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class EventService:
    """Servicio para operaciones CRUD con eventos."""
    
    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        self.db = db_connection or DatabaseConnection()
        logger.info("EventService inicializado")
    
    def create_event(self, event: Event) -> Optional[Event]:
        """Crea un nuevo evento en la base de datos."""
        try:
            logger.info(f"Creando nuevo evento: {event.title}")
            
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
            
            event_id = self.db.execute_query(query, params)
            
            if event_id:
                event.id = event_id
                logger.info(f"✅ Evento creado con ID: {event_id}")
                
                if event.resource_ids:
                    self._assign_resources_to_event(event_id, event.resource_ids)
                
                self._log_event_action(event_id, "created", f"Evento '{event.title}' creado")
                return event
            
            logger.error("❌ No se pudo crear el evento")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al crear evento: {e}")
            return None
    
    def get_event(self, event_id: int) -> Optional[Event]:
        """Obtiene un evento por su ID."""
        try:
            logger.debug(f"Buscando evento ID: {event_id}")
            
            query = "SELECT * FROM events WHERE id = %s"
            result = self.db.execute_query(query, (event_id,), fetch=True)
            
            if result:
                event_data = result[0]
                
                resources_query = """
                    SELECT resource_id FROM event_resources 
                    WHERE event_id = %s
                """
                resources_result = self.db.execute_query(
                    resources_query, (event_id,), fetch=True
                )
                
                resource_ids = [r['resource_id'] for r in resources_result] if resources_result else []
                
                event = Event.from_db_row(event_data)
                event.resource_ids = resource_ids
                
                logger.debug(f"✅ Evento encontrado: {event.title}")
                return event
            
            logger.warning(f"⚠️ Evento ID {event_id} no encontrado")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al obtener evento: {e}")
            return None
    
    def get_all_events(self, limit: int = 100, offset: int = 0) -> List[Event]:
        """Obtiene todos los eventos con paginación."""
        try:
            logger.debug(f"Obteniendo todos los eventos (limit: {limit}, offset: {offset})")
            
            query = """
                SELECT * FROM events 
                ORDER BY start_time DESC 
                LIMIT %s OFFSET %s
            """
            
            results = self.db.execute_query(query, (limit, offset), fetch=True)
            events = []
            
            for row in results:
                event = Event.from_db_row(row)
                
                resources_query = """
                    SELECT resource_id FROM event_resources 
                    WHERE event_id = %s
                """
                resources_result = self.db.execute_query(
                    resources_query, (event.id,), fetch=True
                )
                
                event.resource_ids = [r['resource_id'] for r in resources_result] if resources_result else []
                events.append(event)
            
            logger.info(f"✅ Encontrados {len(events)} eventos")
            return events
            
        except Exception as e:
            logger.error(f"❌ Error al obtener eventos: {e}")
            return []
    
    def update_event(self, event_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza un evento existente."""
        try:
            logger.info(f"Actualizando evento ID: {event_id}")
            
            current_event = self.get_event(event_id)
            if not current_event:
                logger.error(f"❌ Evento ID {event_id} no encontrado para actualizar")
                return False
            
            set_clauses = []
            params = []
            allowed_fields = ['title', 'description', 'start_time', 'end_time', 'status']
            
            for field, value in updates.items():
                if field in allowed_fields and value is not None:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                logger.warning("⚠️ No hay campos válidos para actualizar")
                return False
            
            set_clauses.append("updated_at = %s")
            params.append(datetime.now())
            params.append(event_id)
            
            query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = %s"
            rows_affected = self.db.execute_query(query, tuple(params))
            
            if rows_affected > 0:
                if 'resource_ids' in updates:
                    self._update_event_resources(event_id, updates['resource_ids'])
                
                self._log_event_action(event_id, "updated", f"Evento actualizado: {updates}")
                logger.info(f"✅ Evento ID {event_id} actualizado correctamente")
                return True
            
            logger.warning(f"⚠️ No se pudo actualizar evento ID {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al actualizar evento: {e}")
            return False
    
    def delete_event(self, event_id: int) -> bool:
        """Elimina un evento por su ID."""
        try:
            logger.info(f"Eliminando evento ID: {event_id}")
            
            event = self.get_event(event_id)
            if not event:
                logger.warning(f"⚠️ Evento ID {event_id} no encontrado")
                return False
            
            query = "DELETE FROM events WHERE id = %s"
            rows_affected = self.db.execute_query(query, (event_id,))
            
            if rows_affected > 0:
                self._log_event_action(event_id, "deleted", f"Evento '{event.title}' eliminado")
                logger.info(f"✅ Evento ID {event_id} eliminado correctamente")
                return True
            
            logger.warning(f"⚠️ No se pudo eliminar evento ID {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al eliminar evento: {e}")
            return False
    
    def assign_resource_to_event(self, event_id: int, resource_id: int, quantity: int = 1) -> bool:
        """Asigna un recurso a un evento."""
        try:
            logger.info(f"Asignando recurso {resource_id} a evento {event_id}")
            
            event = self.get_event(event_id)
            if not event:
                logger.error(f"❌ Evento ID {event_id} no encontrado")
                return False
            
            query = """
                INSERT INTO event_resources (event_id, resource_id, quantity_used)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity_used = %s
            """
            
            params = (event_id, resource_id, quantity, quantity)
            result = self.db.execute_query(query, params)
            
            if result:
                if resource_id not in event.resource_ids:
                    event.resource_ids.append(resource_id)
                
                self._log_event_action(
                    event_id, 
                    "resource_assigned", 
                    f"Recurso {resource_id} asignado al evento"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al asignar recurso: {e}")
            return False
    
    def remove_resource_from_event(self, event_id: int, resource_id: int) -> bool:
        """Remueve un recurso de un evento."""
        try:
            logger.info(f"Removiendo recurso {resource_id} de evento {event_id}")
            
            query = "DELETE FROM event_resources WHERE event_id = %s AND resource_id = %s"
            rows_affected = self.db.execute_query(query, (event_id, resource_id))
            
            if rows_affected > 0:
                self._log_event_action(
                    event_id,
                    "resource_removed",
                    f"Recurso {resource_id} removido del evento"
                )
                return True
            
            logger.warning(f"⚠️ Recurso {resource_id} no estaba asignado a evento {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al remover recurso: {e}")
            return False
    
    def get_events_in_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """Obtiene eventos en un rango de fechas."""
        try:
            logger.debug(f"Buscando eventos entre {start_date} y {end_date}")
            
            query = """
                SELECT * FROM events 
                WHERE start_time BETWEEN %s AND %s 
                OR end_time BETWEEN %s AND %s
                ORDER BY start_time
            """
            
            params = (start_date, end_date, start_date, end_date)
            results = self.db.execute_query(query, params, fetch=True)
            
            events = [Event.from_db_row(row) for row in results]
            logger.info(f"✅ Encontrados {len(events)} eventos en el rango")
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error al buscar eventos en rango: {e}")
            return []
    
    def check_resource_conflict(self, resource_id: int, start_time: datetime, end_time: datetime, 
                               exclude_event_id: Optional[int] = None) -> bool:
        """Verifica si un recurso tiene conflicto en un horario."""
        try:
            logger.debug(f"Verificando conflicto para recurso {resource_id} en {start_time} - {end_time}")
            
            query = """
                SELECT COUNT(*) as conflict_count
                FROM event_resources er
                JOIN events e ON er.event_id = e.id
                WHERE er.resource_id = %s
                AND e.status = 'scheduled'
                AND (
                    (e.start_time < %s AND e.end_time > %s) OR
                    (e.start_time BETWEEN %s AND %s) OR
                    (e.end_time BETWEEN %s AND %s)
                )
            """
            
            params = [resource_id, end_time, start_time, 
                     start_time, end_time, start_time, end_time]
            
            if exclude_event_id:
                query += " AND e.id != %s"
                params.append(exclude_event_id)
            
            result = self.db.execute_query(query, tuple(params), fetch=True)
            has_conflict = result[0]['conflict_count'] > 0 if result else False
            
            if has_conflict:
                logger.warning(f"⚠️ Conflicto encontrado para recurso {resource_id}")
            else:
                logger.debug(f"✅ Recurso {resource_id} disponible en ese horario")
            
            return has_conflict
            
        except Exception as e:
            logger.error(f"❌ Error al verificar conflicto: {e}")
            return True
    
    def _assign_resources_to_event(self, event_id: int, resource_ids: List[int]):
        """Asigna múltiples recursos a un evento."""
        for resource_id in resource_ids:
            self.assign_resource_to_event(event_id, resource_id)
    
    def _update_event_resources(self, event_id: int, new_resource_ids: List[int]):
        """Actualiza la lista completa de recursos de un evento."""
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
        """Registra una acción en el log de eventos."""
        try:
            query = """
                INSERT INTO event_logs (event_id, action, details, performed_by)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_query(query, (event_id, action, details, "system"))
        except Exception as e:
            logger.error(f"❌ Error al registrar log: {e}")