import unittest
from jarvis.core import route, respond, update_delivery


class CoreTests(unittest.TestCase):
    def test_route_is_conservative(self):
        self.assertEqual(route('que horas são?'), 'local')
        self.assertEqual(route('corrija o código do projeto'), 'codex')
        self.assertEqual(route('explique o universo'), 'ollama')

    def test_local_response(self):
        self.assertIn('senhor', respond('olá').lower())

    def test_delivery_requires_unique_match(self):
        rows = [{'motorista': 'Carlos', 'placa': 'ABC1D23'}, {'motorista': 'Carlos', 'placa': 'DEF4G56'}]
        with self.assertRaises(ValueError):
            update_delivery(rows, 'Carlos', {'cidade': 'Sobral'})
        self.assertNotIn('cidade', rows[0])
        update_delivery(rows, 'ABC1D23', {'cidade': 'Sobral'})
        self.assertEqual(rows[0]['cidade'], 'Sobral')


if __name__ == '__main__':
    unittest.main()
