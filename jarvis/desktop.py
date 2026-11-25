"""Interface desktop local. Nenhuma tarefa Codex é executada por esta interface."""
import argparse
import sys
import sqlite3
import json
import subprocess
import threading
import time
import html
from datetime import datetime
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QSpinBox, QStackedWidget, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from .conversation import answer, ollama
from .voice_session import Session
from .shared_conversation import SharedConversation

STYLE = '''
QWidget { background:#070d16; color:#d9e8f1; font-family:'Segoe UI'; font-size:13px; }
QFrame#rail { background:#09121e; border-right:1px solid #172e3e; }
QFrame#panel { background:#0b1623; border:1px solid #1b3545; border-radius:10px; }
QLabel { background:transparent; }
QLabel#brand { color:#f1fbff; font-size:21px; font-weight:700; letter-spacing:4px; }
QLabel#eyebrow { color:#5dd8eb; font-size:11px; font-weight:600; letter-spacing:2px; }
QLabel#title { color:#f1fbff; font-size:27px; font-weight:600; }
QLabel#muted { color:#8ba4b5; }
QLabel#value { color:#e5f9fd; font-size:20px; font-weight:600; }
QPushButton { background:#102536; border:1px solid #28495a; border-radius:6px; padding:10px 14px; text-align:left; }
QPushButton:hover { background:#17384a; border-color:#5dd8eb; }
QPushButton:focus { border:2px solid #70dcec; }
QPushButton#primary { color:#07131a; background:#65d8e9; font-weight:700; }
QLineEdit, QTextEdit, QListWidget { background:#08121d; border:1px solid #203b4a; border-radius:6px; padding:9px; selection-background-color:#255064; }
QLineEdit:focus, QTextEdit:focus { border:1px solid #64d8e8; }
'''


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class VoiceSignals(QObject):
    exchange = Signal(str, str)
    level = Signal(float)


class Worker(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as exc:
            self.signals.failed.emit(f'{type(exc).__name__}: {exc}')


class CoreRing(QWidget):
    def __init__(self):
        super().__init__()
        self.status = 'disponível'
        self.phase = 0
        self.level = 0.0
        self.setMinimumSize(280, 250)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)

    def tick(self):
        if self.status == 'processando':
            self.phase = (self.phase + 2) % 360
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        x, y = self.width() / 2, self.height() / 2
        radius = min(self.width(), self.height()) * (.34 + min(self.level, .1) * .12)
        for factor, color, width in ((1.25, '#163d51', 1), (1.04, '#23566c', 2), (.85, '#4ac2d8', 2), (.57, '#3f9db3', 1)):
            painter.setPen(QPen(QColor(color), width))
            painter.drawEllipse(int(x-radius*factor), int(y-radius*factor), int(radius*2*factor), int(radius*2*factor))
        painter.setPen(QPen(QColor('#76e7f5'), 4))
        painter.drawArc(int(x-radius), int(y-radius), int(radius*2), int(radius*2), (45+self.phase)*16, 82*16)
        painter.setPen(QColor('#d9f7fc'))
        painter.drawText(self.rect(), Qt.AlignCenter, 'J A R V I S\n\n' + self.status.upper())


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


