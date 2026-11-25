import unittest
from unittest.mock import patch


class DiagnosticTests(unittest.TestCase):
    def test_offline_service_is_reported_without_fabricated_gpu(self):
        from jarvis.diagnostics import collect
        with patch('jarvis.diagnostics.urlopen', side_effect=OSError('offline')):
            data = collect()
        self.assertEqual(data['ollama'], 'indisponível')
        self.assertIsNone(data['vram_bytes'])
        self.assertIsNone(data['gpu_percent'])

    def test_usage_ignores_prompt_and_output(self):
        from jarvis.diagnostics import usage_fields
        result = usage_fields({'prompt_eval_count': 12, 'eval_count': 5, 'message': {'content': 'privado'}})
        self.assertEqual(result['entrada'], 12)
        self.assertEqual(result['saida'], 5)
        self.assertNotIn('privado', str(result))
