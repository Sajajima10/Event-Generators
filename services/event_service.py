"""
EventService - Servicio CRUD para manejar eventos en el gestor de eventos.
Conecta los modelos con la base de datos.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from models.event import Event
from database.db_connection import DatabaseConnection

logger = logging.getLogger(__name__)

class EventService:
    """Servicio para operaciones CRUD con eventos."""
    
    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        """
        Inicializa el servicio de eventos.
        
        Args:
            db_connection: Conexión a la base de datos (opcional, crea una nueva si no se proporciona)
        """
        self.db = db_connection or DatabaseConnection()
        logger.info("EventService inicializado")
    
    def create_event(self, event: Event) -> Optional[Event]:
        """
        Crea un nuevo evento en la base de datos.
        
        Args:
            event: Objeto Event a crear
        
        Returns:
            Event creado con ID asignado, o None si hay error
        """
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
            
            # Ejecutar inserción
            event_id = self.db.execute_query(query, params)
            
            if event_id:
                # Asignar el ID al evento
                event.id = event_id
                logger.info(f"✅ Evento creado con ID: {event_id}")
                
                # Asignar recursos si hay
                if event.resource_ids:
                    self._assign_resources_to_event(event_id, event.resource_ids)
                
                # Registrar en logs
                self._log_event_action(event_id, "created", f"Evento '{event.title}' creado")
                
                return event
            
            logger.error("❌ No se pudo crear el evento")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al crear evento: {e}")
            return None
    
    def get_event(self, event_id: int) -> Optional[Event]:
        """
        Obtiene un evento por su ID.
        
        Args:
            event_id: ID del evento a buscar
        
        Returns:
            Event encontrado o None si no existe
        """
        try:
            logger.debug(f"Buscando evento ID: {event_id}")
            
            query = "SELECT * FROM events WHERE id = %s"
            result = self.db.execute_query(query, (event_id,), fetch=True)
            
            if result:
                event_data = result[0]
                
                # Obtener recursos asignados a este evento
                resources_query = """
                    SELECT resource_id FROM event_resources 
                    WHERE event_id = %s
                """
                resources_result = self.db.execute_query(
                    resources_query, (event_id,), fetch=True
                )
                
                resource_ids = [r['resource_id'] for r in resources_result] if resources_result else []
                
                # Crear objeto Event
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
        """
        Obtiene todos los eventos con paginación.
        
        Args:
            limit: Máximo número de eventos a retornar
            offset: Desplazamiento para paginación
        
        Returns:
            Lista de objetos Event
        """
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
                
                # Obtener recursos para cada evento
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
        """
        Actualiza un evento existente.
        
        Args:
            event_id: ID del evento a actualizar
            updates: Diccionario con campos a actualizar
        
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Actualizando evento ID: {event_id}")
            
            # Verificar que el evento existe
            current_event = self.get_event(event_id)
            if not current_event:
                logger.error(f"❌ Evento ID {event_id} no encontrado para actualizar")
                return False
            
            # Construir query dinámica
            set_clauses = []
            params = []
            
            # Campos permitidos para actualizar
            allowed_fields = ['title', 'description', 'start_time', 'end_time', 'status']
            
            for field, value in updates.items():
                if field in allowed_fields and value is not None:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                logger.warning("⚠️ No hay campos válidos para actualizar")
                return False
            
            # Añadir updated_at
            set_clauses.append("updated_at = %s")
            params.append(datetime.now())
            
            # Añadir event_id al final para WHERE
            params.append(event_id)
            
            query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = %s"
            
            # Ejecutar actualización
            rows_affected = self.db.execute_query(query, tuple(params))
            
            if rows_affected > 0:
                # Actualizar recursos si se proporcionan
                if 'resource_ids' in updates:
                    self._update_event_resources(event_id, updates['resource_ids'])
                
                # Registrar en logs
                self._log_event_action(event_id, "updated", f"Evento actualizado: {updates}")
                
                logger.info(f"✅ Evento ID {event_id} actualizado correctamente")
                return True
            
            logger.warning(f"⚠️ No se pudo actualizar evento ID {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al actualizar evento: {e}")
            return False
    
    def delete_event(self, event_id: int) -> bool:
        """
        Elimina un evento por su ID.
        
        Args:
            event_id: ID del evento a eliminar
        
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Eliminando evento ID: {event_id}")
            
            # Primero obtener información para el log
            event = self.get_event(event_id)
            if not event:
                logger.warning(f"⚠️ Evento ID {event_id} no encontrado")
                return False
            
            # Eliminar el evento (las FK con CASCADE eliminarán las asignaciones)
            query = "DELETE FROM events WHERE id = %s"
            rows_affected = self.db.execute_query(query, (event_id,))
            
            if rows_affected > 0:
                # Registrar en logs
                self._log_event_action(event_id, "deleted", f"Evento '{event.title}' eliminado")
                
                logger.info(f"✅ Evento ID {event_id} eliminado correctamente")
                return True
            
            logger.warning(f"⚠️ No se pudo eliminar evento ID {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al eliminar evento: {e}")
            return False
    
    def assign_resource_to_event(self, event_id: int, resource_id: int, quantity: int = 1) -> bool:
        """
        Asigna un recurso a un evento.
        
        Args:
            event_id: ID del evento
            resource_id: ID del recurso
            quantity: Cantidad a asignar
        
        Returns:
            True si se asignó correctamente
        """
        try:
            logger.info(f"Asignando recurso {resource_id} a evento {event_id}")
            
            # Verificar que ambos existen
            event = self.get_event(event_id)
            if not event:
                logger.error(f"❌ Evento ID {event_id} no encontrado")
                return False
            
            # Aquí deberíamos verificar que el recurso existe
            # (necesitaríamos ResourceService)
            
            query = """
                INSERT INTO event_resources (event_id, resource_id, quantity_used)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity_used = %s
            """
            
            params = (event_id, resource_id, quantity, quantity)
            result = self.db.execute_query(query, params)
            
            if result:
                # Actualizar lista de recursos en el objeto evento
                if resource_id not in event.resource_ids:
                    event.resource_ids.append(resource_id)
                
                # Registrar en logs
                self._log_event_action(
                    event_id, 
                    "resource_assigned", 
                    f"Recurso {resource_id} asignado al evento"
                )
                
                logger.info(f"✅ Recurso {resource_id} asignado a evento {event_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al asignar recurso: {e}")
            return False
    
    def remove_resource_from_event(self, event_id: int, resource_id: int) -> bool:
        """
        Remueve un recurso de un evento.
        
        Args:
            event_id: ID del evento
            resource_id: ID del recurso
        
        Returns:
            True si se removió correctamente
        """
        try:
            logger.info(f"Removiendo recurso {resource_id} de evento {event_id}")
            
            query = "DELETE FROM event_resources WHERE event_id = %s AND resource_id = %s"
            rows_affected = self.db.execute_query(query, (event_id, resource_id))
            
            if rows_affected > 0:
                # Registrar en logs
                self._log_event_action(
                    event_id,
                    "resource_removed",
                    f"Recurso {resource_id} removido del evento"
                )
                
                logger.info(f"✅ Recurso {resource_id} removido de evento {event_id}")
                return True
            
            logger.warning(f"⚠️ Recurso {resource_id} no estaba asignado a evento {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al remover recurso: {e}")
            return False
    
    def get_events_in_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Obtiene eventos en un rango de fechas.
        
        Args:
            start_date: Fecha de inicio del rango
            end_date: Fecha de fin del rango
        
        Returns:
            Lista de eventos en el rango
        """
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
        """
        Verifica si un recurso tiene conflicto en un horario.
        
        Args:
            resource_id: ID del recurso
            start_time: Hora de inicio a verificar
            end_time: Hora de fin a verificar
            exclude_event_id: ID de evento a excluir (para updates)
        
        Returns:
            True si hay conflicto, False si está disponible
        """
        try:
            logger.debug(f"Verificando conflicto para recurso {resource_id} en {start_time} - {end_time}")
            
            query = """
                SELECT COUNT(*) as conflict_count
                FROM event_resources er
                JOIN events e ON er.event_id = e.id
                WHERE er.resource_id = %s
                AND e.status = 'scheduled'
                AND (
                    (e.start_time < %s AND e.end_time > %s) OR  -- Evento contiene el periodo
                    (e.start_time BETWEEN %s AND %s) OR          -- Evento empieza en el periodo
                    (e.end_time BETWEEN %s AND %s)               -- Evento termina en el periodo
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
            return True  # Asumir conflicto en caso de error
    
    # ===== MÉTODOS PRIVADOS =====
    
    def _assign_resources_to_event(self, event_id: int, resource_ids: List[int]):
        """Asigna múltiples recursos a un evento."""
        for resource_id in resource_ids:
            self.assign_resource_to_event(event_id, resource_id)
    
    def _update_event_resources(self, event_id: int, new_resource_ids: List[int]):
        """Actualiza la lista completa de recursos de un evento."""
        # Obtener recursos actuales
        current_query = "SELECT resource_id FROM event_resources WHERE event_id = %s"
        current_result = self.db.execute_query(current_query, (event_id,), fetch=True)
        current_ids = [r['resource_id'] for r in current_result] if current_result else []
        
        # Agregar nuevos
        for resource_id in new_resource_ids:
            if resource_id not in current_ids:
                self.assign_resource_to_event(event_id, resource_id)
        
        # Remover los que ya no están
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

# ===== PRUEBAS DEL SERVICIO =====
if __name__ == "__main__":
    print("🧪 PROBANDO EVENT SERVICE")
    print("=" * 60)
    
    try:
        from datetime import datetime, timedelta
        
        # Crear servicio
        service = EventService()
        print("✅ EventService creado")
        
        # Crear evento de prueba
        test_event = Event(
            title="Prueba EventService",
            description="Evento de prueba para el servicio",
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2),
            status="scheduled",
            created_by="tester",
            resource_ids=[1, 2]  # IDs de recursos de prueba
        )
        
        # 1. Crear evento
        created_event = service.create_event(test_event)
        if created_event:
            print(f"✅ Evento creado con ID: {created_event.id}")
            
            # 2. Obtener evento por ID
            retrieved_event = service.get_event(created_event.id)
            if retrieved_event:
                print(f"✅ Evento recuperado: {retrieved_event.title}")
            
            # 3. Obtener todos los eventos
            all_events = service.get_all_events(limit=5)
            print(f"✅ Total eventos: {len(all_events)}")
            
            # 4. Actualizar evento
            updates = {
                'title': 'Evento Actualizado',
                'description': 'Descripción actualizada'
            }
            if service.update_event(created_event.id, updates):
                print("✅ Evento actualizado")
            
            # 5. Verificar conflicto
            conflict = service.check_resource_conflict(
                resource_id=1,
                start_time=test_event.start_time,
                end_time=test_event.end_time
            )
            print(f"✅ Conflicto verificado: {'Sí' if conflict else 'No'}")
            
            # 6. Eliminar evento (comentado para no borrar datos reales)
            # if service.delete_event(created_event.id):
            #     print("✅ Evento eliminado")
            
        else:
            print("❌ No se pudo crear el evento")
        
        print("\n🎉 ¡Pruebas de EventService completadas!")
        
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        import traceback
        traceback.print_exc()