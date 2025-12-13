import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.constraint_service import ConstraintService

class TestConstraintService(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.service = ConstraintService(db_connection=self.mock_db)

    def test_validate_requirement_missing(self):
        """Prueba: Recurso A requiere B, pero B no está presente."""
        
        # Simulamos que la DB devuelve una regla activa
        # Regla: Recurso 1 (Proyector) REQUIRES Recurso 2 (Pantalla)
        mock_rules = [
            {
                'constraint_id': 100,
                'resource_id': 1,        # Si uso el 1...
                'rule_type': 'requires', # ...necesito...
                'related_resource_id': 2,# ...el 2
                'value': None
            }
        ]
        
        self.mock_db.execute_query.return_value = mock_rules
        
        # Intentamos usar SOLO el recurso 1
        resource_ids = [1]
        violations = self.service.validate_resources(resource_ids)
        
        # Debería haber 1 violación
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]['type'], 'missing_requirement')
        self.assertIn("requiere el recurso 2", violations[0]['message'])

    def test_validate_exclusion_fail(self):
        """Prueba: Recurso A excluye B, y ambos están presentes."""
        
        # Regla: Recurso 1 EXCLUDES Recurso 3
        mock_rules = [
            {
                'constraint_id': 101,
                'resource_id': 1,
                'rule_type': 'excludes',
                'related_resource_id': 3,
                'value': None
            }
        ]
        self.mock_db.execute_query.return_value = mock_rules
        
        # Intentamos usar el 1 y el 3 juntos
        resource_ids = [1, 3]
        violations = self.service.validate_resources(resource_ids)
        
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]['type'], 'mutual_exclusion')

    def test_validate_success(self):
        """Prueba: Cumple todos los requisitos."""
        
        # Regla: 1 requiere 2
        mock_rules = [
            {
                'constraint_id': 100,
                'resource_id': 1,
                'rule_type': 'requires',
                'related_resource_id': 2,
                'value': None
            }
        ]
        self.mock_db.execute_query.return_value = mock_rules
        
        # Usamos 1 y 2. Debería pasar.
        resource_ids = [1, 2]
        violations = self.service.validate_resources(resource_ids)
        
        self.assertEqual(len(violations), 0)

if __name__ == '__main__':
    unittest.main()