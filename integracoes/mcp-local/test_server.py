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
        self.config.write_text(json.dumps({'projetos': {'Racha Fortalaka': str(self.repo)}, 'aplicativos': {}}))
        self.patcher = patch.object(server, 'CONFIG', self.config)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.root_patcher = patch.object(server, 'FORTALAKA_ROOT', self.repo)
        self.root_patcher.start()
        self.addCleanup(self.root_patcher.stop)

    def test_git_and_disallowed(self):
        self.assertIn('teste.txt', server.git_query('Racha Fortalaka', 'status'))
        self.assertIn('## ', server.git_query('Racha Fortalaka', 'status'))
        self.assertIn('ficticio', server.git_query('Racha Fortalaka', 'log'))
        with self.assertRaises(ValueError): server.git_query('../fora', 'status')
        with self.assertRaises(ValueError): server.run('local_abrir_aplicativo', {'aplicativo': 'cmd'})

    def test_external_git_objects_rejected(self):
        p = self.repo / '.git' / 'objects' / 'info' / 'alternates'
        p.write_text(str(Path(self.temp.name)))
        with self.assertRaises(ValueError): server.git_query('Racha Fortalaka', 'status')

    def test_docs_allowlist_and_scope(self):
        (self.repo / 'README.md').write_text('Futebol ficticio', encoding='utf8')
        result = server.project_document('Racha Fortalaka', 'visao geral')
        self.assertIn('Futebol ficticio', result['conteudo'])
        with self.assertRaises(ValueError): server.project_document('Racha Fortalaka', '../../secret')
        with self.assertRaises(ValueError): server.project_document('outro', 'visao geral')

    def test_project_pending_isolation(self):
        vault = Path(self.temp.name) / 'cofre'; vault.mkdir()
        (vault / 'outro.md').write_text('# Outro projeto\n- [ ] tarefa de outro projeto', encoding='utf8')
        (vault / 'fortalaka.md').write_text('# Racha Fortalaka\n- [ ] tarefa ficticia do racha', encoding='utf8')
        with patch.object(server, 'VAULT', vault):
            result = server.project_pending('Racha Fortalaka')
        self.assertEqual(len(result['pendencias']), 1)
        self.assertIn('tarefa ficticia', result['pendencias'][0]['trecho'])

    def test_git_and_obsidian_have_distinct_sources_and_dates(self):
        git = server.run('local_git_status', {'projeto': 'Racha Fortalaka'})
        self.assertEqual(git['fonte'], 'Git local')
        self.assertIn('consultado_em', git)
        self.assertNotIn('pendencias_obsidian', git)
        vault = Path(self.temp.name) / 'cofre'; vault.mkdir()
        with patch.object(server, 'VAULT', vault):
            memory = server.project_pending('Racha Fortalaka')
        self.assertEqual(memory['fonte'], 'Obsidian')
        self.assertIn('consultado_em', memory)
        self.assertEqual(memory['mensagem'], 'Nenhuma pendência registrada no Obsidian')
        self.assertEqual(memory['pendencias'], [])

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
            result = server.search_memories('estrela')
        self.assertEqual(len(result['resultados']), 1)
        self.assertIn('estrela azul', result['resultados'][0]['trecho'])

    def test_only_safe_tools_are_exposed_to_agent(self):
        exposed = {tool.spec.name for tool in server.tools}
        self.assertNotIn('shell_exec', exposed)
        self.assertNotIn('file_write', exposed)
        self.assertNotIn('codex_exec', exposed)
        self.assertNotIn('local_memorias', exposed)

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
