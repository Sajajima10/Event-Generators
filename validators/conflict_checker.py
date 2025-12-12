"""
ConflictChecker - Validador para detectar conflictos de horarios entre eventos.
Verifica si recursos están disponibles en ciertos horarios.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

# ========== CONFIGURAR IMPORTS ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from database.db_connection import DatabaseConnection
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    IMPORT_SUCCESS = False

# ========== CLASE PRINCIPAL ==========
if IMPORT_SUCCESS:
    logger = logging.getLogger(__name__)
    
    class ConflictChecker:
        """Validador para detectar conflictos de horarios."""
        
        def __init__(self, db_connection: Optional[DatabaseConnection] = None):
            """
            Inicializa el ConflictChecker.
            
            Args:
                db_connection: Conexión a la base de datos (opcional)
            """
            self.db = db_connection or DatabaseConnection()
            logger.info("✅ ConflictChecker inicializado")
        
        def check_resource_conflict(
            self, 
            resource_id: int, 
            start_time: datetime, 
            end_time: datetime,
            exclude_event_id: Optional[int] = None
        ) -> Tuple[bool, List[Dict[str, Any]]]:
            """
            Verifica si un recurso tiene conflicto en un horario específico.
            
            Args:
                resource_id: ID del recurso
                start_time: Hora de inicio a verificar
                end_time: Hora de fin a verificar
                exclude_event_id: ID de evento a excluir (para updates)
            
            Returns:
                Tuple: (has_conflict, conflict_details)
            """
            try:
                logger.debug(f"Verificando conflicto para recurso {resource_id}")
                
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
                    AND e.end_time > NOW()  -- Solo eventos futuros
                    AND (
                        -- El nuevo evento empieza durante un evento existente
                        (%s BETWEEN e.start_time AND e.end_time)
                        OR
                        -- El nuevo evento termina durante un evento existente
                        (%s BETWEEN e.start_time AND e.end_time)
                        OR
                        -- El nuevo evento contiene completamente un evento existente
                        (e.start_time BETWEEN %s AND %s)
                        OR
                        -- Los eventos se solapan parcialmente
                        (e.start_time < %s AND e.end_time > %s)
                    )
                """
                
                params = [
                    resource_id,
                    start_time, end_time,  # Para BETWEEN checks
                    start_time, end_time,  # Para evento contiene existente
                    end_time, start_time   # Para solapamiento parcial
                ]
                
                if exclude_event_id:
                    query += " AND e.id != %s"
                    params.append(exclude_event_id)
                
                query += " ORDER BY e.start_time"
                
                results = self.db.execute_query(query, tuple(params), fetch=True)
                
                if results:
                    conflicts = []
                    for row in results:
                        conflict = {
                            'event_id': row['event_id'],
                            'event_title': row['title'],
                            'existing_start': row['start_time'],
                            'existing_end': row['end_time'],
                            'quantity_used': row['quantity_used'],
                            'conflict_type': self._determine_conflict_type(
                                start_time, end_time, 
                                row['start_time'], row['end_time']
                            )
                        }
                        conflicts.append(conflict)
                    
                    logger.warning(f"⚠️ Encontrados {len(conflicts)} conflictos para recurso {resource_id}")
                    return True, conflicts
                
                logger.debug(f"✅ Recurso {resource_id} disponible en {start_time} - {end_time}")
                return False, []
                
            except Exception as e:
                logger.error(f"❌ Error al verificar conflicto: {e}")
                return True, [{'error': str(e)}]
        
        def check_multiple_resources_conflict(
            self,
            resource_ids: List[int],
            start_time: datetime,
            end_time: datetime,
            exclude_event_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Verifica conflictos para múltiples recursos simultáneamente.
            
            Args:
                resource_ids: Lista de IDs de recursos
                start_time: Hora de inicio
                end_time: Hora de fin
                exclude_event_id: ID de evento a excluir
            
            Returns:
                Dict con resultados de conflicto
            """
            try:
                logger.debug(f"Verificando {len(resource_ids)} recursos")
                
                all_conflicts = []
                conflicting_resources = []
                
                for resource_id in resource_ids:
                    has_conflict, conflicts = self.check_resource_conflict(
                        resource_id, start_time, end_time, exclude_event_id
                    )
                    
                    if has_conflict:
                        conflicting_resources.append(resource_id)
                        all_conflicts.extend(conflicts)
                
                result = {
                    'has_conflict': len(conflicting_resources) > 0,
                    'conflicting_resources': conflicting_resources,
                    'conflicts': all_conflicts,
                    'total_resources_checked': len(resource_ids),
                    'conflicting_count': len(conflicting_resources)
                }
                
                if result['has_conflict']:
                    logger.warning(f"⚠️ Conflictos en {len(conflicting_resources)} de {len(resource_ids)} recursos")
                else:
                    logger.debug(f"✅ Todos los {len(resource_ids)} recursos disponibles")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Error al verificar múltiples recursos: {e}")
                return {
                    'has_conflict': True,
                    'error': str(e),
                    'conflicting_resources': [],
                    'conflicts': []
                }
        
        def find_available_time_slot(
            self,
            resource_ids: List[int],
            desired_start: datetime,
            desired_end: datetime,
            duration_hours: int = 1,
            max_days_ahead: int = 30,
            exclude_event_id: Optional[int] = None
        ) -> Optional[Dict[str, Any]]:
            """
            Encuentra el próximo horario disponible para un conjunto de recursos.
            
            Args:
                resource_ids: Lista de IDs de recursos
                desired_start: Hora de inicio deseada
                desired_end: Hora de fin deseada
                duration_hours: Duración en horas
                max_days_ahead: Máximo número de días a buscar
                exclude_event_id: ID de evento a excluir
            
            Returns:
                Dict con horario disponible o None
            """
            try:
                logger.info(f"Buscando horario para {len(resource_ids)} recursos")
                
                # Si el horario deseado está disponible, usarlo
                desired_result = self.check_multiple_resources_conflict(
                    resource_ids, desired_start, desired_end, exclude_event_id
                )
                
                if not desired_result['has_conflict']:
                    logger.info(f"✅ Horario deseado disponible: {desired_start} - {desired_end}")
                    return {
                        'available': True,
                        'start_time': desired_start,
                        'end_time': desired_end,
                        'reason': 'Horario deseado disponible'
                    }
                
                # Buscar en el mismo día, desplazando por horas
                current_date = desired_start.date()
                search_start = datetime.combine(current_date, desired_start.time())
                
                for day_offset in range(max_days_ahead):
                    search_date = current_date + timedelta(days=day_offset)
                    
                    # Intentar diferentes horas del día (8 AM a 8 PM)
                    for hour in range(8, 20):
                        candidate_start = datetime.combine(
                            search_date, 
                            datetime.min.time().replace(hour=hour)
                        )
                        candidate_end = candidate_start + timedelta(hours=duration_hours)
                        
                        # Verificar disponibilidad
                        candidate_result = self.check_multiple_resources_conflict(
                            resource_ids, candidate_start, candidate_end, exclude_event_id
                        )
                        
                        if not candidate_result['has_conflict']:
                            logger.info(f"✅ Horario encontrado: {candidate_start} - {candidate_end}")
                            return {
                                'available': True,
                                'start_time': candidate_start,
                                'end_time': candidate_end,
                                'reason': f'Disponible el {search_date} a las {hour:02d}:00',
                                'days_offset': day_offset,
                                'hour': hour
                            }
                
                logger.warning(f"⚠️ No se encontró horario en {max_days_ahead} días")
                return {
                    'available': False,
                    'reason': f'No hay disponibilidad en los próximos {max_days_ahead} días',
                    'max_days_checked': max_days_ahead
                }
                
            except Exception as e:
                logger.error(f"❌ Error al buscar horario: {e}")
                return {
                    'available': False,
                    'reason': f'Error: {str(e)}'
                }
        
        def get_resource_schedule(
            self,
            resource_id: int,
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, Any]:
            """
            Obtiene el calendario/horario de un recurso.
            
            Args:
                resource_id: ID del recurso
                start_date: Fecha de inicio
                end_date: Fecha de fin
            
            Returns:
                Dict con eventos programados y horarios ocupados
            """
            try:
                logger.debug(f"Obteniendo calendario para recurso {resource_id}")
                
                query = """
                    SELECT 
                        e.id,
                        e.title,
                        e.description,
                        e.start_time,
                        e.end_time,
                        e.status,
                        er.quantity_used
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
                    event = {
                        'event_id': row['id'],
                        'title': row['title'],
                        'description': row['description'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time'],
                        'status': row['status'],
                        'quantity_used': row['quantity_used']
                    }
                    events.append(event)
                    
                    # Agregar slot ocupado
                    busy_slots.append({
                        'start': row['start_time'],
                        'end': row['end_time'],
                        'event_id': row['id']
                    })
                
                # Calcular disponibilidad por día
                availability_by_day = self._calculate_daily_availability(
                    busy_slots, start_date, end_date
                )
                
                result = {
                    'resource_id': resource_id,
                    'period_start': start_date,
                    'period_end': end_date,
                    'total_events': len(events),
                    'events': events,
                    'busy_slots': busy_slots,
                    'availability_by_day': availability_by_day,
                    'busy_hours': self._calculate_busy_hours(busy_slots),
                    'free_hours': self._calculate_free_hours(busy_slots, start_date, end_date)
                }
                
                logger.info(f"✅ Calendario obtenido: {len(events)} eventos")
                return result
                
            except Exception as e:
                logger.error(f"❌ Error al obtener calendario: {e}")
                return {
                    'resource_id': resource_id,
                    'error': str(e),
                    'events': [],
                    'busy_slots': []
                }
        
        def _determine_conflict_type(
            self,
            new_start: datetime,
            new_end: datetime,
            existing_start: datetime,
            existing_end: datetime
        ) -> str:
            """
            Determina el tipo de conflicto entre dos intervalos.
            
            Returns:
                Tipo de conflicto: 'overlap', 'contained', 'contains', 'adjacent'
            """
            if new_start < existing_start and new_end > existing_end:
                return 'contains'  # Nuevo evento contiene al existente
            elif new_start > existing_start and new_end < existing_end:
                return 'contained'  # Nuevo evento está contenido en existente
            elif new_start <= existing_end and new_end >= existing_start:
                return 'overlap'    # Solapamiento parcial
            elif new_end == existing_start or new_start == existing_end:
                return 'adjacent'   # Eventos adyacentes
            else:
                return 'unknown'
        
        def _calculate_daily_availability(
            self,
            busy_slots: List[Dict],
            start_date: datetime,
            end_date: datetime
        ) -> Dict[str, Any]:
            """Calcula disponibilidad por día."""
            availability = {}
            current_date = start_date.date()
            end_date_date = end_date.date()
            
            while current_date <= end_date_date:
                day_slots = [
                    slot for slot in busy_slots 
                    if slot['start'].date() == current_date
                ]
                
                busy_hours = sum(
                    (slot['end'] - slot['start']).total_seconds() / 3600
                    for slot in day_slots
                )
                
                availability[str(current_date)] = {
                    'busy_hours': busy_hours,
                    'free_hours': 24 - busy_hours,
                    'event_count': len(day_slots),
                    'is_weekend': current_date.weekday() >= 5
                }
                
                current_date += timedelta(days=1)
            
            return availability
        
        def _calculate_busy_hours(self, busy_slots: List[Dict]) -> float:
            """Calcula total de horas ocupadas."""
            total_hours = 0
            for slot in busy_slots:
                duration = slot['end'] - slot['start']
                total_hours += duration.total_seconds() / 3600
            return total_hours
        
        def _calculate_free_hours(
            self,
            busy_slots: List[Dict],
            start_date: datetime,
            end_date: datetime
        ) -> float:
            """Calcula total de horas libres en el período."""
            total_duration = (end_date - start_date).total_seconds() / 3600
            busy_hours = self._calculate_busy_hours(busy_slots)
            return max(0, total_duration - busy_hours)

    # ===== PRUEBAS DEL CONFLICT CHECKER =====
    if __name__ == "__main__":
        print("\n" + "="*60)
        print("🧪 PROBANDO CONFLICT CHECKER")
        print("="*60)
        
        try:
            from datetime import datetime, timedelta
            
            # Crear checker
            checker = ConflictChecker()
            print("✅ ConflictChecker creado")
            
            # Fechas de prueba
            now = datetime.now()
            future_start = now + timedelta(hours=1)
            future_end = now + timedelta(hours=2)
            
            # 1. Verificar conflicto para un recurso (simulado)
            print(f"\n1️⃣ Verificando conflicto para recurso 1...")
            has_conflict, conflicts = checker.check_resource_conflict(1, future_start, future_end)
            print(f"   Conflicto: {'Sí' if has_conflict else 'No'}")
            if has_conflict:
                print(f"   Conflictos encontrados: {len(conflicts)}")
            
            # 2. Verificar múltiples recursos
            print(f"\n2️⃣ Verificando 3 recursos...")
            resources = [1, 2, 3]
            multi_result = checker.check_multiple_resources_conflict(
                resources, future_start, future_end
            )
            print(f"   Total recursos: {multi_result['total_resources_checked']}")
            print(f"   Con conflicto: {multi_result['conflicting_count']}")
            
            # 3. Buscar horario disponible
            print(f"\n3️⃣ Buscando horario disponible...")
            slot_result = checker.find_available_time_slot(
                resource_ids=resources,
                desired_start=future_start,
                desired_end=future_end,
                duration_hours=1,
                max_days_ahead=7
            )
            print(f"   Disponible: {slot_result['available']}")
            if slot_result['available']:
                print(f"   Horario: {slot_result['start_time']} - {slot_result['end_time']}")
            
            # 4. Obtener calendario de recurso
            print(f"\n4️⃣ Obteniendo calendario...")
            start_date = now.replace(hour=0, minute=0, second=0)
            end_date = start_date + timedelta(days=7)
            schedule = checker.get_resource_schedule(1, start_date, end_date)
            print(f"   Período: {start_date.date()} a {end_date.date()}")
            print(f"   Eventos: {schedule.get('total_events', 0)}")
            print(f"   Horas ocupadas: {schedule.get('busy_hours', 0):.1f}h")
            
            print("\n" + "="*60)
            print("🎉 ¡CONFLICT CHECKER PROBADO EXITOSAMENTE!")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error en pruebas: {e}")
            import traceback
            traceback.print_exc()
else:
    print("❌ No se pudo inicializar ConflictChecker")