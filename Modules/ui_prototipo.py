"""
Protótipo de UI em PyQt6 (isolado) para experimentação de UX/estética.

Inclui (simulado):
 - Navegação lateral moderna
 - Dashboard com cartões, micro‑gráficos (sparklines) e logs
 - Monitor de sensores com cartões responsivos
 - Fluxo de calibração fake
 - Testes com métricas (MAE / RMSE / Corr) em tempo real
 - Dois minigames simples embutidos (pong / pulso animado)
 - Histórico (mock)
 - Configurações + seletor de tema rápido (Dark / Light)
 - Painel Dev (logs internos)

Objetivo: refinar layout (cantos arredondados, sombras, top bar custom, paleta coesa)
sem depender dos módulos reais ainda.
Execute: python ui_prototipo.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import time
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

from PyQt6.QtCore import (
    Qt, QTimer, QSize, QAbstractTableModel, QModelIndex, QVariant
)
from PyQt6.QtGui import QColor, QPalette, QIcon, QPixmap, QPainter, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QGridLayout, QFrame, QProgressBar,
    QTableView, QFormLayout, QLineEdit, QSpinBox, QComboBox, QTextEdit,
    QMessageBox, QCheckBox, QGraphicsDropShadowEffect, QToolButton
)

# Pygame embutido (minigames) usando uma superfície integrada (conceitual)
import pygame

try:
    import numpy as np
except ImportError:
    class np:  # fallback mínimo
        @staticmethod
        def mean(arr):
            return sum(arr)/len(arr) if arr else 0
        @staticmethod
        def sqrt(x):
            return x ** 0.5
        @staticmethod
        def array(a):
            return a
        @staticmethod
        def corrcoef(a, b):
            return [[1, 0],[0,1]]

# ------------------ Dados simulados ------------------
SENSOR_NAMES_FLEX = [f"flex{i}" for i in range(1, 9)]
SENSOR_NAMES_FSR = [f"fsr{i}" for i in range(1, 5)]

@dataclass
class SensorState:
    name: str
    values: List[float] = field(default_factory=list)
    last_value: float = 0.0
    enabled: bool = True

@dataclass
class AppSession:
    id: str
    start_time: float
    patient: str = "Paciente Demo"
    notes: str = ""
    calibration_version: str = "v1"

# ------------------ Utilitário: garantir plugin Qt ------------------
def ensure_qt_platform():
    try:
        import PyQt6
        qt_plugins = Path(PyQt6.__file__).parent / "Qt6" / "plugins"
        platforms = qt_plugins / "platforms"
        if platforms.exists():
            cur = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH")
            if not cur or not Path(cur).exists() or "platforms" not in cur.lower():
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
    except Exception:
        pass

# ------------------ Componentes reutilizáveis ------------------
class StatusCard(QFrame):
    def __init__(self, title: str, initial: str = "--"):
        super().__init__()
        self.setObjectName("StatusCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        self.title_label = QLabel(title.upper())
        self.value_label = QLabel(initial)
        ft = self.title_label.font(); ft.setPointSize(10); ft.setBold(True); self.title_label.setFont(ft)
        fv = self.value_label.font(); fv.setPointSize(20); fv.setBold(True); self.value_label.setFont(fv)
        self.title_label.setProperty("class","card-title")
        self.value_label.setProperty("class","card-value")
        lay.addWidget(self.title_label)
        lay.addWidget(self.value_label)
        lay.addStretch()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22); shadow.setXOffset(0); shadow.setYOffset(4)
        shadow.setColor(QColor(0,0,0,160))
        self.setGraphicsEffect(shadow)
    def update_value(self, text: str):
        self.value_label.setText(text)

class MiniSparkline(QFrame):
    def __init__(self, max_points=60, color="#4caf50"):
        super().__init__()
        self.max_points = max_points
        self.values: List[float] = []
        self.color = color
        self.setMinimumHeight(50)
        self.setObjectName("Sparkline")
    def push(self, v: float):
        self.values.append(v)
        if len(self.values) > self.max_points:
            self.values.pop(0)
        self.update()
    def paintEvent(self, _):
        if not self.values:
            return
        from PyQt6.QtGui import QPainter, QPen, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width(); h = self.height()
        mx = max(self.values) or 1
        pts = []
        for i, val in enumerate(self.values):
            x = int(i * (w / (len(self.values)-1))) if len(self.values) > 1 else w//2
            y = h - int((val / mx) * (h - 10)) - 5
            pts.append((x,y))
        path = QPainterPath(); path.moveTo(*pts[0])
        for i in range(1, len(pts)):
            path.lineTo(*pts[i])
        pen = QPen(QColor(self.color)); pen.setWidth(2)
        p.setPen(pen); p.drawPath(path)

# ------------------ Módulos de Página ------------------
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(20)
        cards_row = QHBoxLayout(); cards_row.setSpacing(16)
        self.card_ble = StatusCard("BLE", "OFF")
        self.card_gonio = StatusCard("GONIÔMETRO", "N/D")
        self.card_calib = StatusCard("CALIBRAÇÃO", "--")
        self.card_session = StatusCard("SESSÃO", "INATIVA")
        for c in (self.card_ble,self.card_gonio,self.card_calib,self.card_session): cards_row.addWidget(c)
        lay.addLayout(cards_row)
        spark_row = QHBoxLayout(); spark_row.setSpacing(14)
        self.spark_flex = MiniSparkline(color="#7e57c2"); self.spark_fsr = MiniSparkline(color="#26c6da")
        spark_row.addWidget(self.spark_flex); spark_row.addWidget(self.spark_fsr)
        lay.addLayout(spark_row)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        lbl = QLabel("LOGS RECENTES"); lbl.setProperty("class","section-title")
        lay.addWidget(lbl); lay.addWidget(self.log_box); lay.addStretch()
    def append_log(self, msg: str):
        self.log_box.append(f"<span style='color:#6a7a89'>[{time.strftime('%H:%M:%S')}]</span> {msg}")

class SensorsPage(QWidget):
    def __init__(self, sensors: Dict[str, SensorState]):
        super().__init__(); self.sensors = sensors
        lay = QVBoxLayout(self); lay.setSpacing(18)
        header = QHBoxLayout(); lbl = QLabel("SENSORES ATIVOS"); lbl.setProperty("class","section-title")
        header.addWidget(lbl); header.addStretch(); lay.addLayout(header)
        filter_row = QHBoxLayout(); filter_row.setSpacing(6)
        self.checks: Dict[str, QCheckBox] = {}
        for name in sensors.keys():
            cb = QCheckBox(name); cb.setChecked(True); cb.stateChanged.connect(self.update_visible)
            filter_row.addWidget(cb); self.checks[name]=cb
        lay.addLayout(filter_row)
        grid = QGridLayout(); grid.setSpacing(18)
        self.plots: Dict[str, MiniSparkline] = {}
        palette_colors = ["#ffb74d","#29b6f6","#66bb6a","#ab47bc","#ef5350","#26c6da","#ffa726","#8d6e63"]
        row=col=0
        for i,name in enumerate(sensors.keys()):
            spark = MiniSparkline(color=palette_colors[i % len(palette_colors)])
            lab = QLabel(name.upper()); lab.setProperty("class","sensor-label")
            card = QFrame(); card.setObjectName("SensorCard")
            inner = QVBoxLayout(card); inner.setContentsMargins(12,12,12,12); inner.setSpacing(8)
            inner.addWidget(lab); inner.addWidget(spark)
            self.plots[name]=spark
            grid.addWidget(card,row,col)
            col+=1
            if col>=4: col=0; row+=1
        lay.addLayout(grid); lay.addStretch()
    def update_visible(self):
        for name, cb in self.checks.items(): self.plots[name].setVisible(cb.isChecked())
    def push_value(self, name: str, v: float):
        if name in self.plots: self.plots[name].push(v)

class CalibrationPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.stage_label = QLabel("Fluxo: Aguardando início")
        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        self.start_btn = QPushButton("Iniciar Calibração")
        self.start_btn.clicked.connect(self.start_flow)
        self.next_btn = QPushButton("Próximo Passo"); self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.next_step)
        self.steps = [
            "Posicionar sensores em repouso",
            "Flexionar até máximo confortável",
            "Retornar ao neutro",
            "Gerando curva...",
            "Concluído"
        ]
        self.current_step = -1
        for w in (self.stage_label,self.progress,self.start_btn,self.next_btn):
            layout.addWidget(w)
        layout.addStretch()
    def start_flow(self):
        self.current_step = 0
        self.update_ui()
        self.next_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
    def next_step(self):
        if self.current_step < len(self.steps)-1:
            self.current_step +=1
            self.update_ui()
        if self.current_step == len(self.steps)-1:
            self.next_btn.setEnabled(False)
    def update_ui(self):
        self.stage_label.setText(self.steps[self.current_step])
        self.progress.setValue(int((self.current_step+1)/len(self.steps)*100))

class TestsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.sensor_select = QComboBox(); self.sensor_select.addItems(SENSOR_NAMES_FLEX)
        self.record_btn = QPushButton("Gravar")
        self.stop_btn = QPushButton("Parar"); self.stop_btn.setEnabled(False)
        self.metrics_label = QLabel("MAE: -- | RMSE: -- | Corr: --")
        self.samples = []
        self.start_t = None
        self.record_btn.clicked.connect(self.start_record)
        self.stop_btn.clicked.connect(self.stop_record)
        for w in (QLabel("Teste de Sensor"), self.sensor_select, self.record_btn, self.stop_btn, self.metrics_label):
            layout.addWidget(w)
        layout.addStretch()
        self.timer = QTimer(); self.timer.timeout.connect(self.collect_sample)
    def start_record(self):
        self.samples=[]; self.start_t=time.time()
        self.record_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.timer.start(100)
    def stop_record(self):
        self.timer.stop(); self.record_btn.setEnabled(True); self.stop_btn.setEnabled(False)
    def collect_sample(self):
        t = time.time()-self.start_t
        flex = 30 + 10*math.sin(t*2)
        gonio = 30 + 10*math.sin(t*2 + 0.2)
        self.samples.append((t, flex, gonio))
        flex_arr = [s[1] for s in self.samples]
        gon_arr = [s[2] for s in self.samples]
        if len(self.samples)>2:
            mae = np.mean([abs(a-b) for a,b in zip(flex_arr,gon_arr)])
            rmse = np.sqrt(np.mean([(a-b)**2 for a,b in zip(flex_arr,gon_arr)]))
            # correlação simplificada
            try:
                corr = 0
                if len(flex_arr)>3:
                    fa = np.array(flex_arr); ga = np.array(gon_arr)
                    c = np.corrcoef(fa,ga)
                    corr = c[0][1]
            except Exception:
                corr=0
            self.metrics_label.setText(f"MAE: {mae:.2f} | RMSE: {rmse:.2f} | Corr: {corr:.2f}")

class GameCanvas(QWidget):
    def __init__(self, game_type: str = "pong"):
        super().__init__()
        self.game_type = game_type
        self.setMinimumSize(400,300)
        self.timer = QTimer(); self.timer.timeout.connect(self.game_loop)
        self.timer.start(30)
        self.init_game()
    def init_game(self):
        self.ball_x=50; self.ball_y=50; self.vx=4; self.vy=3
        self.phase=0
    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QBrush
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#000'))
        p.setPen(QPen(QColor('#4caf50')))
        if self.game_type == 'pong':
            p.setBrush(QBrush(QColor('#2196f3')))
            p.drawEllipse(int(self.ball_x), int(self.ball_y), 20,20)
        else:  # animação simples
            r = 50 + 30*math.sin(self.phase)
            p.setBrush(QBrush(QColor('#ff9800')))
            p.drawEllipse(self.width()//2 - int(r/2), self.height()//2 - int(r/2), int(r), int(r))
    def game_loop(self):
        if self.game_type=='pong':
            self.ball_x += self.vx; self.ball_y += self.vy
            if self.ball_x<0 or self.ball_x>self.width()-20: self.vx*=-1
            if self.ball_y<0 or self.ball_y>self.height()-20: self.vy*=-1
        else:
            self.phase += 0.1
        self.update()

class GamesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.selector = QComboBox(); self.selector.addItems(["Pong Simples","Pulso"])
        self.canvas_container = QVBoxLayout()
        self.current_canvas: Optional[GameCanvas]=None
        self.selector.currentIndexChanged.connect(self.switch_game)
        layout.addWidget(QLabel("Biblioteca de Jogos"))
        layout.addWidget(self.selector)
        canvas_host = QWidget(); canvas_host.setLayout(self.canvas_container)
        layout.addWidget(canvas_host)
        layout.addStretch()
        self.switch_game(0)
    def switch_game(self, idx:int):
        if self.current_canvas:
            w = self.current_canvas
            self.canvas_container.removeWidget(w); w.deleteLater()
        game_type = 'pong' if idx==0 else 'pulse'
        self.current_canvas = GameCanvas(game_type)
        self.canvas_container.addWidget(self.current_canvas)

class HistoryModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows = [
            {"id":"sess_001","inicio":"10:00","paciente":"Demo","tipo":"Teste","amostras":120},
            {"id":"sess_002","inicio":"10:05","paciente":"Demo","tipo":"Jogo","amostras":340},
        ]
    def rowCount(self, parent=QModelIndex()): return len(self.rows)
    def columnCount(self, parent=QModelIndex()): return 5
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return QVariant()
        cols = ["id","inicio","paciente","tipo","amostras"]
        if role==Qt.ItemDataRole.DisplayRole:
            return str(self.rows[index.row()][cols[index.column()]])
        return QVariant()
    def headerData(self, section, orientation, role):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:
            return ["ID","Início","Paciente","Tipo","Amostras"][section]
        return QVariant()

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Histórico de Sessões"))
        self.table = QTableView(); self.model = HistoryModel(); self.table.setModel(self.model)
        layout.addWidget(self.table)
        layout.addStretch()

class SettingsPage(QWidget):
    def __init__(self, on_theme_change: Callable[[str], None]):
        super().__init__()
        self._cb = on_theme_change
        form = QFormLayout(self)
        self.poll_spin = QSpinBox(); self.poll_spin.setRange(10,1000); self.poll_spin.setValue(50)
        self.render_spin = QSpinBox(); self.render_spin.setRange(10,1000); self.render_spin.setValue(100)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["Dark","Light"])
        self.theme_combo.currentTextChanged.connect(self._cb)
        form.addRow("Aquisição (ms)", self.poll_spin)
        form.addRow("Render (ms)", self.render_spin)
        form.addRow("Tema", self.theme_combo)
        form.addRow(QLabel("Protótipo – sem persistência ainda."))

class DevPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        layout.addWidget(QLabel("Painel de Diagnóstico"))
        layout.addWidget(self.log)
        layout.addStretch()
    def add_line(self, text: str):
        self.log.append(text)

# ------------------ Main Window ------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarmSoft Protótipo PyQt6 Moderno")
        self.resize(1500, 920)

        # Estado principal
        self.sensors: Dict[str, SensorState] = {n: SensorState(n) for n in SENSOR_NAMES_FLEX + SENSOR_NAMES_FSR}
        self.session: Optional[AppSession] = None
        self.current_theme = "Dark"
        self.sidebar_collapsed = False

        # Central widget & layout raiz
        central = QWidget(); self.setCentralWidget(central)
        main_v = QVBoxLayout(central); main_v.setContentsMargins(0,0,0,0); main_v.setSpacing(0)

        # Top Bar
        self.top_bar = QWidget(); self.top_bar.setObjectName("TopBar")
        top_lay = QHBoxLayout(self.top_bar); top_lay.setContentsMargins(14,8,14,8); top_lay.setSpacing(12)
        self.btn_toggle = QPushButton("☰"); self.btn_toggle.setObjectName("ToggleBtn"); self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        self.brand = QLabel("MarmSoft")
        self.session_badge = QLabel("Sessão: --"); self.session_badge.setProperty("class","badge")
        self.quick_theme = QComboBox(); self.quick_theme.addItems(["Dark","Light"]); self.quick_theme.currentTextChanged.connect(self.change_theme)
        top_lay.addWidget(self.btn_toggle)
        top_lay.addWidget(self.brand)
        top_lay.addStretch()
        top_lay.addWidget(self.session_badge)
        top_lay.addWidget(QLabel("Tema:"))
        top_lay.addWidget(self.quick_theme)
        main_v.addWidget(self.top_bar)

        # Body (sidebar + stack)
        body_h = QHBoxLayout(); body_h.setContentsMargins(18,18,18,18); body_h.setSpacing(20)

        # Sidebar list
        self.nav_list = QListWidget(); self.nav_list.setObjectName("Sidebar"); self.nav_list.setFixedWidth(230)
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        nav_specs = [
            ("Dashboard", "🏠"),
            ("Sensores", "🧪"),
            ("Calibração", "🛠"),
            ("Testes", "📊"),
            ("Jogos", "🎮"),
            ("Histórico", "🗂"),
            ("Config", "⚙"),
            ("Dev", "</>")
        ]
        for text, glyph in nav_specs:
            it = QListWidgetItem(text)
            it.setSizeHint(QSize(200,48))
            it.setIcon(self.make_icon(glyph))
            it.setData(Qt.ItemDataRole.UserRole, text)
            self.nav_list.addItem(it)

        # Stacked pages
        self.stack = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_sensors = SensorsPage(self.sensors)
        self.page_calib = CalibrationPage()
        self.page_tests = TestsPage()
        self.page_games = GamesPage()
        self.page_history = HistoryPage()
        self.page_settings = SettingsPage(self.change_theme)
        self.page_dev = DevPage()
        for p in [self.page_dashboard,self.page_sensors,self.page_calib,self.page_tests,self.page_games,self.page_history,self.page_settings,self.page_dev]:
            self.stack.addWidget(p)
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        body_h.addWidget(self.nav_list)
        body_h.addWidget(self.stack, 1)
        main_v.addLayout(body_h, 1)

        # Seleciona página inicial
        self.nav_list.setCurrentRow(0)

        # Timers de simulação / atualização
        self.sensor_timer = QTimer(self); self.sensor_timer.timeout.connect(self.simulate_sensors); self.sensor_timer.start(50)
        self.dashboard_timer = QTimer(self); self.dashboard_timer.timeout.connect(self.update_dashboard); self.dashboard_timer.start(1000)
    # Tests page updates metrics internally during recording; no periodic external timer needed

        # Log e BLE simulado
        self.fake_ble_connected = False
        QTimer.singleShot(1500, self.simulate_ble_connect)
        self.page_dashboard.append_log("Aplicação iniciada (simulada)")
        self.page_dev.add_line("[INFO] Protótipo carregado")

        # Estilo inicial
        self.apply_stylesheet()

    def apply_stylesheet(self):
        dark = {
            'bg': '#0e1116', 'top': 'rgba(20,24,30,0.85)', 'top_border': '#1f242b',
            'side_bg':'#161a21','side_border':'#232a33','side_item':'#b6c3cf','side_hover':'#212a33',
            'card_bg':'#1c222a','card_border':'#2a333d','sensor_bg':'#1a1f27','sensor_border':'#26313b',
            'text_edit_bg':'#161b22','text_edit_border':'#27313b','text':'#ffffff','muted':'#8b97a6',
            'badge_bg':'#4254b5','accent_a':'#3949ab','accent_b':'#5667c2','progress_a':'#3d4faa','progress_b':'#6073d3',
            'input_bg':'#161b22','input_border':'#28323c','checkbox_border':'#3a4652','checkbox_bg':'#182028','checkbox_border_sel':'#4f5d73','checkbox_bg_sel':'#3e51b5',
            'btn_bg':'#26313b','btn_border':'#32404c','btn_bg_hover':'#2e3a45','btn_bg_press':'#3a4753',
            'label_sensor':'#ffffff'
        }
        light = {
            'bg': '#f5f7fa', 'top': '#ffffff', 'top_border': '#d4dce4',
            'side_bg':'#ffffff','side_border':'#dbe2ec','side_item':'#4a5968','side_hover':'#e8f0fa',
            'card_bg':'#ffffff','card_border':'#d9e2ec','sensor_bg':'#ffffff','sensor_border':'#d3dde7',
            'text_edit_bg':'#ffffff','text_edit_border':'#d0dae4','text':'#1e2a33','muted':'#5a6b7a',
            'badge_bg':'#2f6dde','accent_a':'#2f6dde','accent_b':'#5c8ef0','progress_a':'#2f6dde','progress_b':'#5c8ef0',
            'input_bg':'#ffffff','input_border':'#c5d2dd','checkbox_border':'#8ca1b3','checkbox_bg':'#ffffff','checkbox_border_sel':'#2f6dde','checkbox_bg_sel':'#2f6dde',
            'btn_bg':'#eef3f8','btn_border':'#c9d6e2','btn_bg_hover':'#dfe9f3','btn_bg_press':'#cedae6',
            'label_sensor':'#1e2a33'
        }
        theme = dark if self.current_theme == 'Dark' else light
        qss = f"""
