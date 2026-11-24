import tempfile
import unittest
from pathlib import Path
from jarvis.codex_profile import build_profile


class ProfileTests(unittest.TestCase):
    def test_profile_limits_paths_and_escapes_windows_names(self):
        with tempfile.TemporaryDirectory() as d:
            workspace = Path(d)/'projeto com espaços'; workspace.mkdir()
            runtime = Path(d)/'pwsh'; runtime.mkdir()
            profile = build_profile(workspace, runtime, writable=True)
            self.assertIn('":minimal"="read"', profile)
            self.assertIn('="write"', profile)
            self.assertIn('="read"', profile)
            self.assertNotIn('danger-full-access', profile)

    def test_rejects_missing_or_overlapping_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); work = root/'work'; work.mkdir()
            with self.assertRaises(ValueError): build_profile(work, root/'missing')
            with self.assertRaises(ValueError): build_profile(work, root)
