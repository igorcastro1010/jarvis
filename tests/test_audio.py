import unittest
import subprocess
import sys
from unittest.mock import patch
import numpy as np
from jarvis import voice


class AudioTests(unittest.TestCase):
    def test_voice_import_does_not_load_inference_libraries(self):
        code = "import sys, jarvis.voice; assert 'faster_whisper' not in sys.modules; assert 'piper' not in sys.modules"
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
    def test_console_refuses_when_resident_is_running(self):
        class Busy:
            def acquire(self): return False
            def close(self): pass
        with patch('jarvis.background.InstanceLock', return_value=Busy()):
            self.assertEqual(voice.main(), 2)

    def test_cancel_stops_capture_and_closes_microphone(self):
        class Stream:
            closed = False
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): Stream.closed = True
            def read(self, block): return np.ones((block, 1), dtype='float32'), False
        with patch.object(voice.sd, 'InputStream', Stream):
            self.assertIsNone(voice.listen(cancelled=lambda: True))
        self.assertTrue(Stream.closed)

    def test_capture_closes_stream_after_voice_and_silence(self):
        class Stream:
            closed = False
            count = 0
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                Stream.closed = True
            def read(self, block):
                self.count += 1
                value = 0.1 if self.count == 1 else 0.0
                return np.full((block, 1), value, dtype='float32'), False
        with patch.object(voice.sd, 'InputStream', Stream):
            audio = voice.listen()
        self.assertTrue(Stream.closed)
        self.assertEqual(len(audio), 6 * (voice.RATE // 5))

    def test_level_and_input_device_are_forwarded(self):
        levels, options = [], {}
        class Stream:
            count = 0
            def __init__(self, **kwargs): options.update(kwargs)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, block):
                self.count += 1
                return np.full((block, 1), 0.1 if self.count == 1 else 0.0, dtype='float32'), False
        with patch.object(voice.sd, 'InputStream', Stream):
            voice.listen(device=7, on_level=levels.append)
        self.assertEqual(options['device'], 7)
        self.assertGreater(levels[0], 0.09)

    def test_escape_stops_playback(self):
        chunk = type('Chunk', (), {'audio_float_array': np.zeros(4), 'sample_rate': 16000})()
        engine = type('Engine', (), {'synthesize': lambda self, text: [chunk]})()
        stream = type('Stream', (), {'active': True})()
        with patch.object(voice.sd, 'play'), patch.object(voice.sd, 'get_stream', return_value=stream), \
             patch.object(voice.sd, 'stop') as stop, patch.object(voice.msvcrt, 'kbhit', return_value=True), \
             patch.object(voice.msvcrt, 'getwch', return_value='\x1b'):
            self.assertFalse(voice.speak(engine, 'teste'))
            stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
