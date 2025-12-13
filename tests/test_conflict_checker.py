import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validators.conflict_checker import ConflictChecker

class TestConflictChecker(unittest.TestCase):

    def setUp(self):
        # Creamos un Mock de la conexión a BD
        self.mock_db = MagicMock()
        # Inyectamos el mock al validador
        self.checker = ConflictChecker(db_connection=self.mock_db)

    def test_capacity_check_success(self):
        """Prueba: Hay capacidad suficiente (Total 10, Usado 5, Pido 2)."""
        
        # 1. Simular respuesta de Capacidad del Recurso
        # execute_query retorna una lista de dicts
        capacity_response = [{'quantity': 10, 'name': 'Sala A'}]
        
        # 2. Simular respuesta de Eventos superpuestos
        # Digamos que hay un evento usando 5 unidades
        events_response = [{'event_id': 1, 'title': 'Otro', 'start_time': None, 'end_time': None, 'quantity_used': 5}]
        
        # Configuramos el mock para devolver estas respuestas en orden
        self.mock_db.execute_query.side_effect = [capacity_response, events_response]
        
        start = datetime.now()
        end = start + timedelta(hours=1)
        
        # Ejecutar prueba pidiendo 2 unidades
        conflict, details = self.checker.check_resource_conflict(
            resource_id=1, start_time=start, end_time=end, needed_quantity=2
        )
        
        # No debería haber conflicto (5 usado + 2 pedido < 10 total)
        self.assertFalse(conflict)
        self.assertEqual(len(details), 0)

    def test_capacity_check_fail(self):
        """Prueba: No hay capacidad (Total 1, Usado 1, Pido 1)."""
        
        # Capacidad 1 (ej. una sala única)
        self.mock_db.execute_query.side_effect = [
            [{'quantity': 1, 'name': 'Sala VIP'}],       # Query 1: Info Recurso
            [{'event_id': 99, 'title': 'Ocupado', 'start_time': None, 'end_time': None, 'quantity_used': 1}] # Query 2: Eventos superpuestos
        ]
        
        conflict, details = self.checker.check_resource_conflict(
            resource_id=1, 
            start_time=datetime.now(), 
            end_time=datetime.now() + timedelta(hours=1), 
            needed_quantity=1
        )
        
        # Debería haber conflicto
        self.assertTrue(conflict)
        self.assertIn("Sala VIP", details[0]['resource_name'])
        self.assertEqual(details[0]['available'], 0)

if __name__ == '__main__':
    unittest.main()