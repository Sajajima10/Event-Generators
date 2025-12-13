import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database.db_connection import DatabaseConnection
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Error de importación: {e}")
    IMPORT_SUCCESS = False

if IMPORT_SUCCESS:
    logger = logging.getLogger(__name__)
    
    class ConflictChecker:
        def __init__(self, db_connection: Optional[DatabaseConnection] = None):
            self.db = db_connection or DatabaseConnection()
            logger.info("ConflictChecker inicializado")
        
        def check_resource_conflict(
            self, 
            resource_id: int, 
            start_time: datetime, 
            end_time: datetime,
            exclude_event_id: Optional[int] = None,
            needed_quantity: int = 1
        ) -> Tuple[bool, List[Dict[str, Any]]]:
            """
            Verifica si hay capacidad suficiente (Capacidad Total - Uso Actual >= Solicitado).
            Retorna: (HayConflicto, ListaDetalles)
            """
            try:
                res_query = "SELECT quantity, name FROM resources WHERE id = %s"
                res_data = self.db.execute_query(res_query, (resource_id,), fetch=True)
                
                if not res_data:
                    return True, [{'error': f'Recurso ID {resource_id} no existe'}]
                
                total_capacity = res_data[0]['quantity']
                resource_name = res_data[0]['name']

                query = """
                    SELECT 
                        e.id as event_id,
                        e.title,
                        e.start_time,
                        e.end_time,
                        er.quantity_used
                    FROM event_resources er
                    JOIN events e ON er.event_id = e.id
                    WHERE er.resource_id = %s
                    AND e.status = 'scheduled'
                    AND (e.start_time < %s AND e.end_time > %s)
                """
                
                params = [resource_id, end_time, start_time]
                
                if exclude_event_id:
                    query += " AND e.id != %s"
                    params.append(exclude_event_id)
                
                overlapping_events = self.db.execute_query(query, tuple(params), fetch=True)
                
                current_usage = 0
                conflicts = []
                
                if overlapping_events:
                    for event in overlapping_events:
                        current_usage += event['quantity_used']
                        conflicts.append({
                            'event_id': event['event_id'],
                            'event_title': event['title'],
                            'time': f"{event['start_time']} - {event['end_time']}",
                            'quantity_used': event['quantity_used']
                        })

                remaining_capacity = total_capacity - current_usage
                
                if needed_quantity > remaining_capacity:
                    logger.warning(f"Conflicto: {resource_name} (Cap: {total_capacity}, Disp: {remaining_capacity})")
                    
                    detail = {
                        'resource_id': resource_id,
                        'resource_name': resource_name,
                        'total_capacity': total_capacity,
                        'current_usage': current_usage,
                        'requested': needed_quantity,
                        'available': remaining_capacity,
                        'conflicting_events': conflicts
                    }
                    return True, [detail]
                
                return False, []
                
            except Exception as e:
                logger.error(f"Error al verificar conflicto: {e}")
                return True, [{'error': str(e)}]
        
        def check_multiple_resources_conflict(
            self,
            resource_ids: List[int],
            start_time: datetime,
            end_time: datetime,
            exclude_event_id: Optional[int] = None
        ) -> Dict[str, Any]:
            try:
                all_conflicts = []
                conflicting_resources = []
                
                for resource_id in resource_ids:
                    has_conflict, conflicts = self.check_resource_conflict(
                        resource_id, start_time, end_time, exclude_event_id, needed_quantity=1
                    )
                    
                    if has_conflict:
                        conflicting_resources.append(resource_id)
                        all_conflicts.extend(conflicts)
                
                return {
                    'has_conflict': len(conflicting_resources) > 0,
                    'conflicting_resources': conflicting_resources,
                    'conflicts': all_conflicts
                }
                
            except Exception as e:
                logger.error(f"Error al verificar múltiples recursos: {e}")
                return {'has_conflict': True, 'error': str(e)}
        
        def find_available_time_slot(
            self,
            resource_ids: List[int],
            desired_start: datetime,
            desired_end: datetime,
            duration_hours: int = 1,
            max_days_ahead: int = 30,
            exclude_event_id: Optional[int] = None
        ) -> Optional[Dict[str, Any]]:
            try:
                desired_result = self.check_multiple_resources_conflict(
                    resource_ids, desired_start, desired_end, exclude_event_id
                )
                
                if not desired_result['has_conflict']:
                    return {
                        'available': True,
                        'start_time': desired_start,
                        'end_time': desired_end,
                        'reason': 'Horario deseado disponible'
                    }
                
                current_date = desired_start.date()
                
                for day_offset in range(max_days_ahead):
                    search_date = current_date + timedelta(days=day_offset)
                    
                    for hour in range(8, 20):
                        candidate_start = datetime.combine(
                            search_date, 
                            datetime.min.time().replace(hour=hour)
                        )
                        candidate_end = candidate_start + timedelta(hours=duration_hours)
                        
                        candidate_result = self.check_multiple_resources_conflict(
                            resource_ids, candidate_start, candidate_end, exclude_event_id
                        )
                        
                        if not candidate_result['has_conflict']:
                            return {
                                'available': True,
                                'start_time': candidate_start,
                                'end_time': candidate_end,
                                'reason': f'Disponible el {search_date} a las {hour:02d}:00'
                            }
                
                return {
                    'available': False,
                    'reason': f'No hay disponibilidad en los próximos {max_days_ahead} días'
                }
                
            except Exception as e:
                logger.error(f"Error al buscar horario: {e}")
                return {'available': False, 'reason': str(e)}
        
        def get_resource_schedule(
            self,
            resource_id: int,
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, Any]:
            try:
                query = """
                    SELECT 
                        e.id, e.title, e.start_time, e.end_time, e.status, er.quantity_used
                    FROM event_resources er
                    JOIN events e ON er.event_id = e.id
                    WHERE er.resource_id = %s
                    AND e.start_time BETWEEN %s AND %s
                    AND e.status = 'scheduled'
                    ORDER BY e.start_time
                """
                
                results = self.db.execute_query(
                    query, (resource_id, start_date, end_date), fetch=True
                )
                
                events = []
                busy_slots = []
                
                for row in results:
                    events.append({
                        'event_id': row['id'],
                        'title': row['title'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time'],
                        'quantity_used': row['quantity_used']
                    })
                    
                    busy_slots.append({
                        'start': row['start_time'],
                        'end': row['end_time']
                    })
                
                return {
                    'resource_id': resource_id,
                    'events': events,
                    'busy_slots': busy_slots
                }
                
            except Exception as e:
                logger.error(f"Error al obtener calendario: {e}")
                return {'resource_id': resource_id, 'error': str(e), 'events': []}
else:
    print("No se pudo inicializar ConflictChecker")