QMainWindow {{ background-color: {theme['bg']}; }}
#TopBar {{ background: {theme['top']}; border-bottom:1px solid {theme['top_border']}; }}
QToolButton {{ background: transparent; font-size:18px; padding:4px 10px; border:0; color:{theme['text']}; }}
QToolButton:hover {{ background: {theme['btn_bg_hover']}; border-radius:10px; }}
QListWidget#Sidebar {{ background:{theme['side_bg']}; border:1px solid {theme['side_border']}; border-radius:18px; padding:12px; }}
QListWidget#Sidebar::item {{ margin:4px 4px; padding:10px 14px; color:{theme['side_item']}; border-radius:12px; font-size:14px; }}
QListWidget#Sidebar::item:selected {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {theme['accent_a']}, stop:1 {theme['accent_b']}); color:#fff; }}
QListWidget#Sidebar::item:hover:!selected {{ background:{theme['side_hover']}; }}
QFrame#StatusCard {{ background:{theme['card_bg']}; border:1px solid {theme['card_border']}; border-radius:18px; }}
QFrame#SensorCard {{ background:{theme['sensor_bg']}; border:1px solid {theme['sensor_border']}; border-radius:14px; }}
QTextEdit {{ background:{theme['text_edit_bg']}; border:1px solid {theme['text_edit_border']}; border-radius:14px; color:{theme['text']}; padding:8px; }}
QProgressBar {{ background:{theme['sensor_bg']}; border:1px solid {theme['sensor_border']}; border-radius:10px; height:22px; color:{theme['text']}; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {theme['progress_a']}, stop:1 {theme['progress_b']}); border-radius:10px; }}
QLabel[class='card-title'] {{ color:{theme['muted']}; letter-spacing:1px; }}
QLabel[class='card-value'] {{ color:{theme['text']}; }}
QLabel[class='brand'] {{ font-size:18px; font-weight:600; color:{theme['text']}; }}
QLabel[class='badge'] {{ background:{theme['badge_bg']}; padding:4px 12px; border-radius:14px; color:#fff; font-size:12px; }}
QLabel[class='section-title'] {{ font-size:14px; font-weight:600; color:{theme['text']}; }}
QLabel[class='sensor-label'] {{ font-weight:600; color:{theme['label_sensor']}; }}
QComboBox, QSpinBox, QLineEdit {{ background:{theme['input_bg']}; border:1px solid {theme['input_border']}; border-radius:10px; padding:6px 10px; color:{theme['text']}; }}
QComboBox::drop-down {{ border:0; }}
QCheckBox {{ color:{theme['text']}; }}
QCheckBox::indicator {{ width:18px; height:18px; }}
QCheckBox::indicator:unchecked {{ border:1px solid {theme['checkbox_border']}; background:{theme['checkbox_bg']}; border-radius:5px; }}
QCheckBox::indicator:checked {{ border:1px solid {theme['checkbox_border_sel']}; background:{theme['checkbox_bg_sel']}; }}
QScrollBar:vertical {{ background:{theme['side_bg']}; width:10px; margin:4px; border-radius:5px; }}
QScrollBar::handle:vertical {{ background:{theme['card_border']}; border-radius:5px; min-height:40px; }}
QScrollBar::handle:vertical:hover {{ background:{theme['accent_a']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
QPushButton {{ background:{theme['btn_bg']}; border:1px solid {theme['btn_border']}; border-radius:12px; color:{theme['side_item'] if self.current_theme=='Light' else '#dde2e7'}; padding:8px 16px; font-weight:500; }}
QPushButton:hover {{ background:{theme['btn_bg_hover']}; }}
QPushButton:pressed {{ background:{theme['btn_bg_press']}; }}
"""
        self.setStyleSheet(qss)

    def make_icon(self, glyph: str) -> QIcon:
        pm = QPixmap(32,32); pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(); font.setPointSize(16); font.setBold(True)
        p.setFont(font)
        color = QColor('#6073d3') if self.current_theme=='Dark' else QColor('#2f6dde')
        p.setPen(color)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
        p.end()
        return QIcon(pm)

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.sidebar_collapsed:
            self.nav_list.setFixedWidth(72)
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                original = it.data(Qt.ItemDataRole.UserRole) or it.text()
                it.setData(Qt.ItemDataRole.UserRole, original)
                it.setText("")
                it.setToolTip(original)
        else:
            self.nav_list.setFixedWidth(230)
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                original = it.data(Qt.ItemDataRole.UserRole)
                if original:
                    it.setText(original)
                    it.setToolTip("")
        # update icons (color may change with theme)
        for i in range(self.nav_list.count()):
            it = self.nav_list.item(i)
            glyph = "?"
            original = it.data(Qt.ItemDataRole.UserRole) or ''
            # recover first char or if emoji left keep same; easier keep icon constant
            # we can't extract glyph from icon, so we rebuild based on stored label mapping
            mapping = {
                'Dashboard':'🏠','Sensores':'🧪','Calibração':'🛠','Testes':'📊','Jogos':'🎮','Histórico':'🗂','Config':'⚙','Dev':'</>'
            }
            glyph = mapping.get(original, '•')
            it.setIcon(self.make_icon(glyph))
        self.apply_stylesheet()

    def update_session_badge(self):
        self.session_badge.setText(f"Sessão: {self.session.id}" if self.session else "Sessão: --")

    def simulate_ble_connect(self):
        self.fake_ble_connected = True
        self.page_dashboard.card_ble.update_value("Conectado")
        self.page_dashboard.append_log("BLE conectado")

    def switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def start_session(self):
        if self.session:
            return
        sid = f"sess_{int(time.time())}"
        self.session = AppSession(id=sid, start_time=time.time())
        self.page_dashboard.card_session.update_value("ATIVA")
        self.update_session_badge()
        self.page_dashboard.append_log(f"Sessão {sid} iniciada")

    def simulate_sensors(self):
        t = time.time()
        for name, st in self.sensors.items():
            if name.startswith('flex'):
                v = 30 + 15*math.sin(t*2 + hash(name)%10)
            else:
                v = 5 + 3*math.sin(t*1.5 + hash(name)%7)
            st.last_value = v
            st.values.append(v)
            if len(st.values)>500: st.values.pop(0)
            # Atualiza plots se página sensores visível
            self.page_sensors.push_value(name, v)
        # Atualiza sparklines principais
        avg_flex = sum(self.sensors[n].last_value for n in self.sensors if n.startswith('flex'))/len(SENSOR_NAMES_FLEX)
        avg_fsr = sum(self.sensors[n].last_value for n in self.sensors if n.startswith('fsr'))/len(SENSOR_NAMES_FSR)
        self.page_dashboard.spark_flex.push(avg_flex)
        self.page_dashboard.spark_fsr.push(avg_fsr)

    def update_dashboard(self):
        if not self.session:
            # autoinicia sessão para demonstração
            self.start_session()
        self.page_dashboard.card_calib.update_value("v1 (simulada)")
        self.page_dashboard.card_gonio.update_value("OK")

    # ------------------ Temas ------------------
    def change_theme(self, theme: str):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        app = QApplication.instance()
        pal = app.palette()
        if theme == "Dark":
            pal.setColor(QPalette.ColorRole.Window, QColor('#121212'))
            pal.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
            pal.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
            pal.setColor(QPalette.ColorRole.Text, QColor('#dddddd'))
            pal.setColor(QPalette.ColorRole.Button, QColor('#333333'))
            pal.setColor(QPalette.ColorRole.ButtonText, QColor('#ffffff'))
        else:  # Light
            pal.setColor(QPalette.ColorRole.Window, QColor('#f5f7fa'))
            pal.setColor(QPalette.ColorRole.WindowText, QColor('#1e2a33'))
            pal.setColor(QPalette.ColorRole.Base, QColor('#ffffff'))
            pal.setColor(QPalette.ColorRole.Text, QColor('#1e2a33'))
            pal.setColor(QPalette.ColorRole.Button, QColor('#eef3f8'))
            pal.setColor(QPalette.ColorRole.ButtonText, QColor('#1e2a33'))
        app.setPalette(pal)
        # Ajuste de stylesheet para alguns componentes (exemplo simples)
        # (Simplificado) Poderíamos variar QSS por tema; por agora mantemos base dark e apenas
        # ajustamos palette para Light / High Contrast.
        if hasattr(self.page_settings, 'theme_combo') and self.page_settings.theme_combo.currentText() != theme:
            self.page_settings.theme_combo.blockSignals(True)
            self.page_settings.theme_combo.setCurrentText(theme)
            self.page_settings.theme_combo.blockSignals(False)
        if hasattr(self, 'quick_theme') and self.quick_theme.currentText() != theme:
            self.quick_theme.blockSignals(True)
            self.quick_theme.setCurrentText(theme)
            self.quick_theme.blockSignals(False)
        # Recria ícones (cores podem mudar)
        for i in range(self.nav_list.count()):
            it = self.nav_list.item(i)
            label = it.data(Qt.ItemDataRole.UserRole) or ''
            mapping = {
                'Dashboard':'🏠','Sensores':'🧪','Calibração':'🛠','Testes':'📊','Jogos':'🎮','Histórico':'🗂','Config':'⚙','Dev':'</>'
            }
            it.setIcon(self.make_icon(mapping.get(label,'•')))
        self.apply_stylesheet()
        self.page_dashboard.append_log(f"Tema alterado para: {theme}")

    def closeEvent(self, event):
        if QMessageBox.question(self, "Sair", "Deseja realmente sair?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
            event.ignore()
        else:
            event.accept()

# ------------------ Execução ------------------
def main():
    ensure_qt_platform()
    app = QApplication(sys.argv)
    # Tema dark básico
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor('#121212'))
    pal.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
    pal.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
    pal.setColor(QPalette.ColorRole.Text, QColor('#dddddd'))
    app.setPalette(pal)

    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
