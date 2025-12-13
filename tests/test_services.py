import unittest
from unittest.mock import MagicMock, ANY
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.event_service import EventService
from models.event import Event

class TestEventService(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.service = EventService(db_connection=self.mock_db)

    def test_create_event_flow(self):
        """Prueba que create_event llama a INSERT y obtiene el ID."""
        
        # Configuramos el mock para devolver ID=55 cuando se inserte
        # Nota: side_effect se usa cuando hay multiples llamadas. 
        # 1ra llamada (Evento) devuelve 55. 2da llamada (Log) devuelve 1.
        self.mock_db.execute_query.side_effect = [55, 1]
        
        new_event = Event(title="Test Event", start_time=datetime.now(), end_time=datetime.now())
        
        saved_event = self.service.create_event(new_event)
        
        # Verificar que retornó el evento con el ID asignado
        self.assertIsNotNone(saved_event)
        self.assertEqual(saved_event.id, 55)
        
        # CORRECCIÓN AQUÍ:
        # Obtenemos la lista de TODAS las llamadas hechas a la base de datos
        db_calls = self.mock_db.execute_query.call_args_list
        
        # Aseguramos que hubo al menos una llamada
        self.assertTrue(len(db_calls) > 0)
        
        # Revisamos la PRIMERA llamada (índice 0), que debe ser el INSERT del evento
        first_call_args = db_calls[0].args # args es una tupla (query, params)
        query_executed = first_call_args[0]
        
        # Verificamos que sea el INSERT correcto
        self.assertIn("INSERT INTO events", query_executed)
        
        # Opcional: Verificamos que se pidió fetch=True en esa primera llamada
        first_call_kwargs = db_calls[0].kwargs
        self.assertTrue(first_call_kwargs.get('fetch'))

    def test_cancel_event(self):
        """Prueba la lógica de cancelación."""
        # Mock para get_event (debe devolver un evento existente)
        mock_event_row = {
            'id': 10, 'title': 'A', 'description': 'B', 
            'start_time': datetime.now(), 'end_time': datetime.now(), 
            'status': 'scheduled', 'created_by': 'admin', 
            'created_at': datetime.now(), 'updated_at': datetime.now()
        }
        
        # Simular respuestas: 
        # 1. SELECT del evento
        # 2. SELECT de recursos (lista vacía)
        # 3. UPDATE status
        # 4. INSERT log
        self.mock_db.execute_query.side_effect = [
            [mock_event_row], # get_event -> select events
            [],               # get_event -> select resources
            1,                # update -> rows affected
            1                 # log -> rows affected
        ]
        
        result = self.service.cancel_event(10)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()