class Window(QMainWindow):
    def __init__(self, *, model=ollama, memory_factory=None, tasks_factory=None, skills_factory=None, tray=True, history_path=None):
        super().__init__()
        self.model = model
        self.session = Session()
        self.shared = SharedConversation()
        self.history_path = Path(history_path) if history_path else None
        self.history_enabled = True
        self.preferences_path = self.history_path.with_name('interface.json') if self.history_path else None
        if self.preferences_path:
            try:
                self.history_enabled = json.loads(self.preferences_path.read_text(encoding='utf8')).get('history_enabled', True) is True
            except (OSError, ValueError, AttributeError):
                pass
        self.voice_state = None
        self.voice_thread = None
        self.voice_lock = None
        self.text_busy = False
        self.voice_signals = VoiceSignals()
        self.voice_signals.exchange.connect(self.show_voice_exchange)
        self.voice_signals.level.connect(self.show_audio_level)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.jobs = set()
        self.memory_factory, self.tasks_factory, self.skills_factory = memory_factory, tasks_factory, skills_factory
        self.status = 'disponível'
        self.allow_quit = False
        self.setWindowTitle('Jarvis — Assistente pessoal')
        self.resize(1280, 800)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(STYLE)
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        rail = QFrame(); rail.setObjectName('rail'); rail.setFixedWidth(212)
        nav = QVBoxLayout(rail); nav.setContentsMargins(20, 28, 20, 22); nav.setSpacing(9)
        nav.addWidget(label('JARVIS', 'brand')); nav.addWidget(label('ASSISTENTE PESSOAL', 'eyebrow'))
        nav.addSpacing(34)
        self.stack = QStackedWidget()
        for name, builder in [('Visão geral', self.dashboard), ('Conversa', self.chat_page), ('Projetos e tarefas', self.tasks_page), ('Memória', self.memory_page), ('Skills e prompts', self.skills_page), ('Configurações', self.settings_page)]:
            button = QPushButton(name); button.clicked.connect(lambda checked=False, i=self.stack.count(): self.stack.setCurrentIndex(i))
            nav.addWidget(button); self.stack.addWidget(builder())
        nav.addStretch(); nav.addWidget(label('LOCAL · CODEX DESATIVADO', 'eyebrow'))
        outer.addWidget(rail); outer.addWidget(self.stack, 1)
        self.tray = None
        if tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon), self)
            menu = QMenu(self); menu.addAction('Abrir', self.showNormal); menu.addAction('Sair', self.quit_app)
            self.tray.setContextMenu(menu); self.tray.setToolTip('Jarvis — interface'); self.tray.show()
            self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.metrics_timer = QTimer(self); self.metrics_timer.timeout.connect(self.update_metrics); self.metrics_timer.start(3000)
        self.update_metrics()

    def page(self, eyebrow, title, description):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(42, 32, 42, 30); layout.setSpacing(16)
        layout.addWidget(label(eyebrow, 'eyebrow')); layout.addWidget(label(title, 'title')); layout.addWidget(label(description, 'muted'))
        return page, layout

    def dashboard(self):
        page, layout = self.page('CENTRAL DE CONTROLE  /  01', 'Olá, senhor.', 'Seu assistente pessoal, em um só lugar.')
        panel = QFrame(); panel.setObjectName('panel'); row = QHBoxLayout(panel); row.setContentsMargins(30, 25, 30, 25)
        left = QVBoxLayout(); left.addWidget(label('ESTADO DO ASSISTENTE', 'eyebrow'))
        self.state_label = label('Disponível', 'value'); left.addWidget(self.state_label)
        left.addWidget(label('Diga Jarvis para começar ou envie uma mensagem.', 'muted'))
        left.addStretch(); button = QPushButton('Abrir conversa  →'); button.setObjectName('primary'); button.clicked.connect(lambda: self.stack.setCurrentIndex(1)); left.addWidget(button)
        row.addLayout(left, 1); self.ring = CoreRing(); row.addWidget(self.ring, 2); layout.addWidget(panel, 1)
        strip = QHBoxLayout()
        self.cpu_label = label('CPU —', 'value'); self.ram_label = label('RAM —', 'value')
        for heading, widget in [('PROCESSADOR', self.cpu_label), ('MEMÓRIA', self.ram_label), ('GPU', label('Indisponível', 'value'))]:
            box = QFrame(); box.setObjectName('panel'); box_layout = QVBoxLayout(box); box_layout.addWidget(label(heading, 'eyebrow')); box_layout.addWidget(widget); strip.addWidget(box)
        layout.addLayout(strip)
        return page

    def chat_page(self):
        page, layout = self.page('CONVERSA  /  02', 'Como posso ajudar?', 'Histórico local sem criptografia. Não inclua dados confidenciais.')
        self.chat = QTextEdit(); self.chat.setReadOnly(True); layout.addWidget(self.chat, 1)
        if self.history_path:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.history_path)) as db, db:
                db.execute('CREATE TABLE IF NOT EXISTS messages (role TEXT NOT NULL, content TEXT NOT NULL, created TEXT)')
                self.ensure_history_columns(db)
                rows = db.execute('SELECT role, content, created FROM messages ORDER BY rowid DESC LIMIT 100').fetchall()
            if self.history_enabled:
                for role, content, created in reversed(rows): self.render_message(role, content, created or 'desconhecido')
        row = QHBoxLayout(); self.message = QLineEdit(); self.message.setPlaceholderText('Escreva uma mensagem para Jarvis…'); self.message.returnPressed.connect(self.send)
        self.send_button = QPushButton('Enviar'); self.send_button.setObjectName('primary'); self.send_button.clicked.connect(self.send)
        row.addWidget(self.message, 1); row.addWidget(self.send_button); layout.addLayout(row)
        voice_controls = QHBoxLayout()
        mute = QPushButton('Silenciar / interromper'); mute.clicked.connect(self.mute_voice)
        unmute = QPushButton('Reativar voz'); unmute.clicked.connect(self.unmute_voice)
        voice_controls.addWidget(mute); voice_controls.addWidget(unmute); layout.addLayout(voice_controls)
        return page

    def tasks_page(self):
        page, layout = self.page('PROJETOS  /  03', 'Projetos e tarefas', 'Cadastro e fila existentes. O Codex não é iniciado automaticamente.')
        self.tasks = QTextEdit(); self.tasks.setReadOnly(True); layout.addWidget(self.tasks, 1)
        row = QHBoxLayout(); self.project_name = QLineEdit(); self.project_name.setPlaceholderText('Nome do projeto')
        self.project_path = QLineEdit(); self.project_path.setPlaceholderText('Diretório Git existente')
        register = QPushButton('Cadastrar'); register.clicked.connect(self.register_project)
        row.addWidget(self.project_name); row.addWidget(self.project_path, 1); row.addWidget(register); layout.addLayout(row)
        row = QHBoxLayout(); self.task_request = QLineEdit(); self.task_request.setPlaceholderText('Pedido para o projeto indicado acima')
        submit = QPushButton('Enfileirar'); submit.clicked.connect(self.submit_task); row.addWidget(self.task_request, 1); row.addWidget(submit); layout.addLayout(row)
        refresh = QPushButton('Atualizar projetos e fila'); refresh.clicked.connect(self.refresh_tasks); layout.addWidget(refresh)
        return page

    def memory_page(self):
        page, layout = self.page('MEMÓRIA LOCAL  /  04', 'Memória', 'Busque no cofre pelo escopo exato do projeto. Conteúdo permanece local.')
        row = QHBoxLayout(); self.memory_project = QLineEdit(); self.memory_project.setPlaceholderText('Projeto (vazio para pessoal)')
        self.memory_query = QLineEdit(); self.memory_query.setPlaceholderText('Termos de busca')
        search = QPushButton('Buscar'); search.clicked.connect(self.search_memory)
        row.addWidget(self.memory_project); row.addWidget(self.memory_query, 1); row.addWidget(search); layout.addLayout(row)
        self.memory_results = QTextEdit(); self.memory_results.setReadOnly(True); layout.addWidget(self.memory_results, 1)
        row = QHBoxLayout(); self.memory_id = QLineEdit(); self.memory_id.setPlaceholderText('ID da memória')
        self.memory_edit = QLineEdit(); self.memory_edit.setPlaceholderText('Conteúdo corrigido')
        correct = QPushButton('Corrigir memória'); correct.clicked.connect(self.correct_memory)
        row.addWidget(self.memory_id); row.addWidget(self.memory_edit, 1); row.addWidget(correct); layout.addLayout(row)
        graph = QPushButton('Mostrar grafo existente do escopo'); graph.clicked.connect(self.show_graph); layout.addWidget(graph)
        layout.addWidget(label('O grafo é exibido como lista de relações locais, sem gerar novo grafo.', 'muted'))
        return page

    def skills_page(self):
        page, layout = self.page('FERRAMENTAS  /  05', 'Skills e prompts', 'Sugestões locais; ativar não instala nem executa uma skill.')
        self.skill_list = QTextEdit(); self.skill_list.setReadOnly(True); layout.addWidget(self.skill_list, 1)
        row = QHBoxLayout(); refresh = QPushButton('Atualizar catálogo'); refresh.clicked.connect(self.refresh_skills)
        self.prompt_input = QLineEdit(); self.prompt_input.setPlaceholderText('Descreva a tarefa')
        generate = QPushButton('Gerar prompt'); generate.clicked.connect(self.generate_prompt)
        row.addWidget(refresh); row.addWidget(self.prompt_input, 1); row.addWidget(generate); layout.addLayout(row)
        row = QHBoxLayout(); self.skill_name = QLineEdit(); self.skill_name.setPlaceholderText('Nome da skill')
        activate = QPushButton('Ativar sugestão'); activate.clicked.connect(lambda: self.set_skill(True))
        deactivate = QPushButton('Desativar sugestão'); deactivate.clicked.connect(lambda: self.set_skill(False))
        search = QPushButton('Buscar Find Skills'); search.clicked.connect(self.find_skills)
        row.addWidget(self.skill_name, 1); row.addWidget(activate); row.addWidget(deactivate); row.addWidget(search); layout.addLayout(row)
        self.prompt_output = QTextEdit(); self.prompt_output.setPlaceholderText('O prompt aparecerá aqui para revisão e cópia manual.'); layout.addWidget(self.prompt_output, 1)
        copy = QPushButton('Copiar prompt'); copy.clicked.connect(lambda: QApplication.clipboard().setText(self.prompt_output.toPlainText())); layout.addWidget(copy)
        return page

    def settings_page(self):
        page, layout = self.page('PREFERÊNCIAS  /  06', 'Configurações', 'A interface não altera automaticamente sua inicialização ou dispositivos.')
        from .background import load_settings
        self.config_path = Path(__file__).resolve().parent.parent / 'data' / 'configuracao.json'
        current = load_settings(self.config_path)
        form = QFormLayout(); self.inactivity = QLineEdit(str(current.inactivity_seconds)); self.threshold = QLineEdit(str(current.threshold))
        form.addRow('Inatividade em segundos', self.inactivity); form.addRow('Limiar do microfone', self.threshold); layout.addLayout(form)
        self.input_device = QComboBox(); self.input_device.addItem('Padrão do sistema', None)
        self.output_device = QComboBox(); self.output_device.addItem('Padrão do sistema', None)
        self.stt_model = QComboBox(); self.stt_model.addItems(['small', 'tiny'])
        self.volume = QSpinBox(); self.volume.setRange(0, 100); self.volume.setValue(100); self.volume.setSuffix('%')
        options = self.audio_options()
        for combo, key in ((self.input_device, 'input'), (self.output_device, 'output')):
            index = options.get(key)
            if type(index) is int and index >= 0:
                combo.addItem(f'Dispositivo salvo #{index} (atualize a lista)', index); combo.setCurrentIndex(1)
        if options.get('stt') in ('small', 'tiny'): self.stt_model.setCurrentText(options['stt'])
        if type(options.get('volume')) is int and 0 <= options['volume'] <= 100: self.volume.setValue(options['volume'])
        form.addRow('Microfone', self.input_device); form.addRow('Saída', self.output_device)
        form.addRow('Reconhecimento local', self.stt_model); form.addRow('Volume de voz', self.volume)
        form.addRow('Síntese', label('Piper pt-BR Faber (modelo instalado)', 'muted'))
        devices = QPushButton('Listar dispositivos de áudio'); devices.clicked.connect(self.list_audio_devices); layout.addWidget(devices)
        save = QPushButton('Salvar configurações de voz'); save.clicked.connect(self.save_voice_settings); layout.addWidget(save)
        self.history_checkbox = QCheckBox('Salvar histórico de conversa neste computador')
        self.history_checkbox.setChecked(self.history_enabled)
        self.history_checkbox.toggled.connect(self.set_history_enabled)
        layout.addWidget(self.history_checkbox)
        startup = QHBoxLayout()
        for title, action in (('Consultar inicialização', 'Status'), ('Habilitar inicialização', 'Habilitar'), ('Desabilitar inicialização', 'Desabilitar')):
            button = QPushButton(title); button.clicked.connect(lambda checked=False, a=action: self.change_startup(a)); startup.addWidget(button)
        layout.addLayout(startup)
        layout.addWidget(label('As alterações entram em vigor ao reiniciar o assistente residente. Dispositivos e inicialização seguem o sistema.', 'muted'))
        compact = QPushButton('Alternar modo compacto'); compact.clicked.connect(self.toggle_compact); layout.addWidget(compact)
        layout.addStretch(); return page

    def toggle_compact(self):
        self.resize(800, 600) if self.width() > 900 else self.resize(1280, 800)

    def change_startup(self, action):
        script = Path(__file__).resolve().parent.parent / 'scripts' / 'inicializacao-interface.ps1'
        def work():
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Acao', action],
                                    capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode: raise RuntimeError('Inicialização indisponível')
            return result.stdout.strip()
        self.run_job(work, lambda message: self.statusBar().showMessage(message, 8000))

    def set_history_enabled(self, enabled):
        self.history_enabled = enabled
        if self.preferences_path:
            try:
                self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.preferences_path.with_suffix('.tmp')
                temp.write_text(json.dumps({'history_enabled': enabled}), encoding='utf8')
                temp.replace(self.preferences_path)
            except OSError:
                self.statusBar().showMessage('Não foi possível salvar a preferência.', 6000)

    def show_voice_exchange(self, spoken, response):
        self.render_message('Você (voz)', spoken)
        self.render_message('Jarvis (voz)', response)
        self.remember_chat('Você (voz)', spoken)
        self.remember_chat('Jarvis (voz)', response)

    def show_audio_level(self, level):
        self.ring.level = max(0, min(level, 1)); self.ring.update()

    def mute_voice(self):
        if self.voice_state:
            self.voice_state.mute()
            self.shared.reset()
            self.show_audio_level(0)

    def unmute_voice(self):
        if self.voice_state:
            self.voice_state.unmute()

    def refresh_voice_status(self):
        if self.voice_state and not self.text_busy:
            with self.voice_state.lock:
                status = self.voice_state.status
            if status not in ('aguardando', 'ouvindo') and self.ring.level:
                self.show_audio_level(0)
            if status != self.status:
                self.set_status(status)

    def start_voice(self):
        from .background import AssistantState, InstanceLock, load_settings
        lock = InstanceLock()
        if not lock.acquire():
            lock.close()
            self.statusBar().showMessage('Outra sessão Jarvis já utiliza a voz.', 0)
            self.set_status('erro')
            return False
        try:
            from .tray import AudioAdapters
            from .voice import listen
            from .service import VoiceService
            from .memory import default_store
            state = AssistantState()
            options = self.audio_options()
            stt = options.get('stt') if options.get('stt') in ('small', 'tiny') else 'small'
            volume = options.get('volume') if type(options.get('volume')) is int and 0 <= options['volume'] <= 100 else 100
            device_in = options.get('input') if type(options.get('input')) is int and options['input'] >= 0 else None
            device_out = options.get('output') if type(options.get('output')) is int and options['output'] >= 0 else None
            adapters = AudioAdapters(stt, device_out, volume / 100)
            capture = lambda **kwargs: listen(**kwargs, device=device_in, on_level=self.voice_signals.level.emit)
            service = VoiceService(state, lambda: load_settings(self.config_path), capture, adapters.transcribe,
                                   adapters.speak, self.model, memory=self.memory_factory() if self.memory_factory else default_store(),
                                   on_exchange=self.voice_signals.exchange.emit, shared=self.shared)
            self.voice_state, self.voice_lock = state, lock
            self.voice_thread = threading.Thread(target=service.run, daemon=True, name='jarvis-voz')
            self.voice_thread.start()
            self.voice_timer = QTimer(self); self.voice_timer.timeout.connect(self.refresh_voice_status); self.voice_timer.start(150)
            return True
        except Exception:
            lock.close()
            self.set_status('erro')
            self.statusBar().showMessage('Não foi possível iniciar o serviço de voz.', 0)
            return False

    def save_voice_settings(self):
        from .background import Settings, save_settings
        try:
            save_settings(self.config_path, Settings(int(self.inactivity.text()), float(self.threshold.text().replace(',', '.'))))
            if self.audio_path:
                self.audio_path.parent.mkdir(parents=True, exist_ok=True)
                self.audio_path.write_text(json.dumps({'input': self.input_device.currentData(), 'output': self.output_device.currentData(),
                                                       'stt': self.stt_model.currentText(), 'volume': self.volume.value()}), encoding='utf8')
            self.statusBar().showMessage('Configurações salvas. Reinicie o serviço de voz.', 6000)
        except (ValueError, OSError):
            self.statusBar().showMessage('Configuração inválida ou arquivo indisponível.', 6000)

    @property
    def audio_path(self):
        return self.preferences_path.with_name('audio-interface.json') if self.preferences_path else None

    def audio_options(self):
        try:
            options = json.loads(self.audio_path.read_text(encoding='utf8')) if self.audio_path else {}
            return options if isinstance(options, dict) else {}
        except (OSError, ValueError):
            return {}

    def list_audio_devices(self):
        def work():
            import sounddevice as sd
            return list(sd.query_devices())
        def done(devices):
            for combo in (self.input_device, self.output_device):
                combo.clear(); combo.addItem('Padrão do sistema', None)
            for index, device in enumerate(devices):
                if device['max_input_channels'] > 0: self.input_device.addItem(device['name'], index)
                if device['max_output_channels'] > 0: self.output_device.addItem(device['name'], index)
            options = self.audio_options()
            for combo, key in ((self.input_device, 'input'), (self.output_device, 'output')):
                match = combo.findData(options.get(key))
                if match >= 0: combo.setCurrentIndex(match)
        self.run_job(work, done)

    def remember_chat(self, role, content):
        from .memory import SECRET
        if not self.history_enabled or not self.history_path or SECRET.search(content): return
        try:
            with closing(sqlite3.connect(self.history_path, timeout=1)) as db, db:
                self.ensure_history_columns(db)
                db.execute('INSERT INTO messages (role, content, created) VALUES (?, ?, ?)',
                           (role, content[:4000], datetime.now().astimezone().isoformat(timespec='seconds')))
        except sqlite3.Error:
            self.statusBar().showMessage('Histórico indisponível nesta mensagem.', 6000)

    @staticmethod
    def ensure_history_columns(db):
        if 'created' not in {row[1] for row in db.execute('PRAGMA table_info(messages)')}:
            db.execute('ALTER TABLE messages ADD COLUMN created TEXT')

    def render_message(self, role, content, created=None):
        try:
            timestamp = datetime.fromisoformat(created).astimezone().strftime('%H:%M') if created else datetime.now().strftime('%H:%M')
        except (ValueError, TypeError):
            timestamp = '--:--'
        color = '#78d9e8' if role.startswith('Jarvis') else '#aabbd0'
        safe_role = html.escape(role)
        safe_content = html.escape(content).replace('\n', '<br>')
        cursor = self.chat.textCursor(); cursor.movePosition(QTextCursor.End)
        if not self.chat.document().isEmpty(): cursor.insertBlock()
        cursor.insertHtml(f'<p style="margin-top:12px; margin-bottom:4px; color:{color};"><b>{safe_role}</b> &nbsp; {timestamp}</p>'
                          f'<p style="margin-top:0px; margin-bottom:14px; color:#e4eef4;">{safe_content}</p>')
        self.chat.setTextCursor(cursor); self.chat.ensureCursorVisible()

    def run_job(self, fn, done):
        job = Worker(fn); self.jobs.add(job)
        def finish(result):
            self.jobs.discard(job); done(result)
        def fail(error):
            self.jobs.discard(job); self.text_busy = False; self.set_status('erro'); self.send_button.setEnabled(True)
            self.chat.insertPlainText('\nJarvis: Não foi possível concluir a operação. Verifique os dados e tente novamente.\n')
            self.statusBar().showMessage('Não foi possível concluir a operação. Verifique os dados.', 7000)
        job.signals.done.connect(finish); job.signals.failed.connect(fail); self.pool.start(job)

    def set_status(self, status):
        self.status = status; self.state_label.setText(status.capitalize()); self.ring.status = status; self.ring.update()

    def send(self):
        text = self.message.text().strip()
        if not text or self.text_busy: return
        self.text_busy = True
        self.message.clear(); self.render_message('Você (texto)', text); self.send_button.setEnabled(False); self.set_status('processando')
        self.remember_chat('Você (texto)', text)
        def work():
            from .memory import default_store
            return self.shared.respond(text, self.model, self.memory_factory() if self.memory_factory else default_store())
        def done(response):
            self.render_message('Jarvis (texto)', response); self.text_busy = False; self.send_button.setEnabled(True); self.set_status('disponível')
            self.remember_chat('Jarvis (texto)', response)
            if self.tray and not self.isVisible(): self.tray.showMessage('Jarvis', 'Resposta disponível na conversa.')
        self.run_job(work, done)

    def refresh_tasks(self):
        def work():
            from .tasks import default_tasks
            store = self.tasks_factory() if self.tasks_factory else default_tasks()
            with store.connect() as db: projects = [row['name'] for row in db.execute('SELECT name FROM projects ORDER BY name')]
            tasks = store.list(50)
            return 'PROJETOS\n' + ('\n'.join(projects) or 'Nenhum projeto cadastrado.') + '\n\nFILA E HISTÓRICO\n' + ('\n'.join(f"{r['id']}  ·  {r['project']}  ·  {r['status']}" for r in tasks) or 'Nenhuma tarefa.')
        self.run_job(work, self.tasks.setPlainText)

    def search_memory(self):
        query, project = self.memory_query.text(), self.memory_project.text().strip() or None
        def work():
            from .memory import default_store
            store = self.memory_factory() if self.memory_factory else default_store()
            return '\n\n'.join(f"{r['id']} · {r['date']} · {r['origin']}\n{r['content']}" for r in store.search(query, project=project)) or 'Nenhuma memória encontrada.'
        self.run_job(work, self.memory_results.setPlainText)

    def correct_memory(self):
        ident, text = self.memory_id.text().strip(), self.memory_edit.text()
        project = self.memory_project.text().strip() or None
        def work():
            from .memory import default_store
            store = self.memory_factory() if self.memory_factory else default_store()
            store.correct(ident, text, project=project)
            return 'Memória corrigida; versão anterior arquivada.'
        self.run_job(work, self.memory_results.setPlainText)

    def show_graph(self):
        project = self.memory_project.text().strip() or None
        def work():
            from .memory import default_store, scope_name
            store = self.memory_factory() if self.memory_factory else default_store()
            graphs = store.root / '.jarvis-grafos'
            scope = graphs / scope_name(project)
            folder = scope / 'graphify-out'
            path = folder / 'graph.json'
            if any(p.is_symlink() for p in (graphs, scope, folder, path)) or not path.is_file() or path.stat().st_size > 2_000_000:
                raise ValueError('Grafo indisponível ou inválido.')
            data = json.loads(path.read_text(encoding='utf8'))
            nodes, edges = data.get('nodes', []), data.get('links', data.get('edges', []))
            if not isinstance(nodes, list) or not isinstance(edges, list): raise ValueError('Formato de grafo inválido.')
            names = {str(n.get('id', '')): str(n.get('label', n.get('id', '')))[:100]
                     for n in nodes[:300] if isinstance(n, dict)}
            relations = []
            for edge in edges[:300]:
                if not isinstance(edge, dict): continue
                source, target = str(edge.get('source', '')), str(edge.get('target', ''))
                if source in names and target in names:
                    relations.append(f'{names[source]} → {names[target]}')
            return 'RELAÇÕES DO GRAFO\n' + ('\n'.join(relations) or 'Nenhuma relação exibível encontrada.')
        self.run_job(work, self.memory_results.setPlainText)

    def register_project(self):
        name, path = self.project_name.text().strip(), self.project_path.text().strip()
        def work():
            from .tasks import default_tasks
            store = self.tasks_factory() if self.tasks_factory else default_tasks()
            store.register(name, [], path, None)
            return 'Projeto cadastrado sem permissões de escrita ou push.'
        self.run_job(work, self.tasks.setPlainText)

    def submit_task(self):
        name, request = self.project_name.text().strip(), self.task_request.text().strip()
        def work():
            from .tasks import default_tasks
            store = self.tasks_factory() if self.tasks_factory else default_tasks()
            return 'Tarefa ' + store.submit(name, request) + ' enfileirada. Execução automática desativada.'
        self.run_job(work, self.tasks.setPlainText)

    def refresh_skills(self):
        def work():
            from .skills import default_manager
            manager = self.skills_factory() if self.skills_factory else default_manager()
            return '\n\n'.join(f"{s['name']}  ·  {'ativa' if s['enabled'] else 'inativa'}\n{s['description']}\n{s['origin']}" for s in manager.list())
        self.run_job(work, self.skill_list.setPlainText)

    def generate_prompt(self):
        request = self.prompt_input.text()
        def work():
            from .skills import default_manager, build_prompt
            from .memory import default_store
            return build_prompt(self.skills_factory() if self.skills_factory else default_manager(), request, self.memory_factory() if self.memory_factory else default_store())
        self.run_job(work, self.prompt_output.setPlainText)

    def set_skill(self, enabled):
        name = self.skill_name.text().strip()
        def work():
            from .skills import default_manager
            manager = self.skills_factory() if self.skills_factory else default_manager()
            manager.set_enabled(name, enabled)
            return 'Preferência salva; nenhuma skill foi instalada ou executada.'
        self.run_job(work, self.skill_list.setPlainText)

    def find_skills(self):
        query = self.skill_name.text().strip()
        def work():
            from .skills import discover
            return discover(query) + '\n\nResultados externos requerem revisão.'
        self.run_job(work, self.skill_list.setPlainText)

    def update_metrics(self):
        try:
            import psutil
            self.cpu_label.setText(f'{psutil.cpu_percent():.0f}%'); self.ram_label.setText(f'{psutil.virtual_memory().percent:.0f}%')
        except ImportError:
            self.cpu_label.setText('Indisponível'); self.ram_label.setText('Indisponível')

    def quit_app(self):
        if self.voice_state:
            with self.voice_state.lock:
                self.voice_state.stopped = True
                self.voice_state.generation += 1
        self.allow_quit = True; self.close(); QApplication.quit()

    def closeEvent(self, event):
        if self.tray and not self.allow_quit:
            self.hide(); event.ignore()
        else:
            if self.voice_state:
                with self.voice_state.lock:
                    self.voice_state.stopped = True
                    self.voice_state.generation += 1
            event.accept()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--screenshot', help=argparse.SUPPRESS)
    args = parser.parse_args()
    from .local_vault import local_root
    app = QApplication(sys.argv[:1])
    desktop_lock = None
    if not args.screenshot:
        from .background import InstanceLock
        desktop_lock = InstanceLock('Local\\JarvisDesktop-v071')
        if not desktop_lock.acquire():
            desktop_lock.close()
            QMessageBox.warning(None, 'Jarvis', 'A interface Jarvis já está aberta.')
            return 2
    window = Window(tray=not bool(args.screenshot), history_path=local_root() / 'conversas.sqlite3'); window.show()
    if args.screenshot:
        QTimer.singleShot(300, lambda: (window.grab().save(args.screenshot), app.quit()))
    else:
        QTimer.singleShot(0, window.start_voice)
    result = app.exec()
    if window.voice_thread:
        window.voice_thread.join(timeout=2)
    if window.voice_lock:
        window.voice_lock.close()
    if desktop_lock:
        desktop_lock.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
