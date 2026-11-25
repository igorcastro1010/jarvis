import json
import unittest
from unittest.mock import patch

from jarvis.conversation import ollama


class ModelOptionsTests(unittest.TestCase):
    def test_generation_marks_truncation_and_configures_qwen3(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'message': {'content': 'Resposta incompleta'}, 'done_reason': 'length'}).encode()
        with patch('urllib.request.urlopen', return_value=Response()) as call:
            output = ollama([{'role': 'user', 'content': 'teste'}], model='qwen3:4b', keep_alive='0')
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(payload['options']['num_predict'], 512)
        self.assertFalse(payload['think'])
        self.assertEqual(payload['keep_alive'], '0')
        self.assertIn('truncada', output)

    def test_invalid_model_is_rejected(self):
        with self.assertRaises(ValueError): ollama([], model='modelo-arbitrario')
