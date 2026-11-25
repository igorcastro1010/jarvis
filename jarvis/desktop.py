"""Interface desktop local. Nenhuma tarefa Codex é executada por esta interface."""
import argparse
import sys
import sqlite3
from contextlib import closing
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QPushButton,
                               QStackedWidget, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from .conversation import answer, ollama
from .voice_session import Session

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
        radius = min(self.width(), self.height()) * .34
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
        self.history_path = Path(history_path) if history_path else None
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
        left = QVBoxLayout(); left.addWidget(label('ESTADO DA INTERFACE', 'eyebrow'))
        self.state_label = label('Disponível', 'value'); left.addWidget(self.state_label)
        left.addWidget(label('Envie uma mensagem para começar. A voz em segundo plano é um serviço separado.', 'muted'))
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
                db.execute('CREATE TABLE IF NOT EXISTS messages (role TEXT NOT NULL, content TEXT NOT NULL)')
                rows = db.execute('SELECT role, content FROM messages ORDER BY rowid DESC LIMIT 100').fetchall()
            for role, content in reversed(rows): self.chat.insertPlainText(role + ': ' + content + '\n')
        row = QHBoxLayout(); self.message = QLineEdit(); self.message.setPlaceholderText('Escreva uma mensagem para Jarvis…'); self.message.returnPressed.connect(self.send)
        self.send_button = QPushButton('Enviar'); self.send_button.setObjectName('primary'); self.send_button.clicked.connect(self.send)
        row.addWidget(self.message, 1); row.addWidget(self.send_button); layout.addLayout(row)
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
        layout.addWidget(label('Grafos existentes ainda não são visualizados nesta interface.', 'muted'))
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
        save = QPushButton('Salvar configurações de voz'); save.clicked.connect(self.save_voice_settings); layout.addWidget(save)
        layout.addWidget(label('As alterações entram em vigor ao reiniciar o assistente residente. Dispositivos e inicialização seguem o sistema.', 'muted'))
        compact = QPushButton('Alternar modo compacto'); compact.clicked.connect(self.toggle_compact); layout.addWidget(compact)
        layout.addStretch(); return page

    def toggle_compact(self):
        self.resize(800, 600) if self.width() > 900 else self.resize(1280, 800)

    def save_voice_settings(self):
        from .background import Settings, save_settings
        try:
            save_settings(self.config_path, Settings(int(self.inactivity.text()), float(self.threshold.text().replace(',', '.'))))
            self.statusBar().showMessage('Configurações salvas. Reinicie o serviço de voz.', 6000)
        except (ValueError, OSError):
            self.statusBar().showMessage('Configuração inválida ou arquivo indisponível.', 6000)

    def remember_chat(self, role, content):
        from .memory import SECRET
        if not self.history_path or SECRET.search(content): return
        try:
            with closing(sqlite3.connect(self.history_path, timeout=1)) as db, db:
                db.execute('INSERT INTO messages VALUES (?, ?)', (role, content[:4000]))
        except sqlite3.Error:
            self.statusBar().showMessage('Histórico indisponível nesta mensagem.', 6000)

    def run_job(self, fn, done):
        job = Worker(fn); self.jobs.add(job)
        def finish(result):
            self.jobs.discard(job); done(result)
        def fail(error):
            self.jobs.discard(job); self.set_status('erro'); self.send_button.setEnabled(True)
            self.chat.insertPlainText('\nJarvis: Não foi possível concluir a operação. Verifique os dados e tente novamente.\n')
            self.statusBar().showMessage('Não foi possível concluir a operação. Verifique os dados.', 7000)
        job.signals.done.connect(finish); job.signals.failed.connect(fail); self.pool.start(job)

    def set_status(self, status):
        self.status = status; self.state_label.setText(status.capitalize()); self.ring.status = status; self.ring.update()

    def send(self):
        text = self.message.text().strip()
        if not text or self.status == 'processando': return
        self.message.clear(); self.chat.insertPlainText('Você: ' + text + '\n'); self.send_button.setEnabled(False); self.set_status('processando')
        self.remember_chat('Você', text)
        def work():
            from .memory import default_store
            return answer(text, self.session, self.model, self.memory_factory() if self.memory_factory else default_store())
        def done(response):
            self.chat.insertPlainText('Jarvis: ' + response + '\n\n'); self.send_button.setEnabled(True); self.set_status('disponível')
            self.remember_chat('Jarvis', response)
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
        self.allow_quit = True; self.close(); QApplication.quit()

    def closeEvent(self, event):
        if self.tray and not self.allow_quit:
            self.hide(); event.ignore()
        else:
            event.accept()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--screenshot', help=argparse.SUPPRESS)
    args = parser.parse_args()
    from .local_vault import local_root
    app = QApplication(sys.argv[:1]); window = Window(tray=not bool(args.screenshot), history_path=local_root() / 'conversas.sqlite3'); window.show()
    if args.screenshot:
        QTimer.singleShot(300, lambda: (window.grab().save(args.screenshot), app.quit()))
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
