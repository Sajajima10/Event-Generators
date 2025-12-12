"""
TimeValidator - Validador para fechas y horas en el gestor de eventos.
"""
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Dict, Any, Union, List
import re
import logging

logger = logging.getLogger(__name__)

class TimeValidator:
    """Validador para operaciones con fechas y horas."""
    
    # Formatos de fecha/hora aceptados
    DATE_FORMATS = [
        '%Y-%m-%d',          # 2024-12-07
        '%d/%m/%Y',          # 07/12/2024
        '%m/%d/%Y',          # 12/07/2024
        '%Y/%m/%d',          # 2024/12/07
        '%d-%m-%Y',          # 07-12-2024
    ]
    
    TIME_FORMATS = [
        '%H:%M',             # 14:30
        '%H:%M:%S',          # 14:30:00
        '%I:%M %p',          # 02:30 PM
        '%I:%M:%S %p',       # 02:30:00 PM
    ]
    
    DATETIME_FORMATS = [
        '%Y-%m-%d %H:%M:%S', # 2024-12-07 14:30:00
        '%Y-%m-%d %H:%M',    # 2024-12-07 14:30
        '%d/%m/%Y %H:%M',    # 07/12/2024 14:30
        '%m/%d/%Y %I:%M %p', # 12/07/2024 02:30 PM
        '%Y-%m-%dT%H:%M:%S', # 2024-12-07T14:30:00 (ISO)
    ]
    
    @staticmethod
    def parse_datetime(datetime_str: str, raise_error: bool = True) -> Optional[datetime]:
        """
        Parsea un string a datetime usando múltiples formatos.
        
        Args:
            datetime_str: String a parsear
            raise_error: Si True, lanza excepción en error
        
        Returns:
            datetime objeto o None si no se pudo parsear
        """
        if not datetime_str:
            if raise_error:
                raise ValueError("La cadena de fecha/hora está vacía")
            return None
        
        datetime_str = str(datetime_str).strip()
        
        # Intentar formatos datetime primero
        for fmt in TimeValidator.DATETIME_FORMATS:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        # Intentar combinación de fecha + hora
        for date_fmt in TimeValidator.DATE_FORMATS:
            for time_fmt in TimeValidator.TIME_FORMATS:
                try:
                    # Intentar con espacio
                    return datetime.strptime(datetime_str, f"{date_fmt} {time_fmt}")
                except ValueError:
                    try:
                        # Intentar con 'T' (ISO)
                        return datetime.strptime(datetime_str, f"{date_fmt}T{time_fmt}")
                    except ValueError:
                        continue
        
        # Intentar solo fecha
        for fmt in TimeValidator.DATE_FORMATS:
            try:
                date_part = datetime.strptime(datetime_str, fmt)
                # Asignar hora por defecto (medio día)
                return datetime.combine(date_part.date(), time(12, 0))
            except ValueError:
                continue
        
        # Intentar solo hora (asume hoy)
        for fmt in TimeValidator.TIME_FORMATS:
            try:
                time_part = datetime.strptime(datetime_str, fmt)
                today = date.today()
                return datetime.combine(today, time_part.time())
            except ValueError:
                continue
        
        # Si llega aquí, no se pudo parsear
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
        """
        Valida que un rango de tiempo sea válido.
        
        Args:
            start_time: Hora de inicio
            end_time: Hora de fin
            min_duration: Duración mínima permitida
            max_duration: Duración máxima permitida
        
        Returns:
            Tuple (es_válido, mensaje)
        """
        try:
            # Convertir strings a datetime si es necesario
            if isinstance(start_time, str):
                start_time = TimeValidator.parse_datetime(start_time)
            if isinstance(end_time, str):
                end_time = TimeValidator.parse_datetime(end_time)
            
            # Validaciones básicas
            if not start_time or not end_time:
                return False, "Las fechas no pueden estar vacías"
            
            if end_time <= start_time:
                return False, "La hora de fin debe ser posterior a la hora de inicio"
            
            # Validar duración
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
        """
        Verifica si una fecha/hora es futura (con buffer opcional).
        
        Args:
            datetime_obj: Fecha/hora a verificar
            buffer_minutes: Buffer en minutos (permite eventos que empiezan pronto)
        
        Returns:
            Tuple (es_futura, mensaje)
        """
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
        """
        Valida completamente los tiempos de un evento.
        
        Args:
            start_time: Hora de inicio del evento
            end_time: Hora de fin del evento
            allow_past: Permitir eventos en el pasado
            min_duration_minutes: Duración mínima en minutos
            max_duration_hours: Duración máxima en horas
        
        Returns:
            Dict con resultados de validación
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'start_time': None,
            'end_time': None,
            'duration_minutes': 0
        }
        
        try:
            # Parsear fechas
            start_dt = TimeValidator.parse_datetime(start_time) if isinstance(start_time, str) else start_time
            end_dt = TimeValidator.parse_datetime(end_time) if isinstance(end_time, str) else end_time
            
            result['start_time'] = start_dt
            result['end_time'] = end_dt
            
            # 1. Validar que no estén vacías
            if not start_dt or not end_dt:
                result['errors'].append("Las fechas no pueden estar vacías")
                return result
            
            # 2. Validar rango de tiempo
            min_duration = timedelta(minutes=min_duration_minutes)
            max_duration = timedelta(hours=max_duration_hours)
            
            range_valid, range_msg = TimeValidator.validate_time_range(
                start_dt, end_dt, min_duration, max_duration
            )
            
            if not range_valid:
                result['errors'].append(range_msg)
            else:
                result['duration_minutes'] = int((end_dt - start_dt).total_seconds() / 60)
            
            # 3. Validar que sean futuras (si no se permiten pasados)
            if not allow_past:
                start_future, start_msg = TimeValidator.is_future_datetime(start_dt)
                if not start_future:
                    result['errors'].append(f"Inicio: {start_msg}")
                
                end_future, end_msg = TimeValidator.is_future_datetime(end_dt)
                if not end_future:
                    result['warnings'].append(f"Fin: {end_msg} (el evento termina en el pasado)")
            
            # 4. Verificar si es muy largo
            duration = end_dt - start_dt
            if duration > timedelta(hours=8):
                result['warnings'].append("El evento es muy largo (más de 8 horas)")
            
            # 5. Verificar horas fuera de horario laboral (9:00-18:00)
            if start_dt.hour < 9 or end_dt.hour >= 18:
                result['warnings'].append("El evento está fuera del horario laboral típico (9:00-18:00)")
            
            # Determinar si es válido
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
        """
        Formatea un datetime para mostrar al usuario.
        
        Args:
            datetime_obj: datetime a formatear
            format_type: 'full', 'date', 'time', 'short'
        
        Returns:
            String formateado
        """
        formats = {
            'full': '%A, %d de %B de %Y a las %H:%M',  # Lunes, 07 de diciembre de 2024 a las 14:30
            'date': '%d/%m/%Y',                        # 07/12/2024
            'time': '%H:%M',                           # 14:30
            'short': '%d/%m %H:%M',                    # 07/12 14:30
            'iso': '%Y-%m-%dT%H:%M:%S',                # 2024-12-07T14:30:00
            'db': '%Y-%m-%d %H:%M:%S',                 # 2024-12-07 14:30:00
        }
        
        fmt = formats.get(format_type, formats['full'])
        
        # Para formato 'full' en español
        if format_type == 'full':
            # Mapear meses en español
            months_es = [
                'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
            ]
            
            # Mapear días en español
            days_es = [
                'Lunes', 'Martes', 'Miércoles', 'Jueves', 
                'Viernes', 'Sábado', 'Domingo'
            ]
            
            formatted = datetime_obj.strftime(fmt)
            
            # Reemplazar inglés por español
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
        """
        Calcula slots de tiempo disponibles entre fechas.
        
        Args:
            start_date: Fecha de inicio para buscar slots
            end_date: Fecha de fin para buscar slots
            busy_slots: Lista de slots ocupados [(start1, end1), ...]
            slot_duration: Duración de cada slot
            work_hours: Horas laborales (inicio, fin)
            break_hours: Horas de descanso [(start1, end1), ...]
        
        Returns:
            Lista de slots disponibles
        """
        available_slots = []
        
        if break_hours is None:
            break_hours = [(12, 13)]  # Descanso para almuerzo por defecto
        
        current_date = start_date
        
        while current_date <= end_date:
            # Para cada día, generar slots en horas laborales
            current_time = datetime.combine(current_date, time(work_hours[0], 0))
            end_of_day = datetime.combine(current_date, time(work_hours[1], 0))
            
            while current_time + slot_duration <= end_of_day:
                slot_end = current_time + slot_duration
                
                # Verificar si está en horas de descanso
                in_break = False
                for break_start, break_end in break_hours:
                    if (current_time.hour >= break_start and current_time.hour < break_end) or \
                       (slot_end.hour > break_start and slot_end.hour <= break_end):
                        in_break = True
                        break
                
                # Verificar si se solapa con slots ocupados
                is_busy = False
                for busy_start, busy_end in busy_slots:
                    if not (slot_end <= busy_start or current_time >= busy_end):
                        is_busy = True
                        break
                
                # Si no está en descanso ni ocupado, es disponible
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

# ===== PRUEBAS DEL VALIDADOR =====
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 PROBANDO TIME VALIDATOR")
    print("="*60)
    
    validator = TimeValidator()
    
    # 1. Probar parseo de fechas
    test_dates = [
        "2024-12-07 14:30:00",
        "07/12/2024",
        "14:30",
        "02:30 PM",
        "2024-12-07T14:30:00",
    ]
    
    print("📅 Probando parseo de fechas:")
    for date_str in test_dates:
        try:
            parsed = validator.parse_datetime(date_str, raise_error=False)
            if parsed:
                print(f"   ✅ '{date_str}' -> {parsed}")
            else:
                print(f"   ❌ '{date_str}' -> No se pudo parsear")
        except Exception as e:
            print(f"   ❌ '{date_str}' -> Error: {e}")
    
    # 2. Probar validación de rango
    print("\n⏱️ Probando validación de rango:")
    test_ranges = [
        ("2024-12-07 10:00", "2024-12-07 11:00"),  # Válido
        ("2024-12-07 11:00", "2024-12-07 10:00"),  # Inválido (fin antes)
        ("2024-12-07 10:00", "2024-12-07 10:15"),  # Inválido (muy corto)
    ]
    
    for start, end in test_ranges:
        valid, msg = validator.validate_time_range(
            start, end, 
            min_duration=timedelta(minutes=30)
        )
        status = "✅" if valid else "❌"
        print(f"   {status} {start} a {end}: {msg}")
    
    # 3. Probar validación completa de evento
    print("\n📋 Probando validación completa de evento:")
    test_event = validator.validate_event_times(
        start_time="2024-12-08 10:00",
        end_time="2024-12-08 11:30",
        allow_past=False
    )
    
    print(f"   Válido: {'✅' if test_event['valid'] else '❌'}")
    if test_event['errors']:
        print(f"   Errores: {', '.join(test_event['errors'])}")
    if test_event['warnings']:
        print(f"   Advertencias: {', '.join(test_event['warnings'])}")
    if test_event.get('success'):
        print(f"   Éxito: {test_event['success']}")
    
    # 4. Probar formato para display
    print("\n🎨 Probando formatos de display:")
    now = datetime.now()
    formats = ['full', 'date', 'time', 'short', 'iso', 'db']
    
    for fmt in formats:
        formatted = validator.format_datetime_for_display(now, fmt)
        print(f"   {fmt:10}: {formatted}")
    
    print("\n" + "="*60)
    print("🎉 ¡TIME VALIDATOR PROBADO EXITOSAMENTE!")
    print("="*60)