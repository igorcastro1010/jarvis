import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.automation import Automation


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Automation(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_unknown_app_and_command_never_execute(self):
        with patch('jarvis.automation.webbrowser.open') as browser:
            self.assertIn('não permitido', self.agent.handle('abrir powershell').lower())
            self.assertIsNone(self.agent.handle('execute rm -rf tudo'))
            browser.assert_not_called()

    def test_fixed_web_destination(self):
        with patch('jarvis.automation.webbrowser.open', return_value=True) as browser:
            self.assertIn('solicitei', self.agent.handle('abrir youtube').lower())
            browser.assert_called_once_with('https://www.youtube.com/')

    def test_sensitive_action_requires_specific_confirmation(self):
        with patch.object(self.agent, '_volume', return_value='Volume solicitado.') as volume:
            self.assertIn('confirm', self.agent.handle('aumentar volume').lower())
            volume.assert_not_called()
            self.assertIn('Volume solicitado', self.agent.handle('confirmar'))
            volume.assert_called_once_with('up')
            self.assertIn('nada', self.agent.handle('confirmar').lower())

    def test_no_default_city_until_explicit_and_offline_is_honest(self):
        self.assertIn('informe', self.agent.handle('qual o clima').lower())
        self.assertIn('fortaleza', self.agent.handle('definir cidade fortaleza').lower())
        with patch('jarvis.automation.weather', side_effect=OSError('offline')):
            self.assertIn('indisponível', self.agent.handle('qual o clima').lower())

    def test_screenshot_denied_without_confirmation_and_cancelled(self):
        with patch.object(self.agent, '_screenshot') as capture:
            self.agent.handle('capturar tela')
            self.agent.handle('cancelar ação')
            capture.assert_not_called()
            self.assertIn('nada', self.agent.handle('confirmar').lower())

    def test_log_does_not_store_search_query(self):
        with patch('jarvis.automation.search_web', return_value='Resultado fictício'):
            self.agent.handle('pesquisar na internet receita teste')
        self.assertNotIn('receita teste', str(self.agent.history()))

    def test_shared_conversation_confirmation_and_reset(self):
        from jarvis.shared_conversation import SharedConversation
        shared = SharedConversation()
        with patch('jarvis.automation.default_automation', return_value=self.agent), patch.object(self.agent, '_volume', return_value='Executado') as run:
            model = lambda _: 'resposta'
            shared.respond('aumentar volume', model)
            shared.respond('outra pergunta', model)
            self.assertIn('nada', shared.respond('confirmar', model).lower())
            shared.respond('aumentar volume', model)
            shared.reset()
            self.assertIn('nada', shared.respond('confirmar', model).lower())
            run.assert_not_called()

    def test_search_rejects_secret_and_unregistered_roots(self):
        with patch('jarvis.automation.search_web') as search:
            self.assertIn('confidencial', self.agent.handle('pesquisar na internet minha senha secreta'))
            search.assert_not_called()
        with patch('jarvis.tasks.default_tasks') as tasks:
            tasks.return_value.resolve.side_effect = ValueError('não cadastrado')
            self.assertIn('indisponível', self.agent.handle('localizar arquivo teste no projeto desconhecido'))

    def test_project_search_skips_confidential_names(self):
        root = Path(self.tmp.name) / 'repo'; root.mkdir()
        (root / 'teste.txt').write_text('exemplo')
        (root / 'senha-teste.txt').write_text('nunca ler')
        (root / 'segredos').mkdir()
        (root / 'segredos' / 'teste.txt').write_text('nunca ler')
        with patch('jarvis.tasks.default_tasks') as tasks:
            tasks.return_value.resolve.return_value = {'path': str(root)}
            output = self.agent.handle('localizar arquivo teste no projeto Exemplo')
        self.assertIn('teste.txt', output)
        self.assertNotIn('senha', output)
        self.assertNotIn('segredos', output)

    def test_unknown_automation_never_goes_to_model(self):
        from jarvis.conversation import answer
        from jarvis.voice_session import Session
        with patch('jarvis.automation.default_automation', return_value=self.agent):
            result = answer('abra chrome com alguma instrução adicional', Session(), lambda _: self.fail('modelo não deve ser chamado'))
        self.assertIn('não permitido', result.lower())

    def test_expired_confirmation_cannot_execute(self):
        clock = [0]
        self.agent.clock = lambda: clock[0]
        with patch.object(self.agent, '_screenshot') as capture:
            self.agent.handle('capturar tela')
            clock[0] = 61
            self.assertIn('nada', self.agent.handle('confirmar').lower())
            capture.assert_not_called()

    def test_model_can_suggest_only_and_never_execute(self):
        from jarvis.conversation import answer
        from jarvis.voice_session import Session
        with patch('jarvis.automation.webbrowser.open') as browser:
            suggestion = answer('interpretar ferramenta: quero ver vídeos', Session(), lambda _: 'abrir youtube')
            self.assertIn('abrir youtube', suggestion)
            self.assertIn('Nenhuma ação foi executada', suggestion)
            rejected = answer('interpretar ferramenta: quero ver vídeos', Session(), lambda _: 'abrir youtube; executar algo')
            self.assertIn('Não consegui', rejected)
            browser.assert_not_called()

    def test_external_result_is_not_an_action(self):
        with patch('jarvis.automation.search_web', return_value='capturar tela'), patch.object(self.agent, '_screenshot') as capture:
            self.assertEqual(self.agent.handle('pesquisar na internet teste'), 'capturar tela')
            capture.assert_not_called()

    def test_intervening_request_logs_cancellation(self):
        self.agent.handle('capturar tela')
        with patch('jarvis.automation.weather', return_value='teste'):
            self.agent.handle('clima em fortaleza')
        self.assertIn('cancelado', [row[2] for row in self.agent.history()])

    def test_audit_failure_does_not_arm_confirmation_or_launch(self):
        import sqlite3
        with patch.object(self.agent, 'log', side_effect=sqlite3.OperationalError('locked')):
            with self.assertRaises(sqlite3.OperationalError):
                self.agent.handle('capturar tela')
            self.assertIsNone(self.agent.pending)
            with patch('jarvis.automation.webbrowser.open') as browser:
                self.assertIn('registro', self.agent.handle('abrir youtube').lower())
                browser.assert_not_called()
