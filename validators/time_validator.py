"""
TimeValidator - Validador para fechas y horas en el gestor de eventos.
"""
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Dict, Any, Union, List
import logging

logger = logging.getLogger(__name__)

class TimeValidator:
    """Validador para operaciones con fechas y horas."""
    
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
    ]
    
    TIME_FORMATS = [
        '%H:%M',
        '%H:%M:%S',
        '%I:%M %p',
        '%I:%M:%S %p',
    ]
    
    DATETIME_FORMATS = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M',
        '%m/%d/%Y %I:%M %p',
        '%Y-%m-%dT%H:%M:%S',
    ]
    
    @staticmethod
    def parse_datetime(datetime_str: str, raise_error: bool = True) -> Optional[datetime]:
        """Parsea un string a datetime usando múltiples formatos."""
        if not datetime_str:
            if raise_error:
                raise ValueError("La cadena de fecha/hora está vacía")
            return None
        
        datetime_str = str(datetime_str).strip()
        
        for fmt in TimeValidator.DATETIME_FORMATS:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        for date_fmt in TimeValidator.DATE_FORMATS:
            for time_fmt in TimeValidator.TIME_FORMATS:
                try:
                    return datetime.strptime(datetime_str, f"{date_fmt} {time_fmt}")
                except ValueError:
                    try:
                        return datetime.strptime(datetime_str, f"{date_fmt}T{time_fmt}")
                    except ValueError:
                        continue
        
        for fmt in TimeValidator.DATE_FORMATS:
            try:
                date_part = datetime.strptime(datetime_str, fmt)
                return datetime.combine(date_part.date(), time(12, 0))
            except ValueError:
                continue
        
        for fmt in TimeValidator.TIME_FORMATS:
            try:
                time_part = datetime.strptime(datetime_str, fmt)
                today = date.today()
                return datetime.combine(today, time_part.time())
            except ValueError:
                continue
        
        if raise_error:
            raise ValueError(f"No se pudo parsear la fecha/hora: '{datetime_str}'")
        return None
    
    @staticmethod
    def validate_time_range(
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        min_duration: Optional[timedelta] = None,
        max_duration: Optional[timedelta] = None
    ) -> Tuple[bool, str]:
        """Valida que un rango de tiempo sea válido."""
        try:
            if isinstance(start_time, str):
                start_time = TimeValidator.parse_datetime(start_time)
            if isinstance(end_time, str):
                end_time = TimeValidator.parse_datetime(end_time)
            
            if not start_time or not end_time:
                return False, "Las fechas no pueden estar vacías"
            
            if end_time <= start_time:
                return False, "La hora de fin debe ser posterior a la hora de inicio"
            
            duration = end_time - start_time
            
            if min_duration and duration < min_duration:
                min_minutes = int(min_duration.total_seconds() / 60)
                return False, f"La duración mínima es de {min_minutes} minutos"
            
            if max_duration and duration > max_duration:
                max_hours = max_duration.total_seconds() / 3600
                return False, f"La duración máxima es de {max_hours:.1f} horas"
            
            return True, "Rango de tiempo válido"
            
        except ValueError as e:
            return False, f"Error en formato de fecha: {e}"
        except Exception as e:
            return False, f"Error validando rango: {e}"
    
    @staticmethod
    def is_future_datetime(datetime_obj: Union[datetime, str], buffer_minutes: int = 15) -> Tuple[bool, str]:
        """Verifica si una fecha/hora es futura (con buffer opcional)."""
        try:
            if isinstance(datetime_obj, str):
                datetime_obj = TimeValidator.parse_datetime(datetime_obj)
            
            now = datetime.now()
            buffer_time = now + timedelta(minutes=buffer_minutes)
            
            if datetime_obj < buffer_time:
                minutes_diff = int((buffer_time - datetime_obj).total_seconds() / 60)
                if minutes_diff > 0:
                    return False, f"La fecha debe ser al menos {buffer_minutes} minutos en el futuro (faltan {minutes_diff} minutos)"
                else:
                    return False, "La fecha debe ser futura"
            
            return True, "Fecha futura válida"
            
        except Exception as e:
            return False, f"Error verificando fecha futura: {e}"
    
    @staticmethod
    def validate_event_times(
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        allow_past: bool = False,
        min_duration_minutes: int = 15,
        max_duration_hours: int = 24
    ) -> Dict[str, Any]:
        """Valida completamente los tiempos de un evento."""
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'start_time': None,
            'end_time': None,
            'duration_minutes': 0
        }
        
        try:
            start_dt = TimeValidator.parse_datetime(start_time) if isinstance(start_time, str) else start_time
            end_dt = TimeValidator.parse_datetime(end_time) if isinstance(end_time, str) else end_time
            
            result['start_time'] = start_dt
            result['end_time'] = end_dt
            
            if not start_dt or not end_dt:
                result['errors'].append("Las fechas no pueden estar vacías")
                return result
            
            min_duration = timedelta(minutes=min_duration_minutes)
            max_duration = timedelta(hours=max_duration_hours)
            
            range_valid, range_msg = TimeValidator.validate_time_range(
                start_dt, end_dt, min_duration, max_duration
            )
            
            if not range_valid:
                result['errors'].append(range_msg)
            else:
                result['duration_minutes'] = int((end_dt - start_dt).total_seconds() / 60)
            
            if not allow_past:
                start_future, start_msg = TimeValidator.is_future_datetime(start_dt)
                if not start_future:
                    result['errors'].append(f"Inicio: {start_msg}")
                
                end_future, end_msg = TimeValidator.is_future_datetime(end_dt)
                if not end_future:
                    result['warnings'].append(f"Fin: {end_msg} (el evento termina en el pasado)")
            
            duration = end_dt - start_dt
            if duration > timedelta(hours=8):
                result['warnings'].append("El evento es muy largo (más de 8 horas)")
            
            if start_dt.hour < 9 or end_dt.hour >= 18:
                result['warnings'].append("El evento está fuera del horario laboral típico (9:00-18:00)")
            
            result['valid'] = len(result['errors']) == 0
            
            if result['valid']:
                result['success'] = "Tiempos del evento válidos"
            else:
                result['success'] = None
            
            return result
            
        except Exception as e:
            result['errors'].append(f"Error inesperado: {e}")
            return result
    
    @staticmethod
    def format_datetime_for_display(datetime_obj: datetime, format_type: str = 'full') -> str:
        """Formatea un datetime para mostrar al usuario."""
        formats = {
            'full': '%A, %d de %B de %Y a las %H:%M',
            'date': '%d/%m/%Y',
            'time': '%H:%M',
            'short': '%d/%m %H:%M',
            'iso': '%Y-%m-%dT%H:%M:%S',
            'db': '%Y-%m-%d %H:%M:%S',
        }
        
        fmt = formats.get(format_type, formats['full'])
        
        if format_type == 'full':
            months_es = [
                'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
            ]
            
            days_es = [
                'Lunes', 'Martes', 'Miércoles', 'Jueves', 
                'Viernes', 'Sábado', 'Domingo'
            ]
            
            formatted = datetime_obj.strftime(fmt)
            
            for i, month in enumerate(months_es, 1):
                formatted = formatted.replace(datetime_obj.strftime(f'%B'), month)
            
            for i, day in enumerate(days_es, 1):
                formatted = formatted.replace(datetime_obj.strftime(f'%A'), day)
            
            return formatted
        
        return datetime_obj.strftime(fmt)
    
    @staticmethod
    def calculate_available_slots(
        start_date: date,
        end_date: date,
        busy_slots: List[Tuple[datetime, datetime]],
        slot_duration: timedelta = timedelta(hours=1),
        work_hours: Tuple[int, int] = (9, 18),
        break_hours: List[Tuple[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Calcula slots de tiempo disponibles entre fechas."""
        available_slots = []
        
        if break_hours is None:
            break_hours = [(12, 13)]
        
        current_date = start_date
        
        while current_date <= end_date:
            current_time = datetime.combine(current_date, time(work_hours[0], 0))
            end_of_day = datetime.combine(current_date, time(work_hours[1], 0))
            
            while current_time + slot_duration <= end_of_day:
                slot_end = current_time + slot_duration
                
                in_break = False
                for break_start, break_end in break_hours:
                    if (current_time.hour >= break_start and current_time.hour < break_end) or \
                       (slot_end.hour > break_start and slot_end.hour <= break_end):
                        in_break = True
                        break
                
                is_busy = False
                for busy_start, busy_end in busy_slots:
                    if not (slot_end <= busy_start or current_time >= busy_end):
                        is_busy = True
                        break
                
                if not in_break and not is_busy:
                    available_slots.append({
                        'start': current_time,
                        'end': slot_end,
                        'duration_minutes': int(slot_duration.total_seconds() / 60),
                        'date': current_date,
                        'formatted': f"{TimeValidator.format_datetime_for_display(current_time, 'short')} - {TimeValidator.format_datetime_for_display(slot_end, 'time')}"
                    })
                
                current_time += slot_duration
            
            current_date += timedelta(days=1)
        
        return available_slots