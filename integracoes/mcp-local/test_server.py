import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import server


class LocalToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Teste'], cwd=self.repo, check=True)
        subprocess.run(['git', 'config', 'user.email', 'teste@example.invalid'], cwd=self.repo, check=True)
        (self.repo / 'teste.txt').write_text('a')
        subprocess.run(['git', 'add', 'teste.txt'], cwd=self.repo, check=True)
        subprocess.run(['git', 'commit', '-qm', 'ficticio'], cwd=self.repo, check=True)
        (self.repo / 'teste.txt').write_text('b')
        self.config = root / 'autorizados.json'
        self.config.write_text(json.dumps({'projetos': {'teste': str(self.repo)}, 'aplicativos': {}}))
        self.patcher = patch.object(server, 'CONFIG', self.config)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_git_and_disallowed(self):
        self.assertIn('teste.txt', server.git_query('teste', 'status'))
        self.assertIn('ficticio', server.git_query('teste', 'log'))
        with self.assertRaises(ValueError): server.git_query('../fora', 'status')
        with self.assertRaises(ValueError): server.run('local_abrir_aplicativo', {'aplicativo': 'cmd'})

    def test_external_git_objects_rejected(self):
        p = self.repo / '.git' / 'objects' / 'info' / 'alternates'
        p.write_text(str(Path(self.temp.name)))
        with self.assertRaises(ValueError): server.git_query('teste', 'status')

    def test_metrics_and_disabled_codex(self):
        self.assertIn('ram_total_bytes', server.metrics())
        self.assertEqual(server.run('local_tarefas_codex', {})['estado'], 'desativado')

    def test_approved_application_passes_no_arguments(self):
        executable = Path(os.environ['SystemRoot']) / 'System32' / 'notepad.exe'
        with patch.object(server.subprocess, 'Popen') as popen:
            server.run('local_abrir_aplicativo', {'aplicativo': 'bloco de notas'})
            self.assertEqual(popen.call_args.args[0], [str(executable)])

    def test_config_cannot_authorize_other_executables(self):
        self.config.write_text(json.dumps({'projetos': {}, 'aplicativos': {'cmd': 'C:/Windows/System32/cmd.exe'}}))
        with patch.object(server.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError): server.run('local_abrir_aplicativo', {'aplicativo': 'cmd'})
            popen.assert_not_called()

    def test_memory_is_scoped_and_skips_sensitive_names(self):
        vault = Path(self.temp.name) / 'cofre'
        vault.mkdir()
        (vault / 'nota.md').write_text('projeto ficticio estrela azul', encoding='utf8')
        (vault / '.env').write_text('estrela segredoficticio', encoding='utf8')
        with patch.object(server, 'VAULT', vault):
            result = server.run('local_memorias', {'consulta': 'estrela'})
        self.assertEqual(len(result['resultados']), 1)
        self.assertIn('estrela azul', result['resultados'][0]['trecho'])

    def test_only_safe_tools_are_exposed_to_agent(self):
        exposed = {tool.spec.name for tool in server.tools}
        self.assertNotIn('shell_exec', exposed)
        self.assertNotIn('file_write', exposed)
        self.assertNotIn('codex_exec', exposed)

    def test_habblaud_reuses_healthy_server(self):
        with patch.object(server.urllib.request, 'urlopen') as urlopen, patch.object(server.os, 'startfile') as open_url, patch.object(server.subprocess, 'Popen') as popen:
            response = urlopen.return_value.__enter__.return_value
            response.status = 200
            with patch.object(server.json, 'load', return_value={'status': 'ok'}):
                result = server.open_habblaud()
            self.assertTrue(result['servidor_ja_ativo'])
            popen.assert_not_called()
            open_url.assert_called_once_with('http://127.0.0.1:4747')


if __name__ == '__main__': unittest.main()
