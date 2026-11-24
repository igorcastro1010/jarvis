import unittest
from unittest.mock import patch
import numpy as np
from jarvis import voice


class AudioTests(unittest.TestCase):
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
