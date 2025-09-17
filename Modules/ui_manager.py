"""
Interface principal MarmSoft em PyQt6.

Inclui:
 - Navegação lateral
 - Dashboard com cartões, sparklines e logs
 - Monitor de sensores (cartões, unificado, modo clássico Matplotlib)
 - Placeholders de Calibração e Testes
 - Integração FlyBird
 - Histórico / Config (Tema, BLE, Suavização) / Painel Dev

Execução direta de teste:
    python -m Modules.ui_manager
ou via entry point principal:
    python main.py
"""
# ================== Imports & Modelos Básicos (restaurados) ==================
from __future__ import annotations

import sys, os, math, time, random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

import numpy as np

from PyQt6.QtCore import Qt, QTimer, QSize, QModelIndex, QVariant, QAbstractTableModel, QSortFilterProxyModel, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTextEdit, QLabel, QFrame, QGraphicsDropShadowEffect, QToolButton, QCheckBox,
    QProgressBar, QPushButton, QComboBox, QSpinBox, QFormLayout, QLineEdit,
    QTableView, QListWidget, QListWidgetItem, QMessageBox, QStackedWidget, QSlider
)
import json


# ------------------ Dataclasses ------------------
@dataclass
class SensorState:
    name: str
    last_value: float = 0.0
    values: List[float] = field(default_factory=list)

@dataclass
class AppSession:
    id: str
    start_time: float

@dataclass
class Patient:
    id: str
    nome: str
    idade: int
    sexo: str
    condicao: str
    fisio: str
    registro_fisio: str


# ------------------ Constantes / Mock ------------------
SENSOR_NAMES_FLEX = [f"flex{i}" for i in range(1,9)]
SENSOR_NAMES_FSR  = [f"fsr{i}" for i in range(1,5)]
GONIOMETRO_NAME = "goniometro"

MOCK_PATIENTS: List[Patient] = [
    Patient("P001","Ana Silva",29,"F","Pós-operatório joelho","Dr. Souza","CREFITO 1234"),
    Patient("P002","João Lima",41,"M","Reabilitação ombro","Dr. Souza","CREFITO 1234"),
]


def ensure_qt_platform():
    # Em alguns ambientes Windows/CI pode ser necessário ajustar a plataforma.
    if os.environ.get("QT_QPA_PLATFORM") in (None,""):
        # Mantemos padrão; poderia forçar 'windows' ou 'offscreen' se preciso.
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
        # Renomeado para Bluetooth
        self.card_ble = StatusCard("Bluetooth", "OFF")
        self.card_gonio = StatusCard("GONIÔMETRO", "N/D")
        self.card_calib = StatusCard("CALIBRAÇÃO", "--")
        self.card_session = StatusCard("SESSÃO", "INATIVA")
        for c in (self.card_ble,self.card_gonio,self.card_calib,self.card_session): cards_row.addWidget(c)
        lay.addLayout(cards_row)
        spark_row = QHBoxLayout(); spark_row.setSpacing(14)
        self.spark_flex = MiniSparkline(color="#7e57c2"); self.spark_fsr = MiniSparkline(color="#26c6da")
        spark_row.addWidget(self.spark_flex); spark_row.addWidget(self.spark_fsr)
        lay.addLayout(spark_row)
        lay.addStretch()
    def append_log(self, msg: str):
        pass

class SensorsPage(QWidget):
    # Página de sensores com dois modos: Cartões ou Unificado.
    # Agora com toggle segmentado, lista de seleção de sinais e sensor adicional goniômetro.
    def __init__(self, sensors: Dict[str, SensorState]):
        super().__init__(); self.sensors = sensors
        from PyQt6.QtWidgets import QCheckBox  # garante escopo local antes do uso
        # Modos restantes: 'cartoes' e 'unificado' (plot consolidado antigo)
        self.mode = 'unificado'
        # Conjunto de nomes habilitados (para modo unificado)
        # Ajuste: deixar 'flex8' desmarcado/inativo por padrão (solicitação usuário)
        self.enabled_names = {n for n in sensors.keys() if n != 'flex8'}
        main_lay = QVBoxLayout(self); main_lay.setSpacing(14)

        # Header: Título + linha com toggle segmentado e opções
        lbl = QLabel("SENSORES"); lbl.setProperty("class","section-title")
        main_lay.addWidget(lbl)

        seg_row = QHBoxLayout(); seg_row.setSpacing(16)
        # Segmented principal (visualização)
        self.segmented = QFrame(); self.segmented.setObjectName("Segmented")
        seg_lay = QHBoxLayout(self.segmented); seg_lay.setContentsMargins(4,4,4,4); seg_lay.setSpacing(2)
        # Botões: Cartões e Unificado (antigo plot)
        self.btn_seg_cartoes = QPushButton("Cartões"); self.btn_seg_unificado_plot = QPushButton("Unificado")
        for b in (self.btn_seg_cartoes, self.btn_seg_unificado_plot):
            b.setCheckable(True); b.clicked.connect(self._segmented_clicked)
        # Iniciar no modo Unificado (plot)
        self.btn_seg_unificado_plot.setChecked(True); self.btn_seg_unificado_plot.setProperty('selected','true')
        self.btn_seg_cartoes.setProperty('selected','false')
        seg_lay.addWidget(self.btn_seg_unificado_plot); seg_lay.addWidget(self.btn_seg_cartoes)

        # Segmented secundário (modo flex/fsr do plot antigo)
        self.segmented_old_mode = QFrame(); self.segmented_old_mode.setObjectName("Segmented")
        old_lay = QHBoxLayout(self.segmented_old_mode); old_lay.setContentsMargins(4,4,4,4); old_lay.setSpacing(2)
        self.btn_old_flex = QPushButton("Flex"); self.btn_old_fsr = QPushButton("FSR")
        for b in (self.btn_old_flex, self.btn_old_fsr):
            b.setCheckable(True); b.clicked.connect(self._old_mode_segment_clicked)
        self.btn_old_flex.setChecked(True); self.btn_old_flex.setProperty("selected","true")
        self.btn_old_fsr.setProperty("selected","false")
        old_lay.addWidget(self.btn_old_flex); old_lay.addWidget(self.btn_old_fsr)
        self.segmented_old_mode.setVisible(False)

        seg_row.addWidget(self.segmented, 0)
        seg_row.addWidget(self.segmented_old_mode, 0)
        seg_row.addStretch()

    # Grupo opções modo unificado (ex-antigo) – legenda / tensão
        self.old_mode_opts = QFrame(); self.old_mode_opts.setObjectName('OldModeOpts')
        omo_lay = QHBoxLayout(self.old_mode_opts); omo_lay.setContentsMargins(0,0,0,0); omo_lay.setSpacing(10)
        self.chk_old_legend = QCheckBox("Legenda"); self.chk_old_legend.setChecked(True); self.chk_old_legend.setProperty('class','pretty')
        self.chk_old_voltage = QCheckBox("Tensão"); self.chk_old_voltage.setChecked(True); self.chk_old_voltage.setProperty('class','pretty')
        self.chk_old_legend.stateChanged.connect(self._old_toggle_legend)
        self.chk_old_voltage.stateChanged.connect(self._old_toggle_voltage)
        omo_lay.addWidget(self.chk_old_legend); omo_lay.addWidget(self.chk_old_voltage)
        self.old_mode_opts.setVisible(False)
        seg_row.addWidget(self.old_mode_opts, 0, Qt.AlignmentFlag.AlignRight)
        main_lay.addLayout(seg_row)

        from PyQt6.QtWidgets import QStackedWidget, QScrollArea
        self.mode_stack = QStackedWidget(); main_lay.addWidget(self.mode_stack, 1)

        # --- Página Cartões ---
        page_cards = QWidget(); cards_lay = QVBoxLayout(page_cards); cards_lay.setSpacing(10)
        # Filtros
        filter_row = QHBoxLayout(); filter_row.setSpacing(6)
        self.checks: Dict[str, QCheckBox] = {}
        for name in sensors.keys():
            cb = QCheckBox(name)
            # flex8 inicia desmarcado
            cb.setChecked(False if name == 'flex8' else True)
            cb.stateChanged.connect(self.update_visible)
            filter_row.addWidget(cb); self.checks[name]=cb
        filter_row.addStretch(); cards_lay.addLayout(filter_row)
        # Grupos Flex / FSR
        self.plots: Dict[str, MiniSparkline] = {}
        palette_colors = ["#ffb74d","#29b6f6","#66bb6a","#ab47bc","#ef5350","#26c6da","#ffa726","#8d6e63"]

        def build_group(title: str, names: List[str]):
            cards_lay.addWidget(QLabel(title))
            grid = QGridLayout(); grid.setSpacing(18)
            row=col=0
            for i,name in enumerate(names):
                spark = MiniSparkline(color=palette_colors[i % len(palette_colors)])
                lab = QLabel(name.upper()); lab.setProperty("class","sensor-label")
                card = QFrame(); card.setObjectName("SensorCard")
                inner = QVBoxLayout(card); inner.setContentsMargins(12,12,12,12); inner.setSpacing(8)
                inner.addWidget(lab); inner.addWidget(spark)
                self.plots[name]=spark
                grid.addWidget(card,row,col)
                col+=1
                if col>=4: col=0; row+=1
            cards_lay.addLayout(grid)

        build_group("Flex Sensors", [n for n in sensors if n.startswith('flex')])
        build_group("FSR Sensors", [n for n in sensors if n.startswith('fsr')])
        # Card separado goniômetro
        if GONIOMETRO_NAME in sensors:
            cards_lay.addWidget(QLabel("Goniômetro"))
            ggrid = QGridLayout(); ggrid.setSpacing(18)
            spark = MiniSparkline(color="#ffffff")
            lab = QLabel("GONIÔMETRO"); lab.setProperty("class","sensor-label")
            card = QFrame(); card.setObjectName("SensorCard")
            inner = QVBoxLayout(card); inner.setContentsMargins(12,12,12,12); inner.setSpacing(8)
            inner.addWidget(lab); inner.addWidget(spark)
            self.plots[GONIOMETRO_NAME] = spark
            ggrid.addWidget(card,0,0)
            cards_lay.addLayout(ggrid)
        cards_lay.addStretch()
        self.mode_stack.addWidget(page_cards)

        # (Página unificada antiga removida)

    # --- Página Unificado (plot antigo Matplotlib) ---
        page_old = QWidget(); old_lay = QVBoxLayout(page_old); old_lay.setContentsMargins(0,0,0,0)
        from Modules.plot_manager import PlotManager  # import local para evitar custos se não usar
        self.old_plot_container = QFrame(); old_plot_layout = QVBoxLayout(self.old_plot_container); old_plot_layout.setContentsMargins(0,0,0,0)
        old_lay.addWidget(self.old_plot_container,1)
        # Checkboxes de seleção de sinais agora abaixo do gráfico (container dedicado)
        sel_wrap = QFrame(); sel_wrap.setObjectName('UnifiedChecksBar')
        sel_wrap.setStyleSheet('#UnifiedChecksBar { border-top: 1px solid rgba(255,255,255,40); padding: 6px 8px; }')
        sel_row = QHBoxLayout(sel_wrap); sel_row.setContentsMargins(4,4,4,4); sel_row.setSpacing(10)
        from PyQt6.QtWidgets import QCheckBox as _QCB2
        self.old_checks = {}
        gchk = _QCB2('goniometer'); gchk.setChecked(True); gchk.setProperty('class','pretty'); sel_row.addWidget(gchk); self.old_checks['goniometer']=gchk
        for sid in sorted([k for k in sensors.keys() if not k.startswith('goniometro')]):
            c = _QCB2(sid)
            c.setChecked(False if sid == 'flex8' else True)
            c.setProperty('class','pretty'); sel_row.addWidget(c); self.old_checks[sid]=c
        sel_row.addStretch(); old_lay.addWidget(sel_wrap)
        # Renomeado: old_plot -> unified_plot
        self.unified_plot = PlotManager(
            self.old_plot_container,
            sensors={k: v for k, v in sensors.items() if not k.startswith('goniometro')},
            # 'flex8' inicia oculto
            displayed_sensors=set(['goniometer'] + [k for k in sensors.keys() if k != 'flex8'])
        )
        # Alias de compatibilidade temporário (caso outras partes externas ainda usem old_plot)
        self.old_plot = self.unified_plot
        def _old_update_checks():
            displayed = {k for k, cb in self.old_checks.items() if cb.isChecked()}
            self.unified_plot.update_displayed_sensors(displayed)
        for cb in self.old_checks.values():
            cb.stateChanged.connect(_old_update_checks)
        self.mode_stack.addWidget(page_old)
        # Agora só duas páginas: 0=cartões, 1=unificado (plot)
        self.mode_stack.setCurrentIndex(1)
        # Exibe imediatamente os toggles Flex/FSR e opções quando iniciamos em modo unificado
        self.segmented_old_mode.setVisible(True)
        self.old_mode_opts.setVisible(True)

    def _old_toggle_legend(self):
        if hasattr(self, 'unified_plot'):
            self.unified_plot.set_show_legend(self.chk_old_legend.isChecked())

    def _old_toggle_voltage(self):
        if hasattr(self, 'unified_plot'):
            self.unified_plot.set_show_voltage(self.chk_old_voltage.isChecked())
        # Nada mais aqui; código de inicialização removido

    def _old_set_mode(self, mode: str):
        if hasattr(self,'unified_plot'):
            self.unified_plot.set_mode(mode)
        self._old_mode_cached = mode
        if hasattr(self,'btn_old_flex'):
            if mode == 'flex':
                self.btn_old_flex.setChecked(True); self.btn_old_fsr.setChecked(False)
                self.btn_old_flex.setProperty('selected','true'); self.btn_old_fsr.setProperty('selected','false')
            else:
                self.btn_old_flex.setChecked(False); self.btn_old_fsr.setChecked(True)
                self.btn_old_flex.setProperty('selected','false'); self.btn_old_fsr.setProperty('selected','true')
            for b in (self.btn_old_flex, self.btn_old_fsr):
                b.style().unpolish(b); b.style().polish(b); b.update()

    def _old_mode_segment_clicked(self):
        sender = self.sender()
        if sender == self.btn_old_flex:
            self._old_set_mode('flex')
        else:
            self._old_set_mode('fsr')

    def toggle_mode(self):
        # Usado se ainda houver chamadas externas
        self._set_mode('unificado' if self.mode=='cartoes' else 'cartoes')

    # (Funções de plot unificado removidas)

    def update_visible(self):
        for name, cb in self.checks.items():
            if name in self.plots:
                self.plots[name].setVisible(cb.isChecked())

    def push_value(self, name: str, v: float):
        if name in self.plots:
            self.plots[name].push(v)

    def _segmented_clicked(self):
        sender = self.sender()
        if sender == self.btn_seg_unificado_plot:
            self._set_mode('unificado')
        elif sender == self.btn_seg_cartoes:
            self._set_mode('cartoes')

    def _set_mode(self, target: str):
        if target == self.mode:
            return
        self.mode = target
        if self.mode == 'unificado':
            self.mode_stack.setCurrentIndex(1)
            self.segmented_old_mode.setVisible(True)
            self.old_mode_opts.setVisible(True)
            self.btn_seg_unificado_plot.setChecked(True); self.btn_seg_cartoes.setChecked(False)
            self.btn_seg_unificado_plot.setProperty('selected','true'); self.btn_seg_cartoes.setProperty('selected','false')
        else:
            self.mode_stack.setCurrentIndex(0)
            self.segmented_old_mode.setVisible(False)
            self.old_mode_opts.setVisible(False)
            self.btn_seg_unificado_plot.setChecked(False); self.btn_seg_cartoes.setChecked(True)
            self.btn_seg_unificado_plot.setProperty('selected','false'); self.btn_seg_cartoes.setProperty('selected','true')
        for b in (self.btn_seg_unificado_plot, self.btn_seg_cartoes):
            b.style().unpolish(b); b.style().polish(b); b.update()
        self.update()

    def update_unified_plot(self, current_time: float, latest_readings: dict):
        if self.mode == 'unificado' and hasattr(self,'unified_plot'):
            try:
                mode_txt = getattr(self, '_old_mode_cached', 'flex')
                self.unified_plot.set_mode(mode_txt)
                self.unified_plot.update(current_time, latest_readings)
            except RuntimeError:
                pass

class MultiSensorPlot(QWidget):
    # Plot multi-sensores simples com filtragem dinâmica por conjunto habilitado.
    def __init__(self, names: List[str], sensors: Dict[str, SensorState], title: str, color_seed: str, enabled_names: Optional[set]=None):
        super().__init__(); self.names = names; self.sensors = sensors; self.title = title; self.color_seed = color_seed; self.enabled_names_ref = enabled_names
        self.setMinimumHeight(440)  # altura dobrada
    def paintEvent(self, _):
        if not self.names:
            return
        from PyQt6.QtGui import QPainter, QPen, QFont
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        p.fillRect(rect, QColor(0,0,0,20))
        ft = QFont(); ft.setPointSize(11); ft.setBold(True); p.setFont(ft)
        p.setPen(QColor('#ffffff'))
        p.drawText(14,20,self.title)
        margin_l, margin_r, margin_t, margin_b = 50, 14, 30, 30
        x0 = rect.left()+margin_l; y0 = rect.bottom()-margin_b
        w = rect.width()-margin_l-margin_r; h = rect.height()-margin_t-margin_b
        p.setPen(QPen(QColor(255,255,255,60),1))
        p.drawRect(x0, rect.top()+margin_t, w, h)
        base_colors = ["#ffb74d","#29b6f6","#66bb6a","#ab47bc","#ef5350","#26c6da","#ffa726","#8d6e63"]
        visible_names = [n for n in self.names if (self.enabled_names_ref is None or n in self.enabled_names_ref)]
        for idx, name in enumerate(visible_names):
            data = self.sensors[name].values[-200:]
            if not data:
                continue
            mx = max(data) or 1
            pts = []
            for i,val in enumerate(data):
                x = x0 + int(i*(w/max(1,len(data)-1)))
                y = y0 - int((val/mx)*(h-4))
                pts.append((x,y))
            pen = QPen(QColor(base_colors[idx % len(base_colors)]),2)
            p.setPen(pen)
            for i in range(1,len(pts)):
                p.drawLine(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1])
            if pts:
                p.setPen(QPen(QColor(base_colors[idx % len(base_colors)])))
                p.drawText(pts[-1][0]-20, pts[-1][1]-6, name)


class CalibrationPage(QWidget):
    """Página de Calibração: replica visual do plot unificado (flex/fsr) porém focada em um sensor de cada vez.

    Requisitos implementados:
    - Toggle Flex/FSR
    - Combo de seleção de sensor (apenas 1 ativo). Para Flex, sempre inclui goniômetro no subplot de ângulo.
    - Uso de PlotManager reduzindo displayed_sensors ao sensor selecionado + goniômetro (flex) ou sensor fsr.
    - Botões: Iniciar Gravação, Parar, Calibrar (somente flex funcional). FSR ainda não grava.
    - Salvamento CSV em calibrations/flex/calibration_<sensor>.csv (Voltage,Angle) e reaplicação imediata.
    """
    def __init__(self, sensors: Dict[str, SensorState], sensor_backend: Dict[str, object], latest_readings: dict, theme_accessor: callable):
        super().__init__()
        self.sensors = sensors
        self.sensor_backend = sensor_backend
        self.latest_readings = latest_readings
        self._get_theme = theme_accessor  # função que retorna tema atual 'Dark'/'Light'
        from Modules.plot_manager import PlotManager
        outer = QVBoxLayout(self); outer.setSpacing(12)

        # Header controles (toggle segmentado + combo)
        ctrl_bar = QHBoxLayout(); ctrl_bar.setSpacing(12)
        self.segmented_mode = QFrame(); self.segmented_mode.setObjectName('Segmented')
        seg_lay = QHBoxLayout(self.segmented_mode); seg_lay.setContentsMargins(4,4,4,4); seg_lay.setSpacing(2)
        self.mode_toggle_flex = QPushButton("Flex"); self.mode_toggle_fsr = QPushButton("FSR")
        for b in (self.mode_toggle_flex, self.mode_toggle_fsr):
            b.setCheckable(True); b.clicked.connect(self._mode_clicked)
        self.mode_toggle_flex.setChecked(True)
        self.mode_toggle_flex.setProperty('selected','true')
        self.mode_toggle_fsr.setProperty('selected','false')
        seg_lay.addWidget(self.mode_toggle_flex); seg_lay.addWidget(self.mode_toggle_fsr)
        ctrl_bar.addWidget(self.segmented_mode)
        ctrl_bar.addSpacing(10)

        self.combo_sensor = QComboBox(); ctrl_bar.addWidget(QLabel("Sensor:")); ctrl_bar.addWidget(self.combo_sensor)

        ctrl_bar.addStretch()
        outer.addLayout(ctrl_bar)

        # Container plot
        self.plot_frame = QFrame(); self.plot_frame.setObjectName('CalibPlotFrame')
        self.plot_frame.setMinimumHeight(380)
        outer.addWidget(self.plot_frame, 1)

        # Instancia PlotManager com os sensores relevantes (todos para reaproveitar legendas/cores)
        self.calib_plot = PlotManager(self.plot_frame, sensors={k: v for k,v in sensors.items() if not k.startswith('goniometro')}, displayed_sensors=set())
        self.calib_plot.set_show_legend(True)
        self.calib_plot.set_show_voltage(True)
        self.calib_plot.set_mode('flex')

        # Botões calibração
        btn_row = QHBoxLayout(); btn_row.setSpacing(12)
        self.btn_start = QPushButton("Iniciar Gravação")
        self.btn_stop = QPushButton("Parar")
        self.btn_save = QPushButton("Calibrar")
        # Labels contador (tempo e amostras) - lógica preenchida posteriormente
        self.lbl_time = QLabel("Tempo: 0.0s")
        self.lbl_samples = QLabel("Amostras: 0")
        self.lbl_time.setMinimumWidth(90); self.lbl_samples.setMinimumWidth(110)
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(False)
        for b in (self.btn_start,self.btn_stop,self.btn_save):
            b.setProperty('class','action')
        self.btn_start.clicked.connect(self.start_record)
        self.btn_stop.clicked.connect(self.stop_record)
        self.btn_save.clicked.connect(self.save_calibration)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        btn_row.addWidget(self.lbl_time)
        btn_row.addWidget(self.lbl_samples)
        outer.addLayout(btn_row)

        # Estado
        self.recording = False
        self.record_points: List[tuple] = []
        self.record_timer = QTimer(self); self.record_timer.timeout.connect(self._collect_point)
        self.record_start_time = None

        self._populate_combo()
        self._apply_display_selection()
        # Aplicar tema atual
        self.apply_theme(self._get_theme())

    def _populate_combo(self):
        self.combo_sensor.blockSignals(True)
        self.combo_sensor.clear()
        if self.is_flex_mode():
            flex_names = sorted([n for n in self.sensors.keys() if n.startswith('flex')])
            self.combo_sensor.addItems(flex_names)
        else:
            fsr_names = sorted([n for n in self.sensors.keys() if n.startswith('fsr')])
            self.combo_sensor.addItems(fsr_names)
        self.combo_sensor.blockSignals(False)
        self.combo_sensor.currentIndexChanged.connect(self._apply_display_selection)

    def _mode_clicked(self):
        if self.sender() == self.mode_toggle_flex:
            self.mode_toggle_flex.setChecked(True); self.mode_toggle_fsr.setChecked(False)
            self.mode_toggle_flex.setProperty('selected','true'); self.mode_toggle_fsr.setProperty('selected','false')
            self.calib_plot.set_mode('flex')
        else:
            self.mode_toggle_flex.setChecked(False); self.mode_toggle_fsr.setChecked(True)
            self.mode_toggle_flex.setProperty('selected','false'); self.mode_toggle_fsr.setProperty('selected','true')
            self.calib_plot.set_mode('fsr')
        for b in (self.mode_toggle_flex,self.mode_toggle_fsr):
            b.style().unpolish(b); b.style().polish(b); b.update()
        self._populate_combo()
        self._apply_display_selection()
        self.apply_theme(self._get_theme())

    def is_flex_mode(self):
        return self.mode_toggle_flex.isChecked()

    def _apply_display_selection(self):
        if self.combo_sensor.count()==0:
            return
        sel = self.combo_sensor.currentText()
        if self.is_flex_mode():
            displayed = {sel, 'goniometer'}
        else:
            displayed = {sel}
        self.calib_plot.update_displayed_sensors(displayed)

    def start_record(self):
        if not self.is_flex_mode():
            # gravação só para flex no momento
            return
        if self.combo_sensor.count()==0:
            return
        self.record_points.clear()
        self.recording = True
        self.record_start_time = time.time()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.lbl_time.setText("Tempo: 0.0s")
        self.lbl_samples.setText("Amostras: 0")
        self.record_timer.start(50)  # 20 Hz

    def stop_record(self):
        if not self.recording:
            return
        self.recording = False
        self.record_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(len(self.record_points) > 5)
        # Congela contador final
        if self.record_start_time:
            elapsed = time.time() - self.record_start_time
            self.lbl_time.setText(f"Tempo: {elapsed:.1f}s")
        self.lbl_samples.setText(f"Amostras: {len(self.record_points)}")

    def _collect_point(self):
        if not self.recording:
            return
        sel = self.combo_sensor.currentText()
        voltage = self.latest_readings.get(f"{sel}_voltage", 0.0)
        angle = self.latest_readings.get('goniometer_angle', 0.0)
        self.record_points.append((voltage, angle))
        # Atualiza contadores
        if self.record_start_time:
            elapsed = time.time() - self.record_start_time
            self.lbl_time.setText(f"Tempo: {elapsed:.1f}s")
        self.lbl_samples.setText(f"Amostras: {len(self.record_points)}")

    def update_live_plot(self, current_time: float):
        """Atualiza o plot de calibração com as leituras mais recentes compartilhadas.

        Reutiliza a lógica do PlotManager como no modo unificado.
        """
        if not hasattr(self, 'calib_plot'):
            return
        try:
            # Garante modo correto conforme toggle
            self.calib_plot.set_mode('flex' if self.is_flex_mode() else 'fsr')
            self.calib_plot.update(current_time, self.latest_readings)
        except RuntimeError:
            pass

    def save_calibration(self):
        if not self.record_points:
            return
        sel = self.combo_sensor.currentText()
        # Ordena por ângulo crescente antes de ajustar
        ordered = sorted(self.record_points, key=lambda x: x[1])
        # Salva
        import os, csv
        os.makedirs('calibrations/flex', exist_ok=True)
        path = f"calibrations/flex/calibration_{sel}.csv"
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Voltage','Angle'])
            w.writerows(ordered)
        # Aplica no backend
        if sel in self.sensor_backend:
            self.sensor_backend[sel].calibrate_with_data_points(ordered)
        self.btn_save.setEnabled(False)
        self.btn_start.setEnabled(True)

    def apply_theme(self, theme: str):
        # Repassa para plot
        if hasattr(self, 'calib_plot'):
            self.calib_plot.apply_theme(theme)
        # Ajusta seleção
        fg_sel = '#ffffff' if theme=='Dark' else '#1e1e1e'
        for b in (self.mode_toggle_flex,self.mode_toggle_fsr):
            if b.property('selected')=='true':
                b.setStyleSheet('font-weight:600;')
            else:
                b.setStyleSheet('')
        self.update()

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
    def __init__(self, launch_flybird: Callable[[],None]):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Jogos"))
        btn = QPushButton("FlyBird")
        btn.clicked.connect(launch_flybird)
        lay.addWidget(btn)
        lay.addStretch()

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

class PatientsTableModel(QAbstractTableModel):
    headers = ["ID","Nome","Idade","Sexo","Condição","Fisioterapeuta","Registro"]
    def __init__(self, patients: List[Patient]):
        super().__init__(); self.patients = patients
    def rowCount(self, parent=QModelIndex()): return len(self.patients)
    def columnCount(self, parent=QModelIndex()): return len(self.headers)
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return QVariant()
        p = self.patients[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return [p.id,p.nome,str(p.idade),p.sexo,p.condicao,p.fisio,p.registro_fisio][index.column()]
        return QVariant()
    def headerData(self, section, orientation, role):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:
            return self.headers[section]
        return QVariant()
    def patient_at(self, row: int) -> Optional[Patient]:
        if 0 <= row < len(self.patients):
            return self.patients[row]
        return None

class PatientsFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.filter_text = ""; self.fisio_filter = "Todos"; self.cond_filter = "Todos"; self.sexo_filter = "Todos"
    def set_filters(self, text: str, fisio: str, cond: str, sexo: str):
        self.filter_text = text.lower().strip()
        self.fisio_filter = fisio
        self.cond_filter = cond
        self.sexo_filter = sexo
        self.invalidateFilter()
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: PatientsTableModel = self.sourceModel()  # type: ignore
        p = model.patient_at(source_row)
        if p is None: return False
        # Texto livre: nome, condição, fisio, registro
        if self.filter_text:
            blob = f"{p.nome} {p.condicao} {p.fisio} {p.registro_fisio}".lower()
            if self.filter_text not in blob:
                return False
        if self.fisio_filter != "Todos" and p.fisio != self.fisio_filter:
            return False
        if self.cond_filter != "Todos" and p.condicao != self.cond_filter:
            return False
        if self.sexo_filter != "Todos" and p.sexo != self.sexo_filter:
            return False
        return True

class PatientsPage(QWidget):
    def __init__(self, patients: List[Patient]):
        super().__init__()
        from PyQt6.QtWidgets import QHeaderView
        self._patients = patients
        lay = QVBoxLayout(self); lay.setSpacing(14)
        title = QLabel("Pacientes"); title.setProperty("class","section-title"); lay.addWidget(title)

        # Filtros / busca
        filter_bar = QHBoxLayout(); filter_bar.setSpacing(8)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Pesquisar nome, condição, fisio...")
        self.cb_fisio = QComboBox(); fisios = sorted({p.fisio for p in patients}); self.cb_fisio.addItems(["Todos"] + fisios)
        self.cb_cond = QComboBox(); conds = sorted({p.condicao for p in patients}); self.cb_cond.addItems(["Todos"] + conds)
        self.cb_sexo = QComboBox(); sexos = sorted({p.sexo for p in patients}); self.cb_sexo.addItems(["Todos"] + sexos)
        filter_bar.addWidget(QLabel("Buscar:")); filter_bar.addWidget(self.search_edit,1)
        filter_bar.addWidget(QLabel("Fisio:")); filter_bar.addWidget(self.cb_fisio)
        filter_bar.addWidget(QLabel("Condição:")); filter_bar.addWidget(self.cb_cond)
        filter_bar.addWidget(QLabel("Sexo:")); filter_bar.addWidget(self.cb_sexo)
        lay.addLayout(filter_bar)

        # Tabela com proxy
        self.model = PatientsTableModel(patients)
        self.proxy = PatientsFilterProxy(); self.proxy.setSourceModel(self.model)
        self.table = QTableView(); self.table.setModel(self.proxy)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        lay.addWidget(self.table, 4)

        # Painel de detalhes
        self.detail_frame = QFrame(); self.detail_frame.setObjectName("SensorCard")
        df_lay = QVBoxLayout(self.detail_frame); df_lay.setContentsMargins(16,16,16,16); df_lay.setSpacing(8)
        self.detail_title = QLabel("Selecione um paciente"); self.detail_title.setProperty("class","sensor-label")
        self.detail_info = QTextEdit(); self.detail_info.setReadOnly(True)
        df_lay.addWidget(self.detail_title)
        df_lay.addWidget(self.detail_info)
        lay.addWidget(self.detail_frame, 2)

        # Conexões
        self.search_edit.textChanged.connect(self._apply_filters)
        self.cb_fisio.currentTextChanged.connect(self._apply_filters)
        self.cb_cond.currentTextChanged.connect(self._apply_filters)
        self.cb_sexo.currentTextChanged.connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._selection_changed)
        self._apply_filters()

    def _apply_filters(self):
        self.proxy.set_filters(self.search_edit.text(), self.cb_fisio.currentText(), self.cb_cond.currentText(), self.cb_sexo.currentText())
        # Limpa detalhe se item atual não passa mais no filtro
        self._update_detail_from_selection()

    def _selection_changed(self, *_):
        self._update_detail_from_selection()

    def _update_detail_from_selection(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            self.detail_title.setText("Selecione um paciente")
            self.detail_info.setPlainText("")
            return
        proxy_index = indexes[0]
        source_index = self.proxy.mapToSource(proxy_index)
        patient = self.model.patient_at(source_index.row())
        if not patient:
            return
        self.detail_title.setText(f"{patient.nome} (ID: {patient.id})")
        # Simulated history placeholder
        history_placeholder = "\n".join([
            "Histórico (demo):",
            "- Sessão 01: Avaliação inicial",
            "- Sessão 02: Exercícios de amplitude",
            "- Sessão 03: Jogo de reabilitação"
        ])
        info = (
            f"Nome: {patient.nome}\n"
            f"Idade: {patient.idade}\n"
            f"Sexo: {patient.sexo}\n"
            f"Condição: {patient.condicao}\n"
            f"Fisioterapeuta: {patient.fisio}\n"
            f"Registro: {patient.registro_fisio}\n\n"
            f"{history_placeholder}\n\nDescrição: (Adicionar notas clínicas aqui)"
        )
        self.detail_info.setPlainText(info)

class StartupOverlay(QWidget):
    # Overlay mostrado ao iniciar para entrada rápida de paciente/fisioterapeuta (somente frontend).
    def __init__(self, parent: QWidget, on_continue: Callable[[str,str,str,str],None]):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("StartupOverlay")
        self.on_continue = on_continue
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QFrame(); card.setObjectName("SensorCard")
        inner = QFormLayout(card); inner.setSpacing(12); inner.setContentsMargins(28,28,28,28)
        self.ed_paciente = QLineEdit(); self.ed_paciente.setPlaceholderText("Nome do paciente")
        self.ed_idade = QSpinBox(); self.ed_idade.setRange(1, 120); self.ed_idade.setValue(30)
        self.cb_sexo = QComboBox(); self.cb_sexo.addItems(["F","M","Outro"]) 
        self.ed_condicao = QLineEdit(); self.ed_condicao.setPlaceholderText("Condição / Observação")
        self.ed_fisio = QLineEdit(); self.ed_fisio.setPlaceholderText("Fisioterapeuta")
        self.ed_registro = QLineEdit(); self.ed_registro.setPlaceholderText("Registro Profissional")
        inner.addRow("Paciente", self.ed_paciente)
        inner.addRow("Idade", self.ed_idade)
        inner.addRow("Sexo", self.cb_sexo)
        inner.addRow("Condição", self.ed_condicao)
        inner.addRow("Fisioterapeuta", self.ed_fisio)
        inner.addRow("Registro", self.ed_registro)
        btn = QPushButton("Continuar")
        btn.clicked.connect(self._submit)
        inner.addRow(btn)
        lay.addWidget(card)
    def _submit(self):
        self.on_continue(
            self.ed_paciente.text() or "Paciente Demo",
            self.ed_fisio.text() or "Fisio Demo",
            self.ed_condicao.text() or "--",
            self.ed_registro.text() or "--"
        )
        self.hide()

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

class DevPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self); layout.setSpacing(18)
        title = QLabel("PAINEL DEV"); title.setProperty("class","section-title")
        layout.addWidget(title)

        # Card de Logs (estilo igual aos demais usando QFrame#SensorCard)
        self.log_card = QFrame(); self.log_card.setObjectName("SensorCard")
        card_lay = QVBoxLayout(self.log_card); card_lay.setSpacing(10); card_lay.setContentsMargins(18,16,18,16)
        header = QHBoxLayout(); header.setSpacing(8)
        lbl_logs = QLabel("LOGS RECENTES")
        lbl_logs.setStyleSheet("font-weight:600; letter-spacing:0.5px;")
        self.btn_clear = QPushButton("Limpar"); self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFixedHeight(26)
        self.btn_clear.clicked.connect(self.clear_log)
        header.addWidget(lbl_logs); header.addStretch(); header.addWidget(self.btn_clear)
        card_lay.addLayout(header)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setPlaceholderText("Logs recentes do sistema...")
        self.log.setMinimumHeight(300)
        card_lay.addWidget(self.log, 1)
        layout.addWidget(self.log_card, 1)
        layout.addStretch()

        self._max_lines = 500
        self._with_timestamp = True

    def add_line(self, text: str):
        if self._with_timestamp:
            ts = time.strftime('%H:%M:%S')
            line = f"[{ts}] {text}"
        else:
            line = text
        self.log.append(line)
        # Limita quantidade de linhas para não crescer indefinidamente
        cur = self.log.toPlainText().splitlines()
        if len(cur) > self._max_lines:
            # Mantém apenas últimas N linhas
            tail = '\n'.join(cur[-self._max_lines:])
            self.log.setPlainText(tail)
            # Move cursor para final novamente
            self.log.moveCursor(self.log.textCursor().MoveOperation.End)

    def clear_log(self):
        self.log.clear()

# ------------------ Main Window ------------------
class MainWindow(QMainWindow):
    def __init__(self, sensors: Dict[str, object]=None, latest_readings: Dict[str,float]=None, goniometer=None):
        super().__init__()
        self.setWindowTitle("MarmSoft")
        # Define ícone principal se disponível
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta marmsoft
            icon_path = os.path.join(base_dir, 'assets', 'icon.png')
            if os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass  # falha silenciosa não crítica
        self.resize(1500, 920)
        # Estado principal
        # Sensores backend (SensorData) e storage de leituras
        self.sensor_backend = sensors or {}
        self.latest_readings = latest_readings or {}
        self.goniometer = goniometer
        sensor_keys = list(self.sensor_backend.keys()) if self.sensor_backend else (SENSOR_NAMES_FLEX + SENSOR_NAMES_FSR + [GONIOMETRO_NAME])
        # Garante que o goniômetro apareça nos painéis se estiver disponível
        if self.goniometer and GONIOMETRO_NAME not in sensor_keys:
            sensor_keys.append(GONIOMETRO_NAME)
        self.sensors = {n: SensorState(n) for n in sensor_keys}
        self.session = None  # AppSession | None
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
            ("Pacientes", "👥"),
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
        self.page_patients = PatientsPage(MOCK_PATIENTS)
        self.page_sensors = SensorsPage(self.sensors)
        self.page_calib = CalibrationPage(self.sensors, self.sensor_backend, self.latest_readings, lambda: self.current_theme)
        self.page_tests = TestsPage()
        self.page_games = GamesPage(self._launch_flybird)
        self.page_history = HistoryPage()
        self.page_settings = SettingsPage(self.change_theme)
        # Extensões dinâmicas (BLE + filtro) após construção da page_settings
        self._extend_settings_with_ble_and_filter()
        self.page_dev = DevPage()
        for p in [self.page_dashboard,self.page_patients,self.page_sensors,self.page_calib,self.page_tests,self.page_games,self.page_history,self.page_settings,self.page_dev]:
            self.stack.addWidget(p)
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        body_h.addWidget(self.nav_list)
        body_h.addWidget(self.stack, 1)
        main_v.addLayout(body_h, 1)

        # Finaliza configuração pós construção básica
        self._post_setup()
        # Carrega calibrações existentes (flex) se disponíveis
        self._load_existing_calibrations()

    def _launch_flybird(self):
        try:
            from threading import Thread
            from FlyBird.main_fb import main_fb
            def run_game():
                # fornece função de sensor flex6 se disponível
                get_angle = lambda: self.latest_readings.get('flex6_angle', 0.0)
                main_fb(sensor_data_provider=get_angle)
            Thread(target=run_game, daemon=True).start()
            self.page_dev.add_line("FlyBird iniciado")
        except Exception as e:
            self.page_dev.add_line(f"Erro ao iniciar FlyBird: {e}")

    def _post_setup(self):
        # Seleciona página inicial
        self.nav_list.setCurrentRow(0)

        # Timers de simulação / atualização
        self.sensor_timer = QTimer(self)
        self.sensor_timer.timeout.connect(self._update_sensors_loop)
        self.sensor_timer.start(50)
        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.timeout.connect(self.update_dashboard)
        self.dashboard_timer.start(1000)

        # Log e BLE simulado
        self.fake_ble_connected = False
        # Tenta autoconectar BLE com base na config (se disponível)
        QTimer.singleShot(500, self._try_auto_reconnect_ble)
        # Logs iniciais
        self.page_dev.add_line("Aplicação iniciada (simulada)")
        self.page_dev.add_line("[INFO] Protótipo carregado")

        # Estilo inicial
        self.apply_stylesheet()
        # Overlay de início (frontend)
        self.show_startup_overlay()

    def _load_existing_calibrations(self):
        """Varre diretório calibrations/flex/ e aplica calibrações para sensores flex existentes.

        Formato esperado: calibrations/flex/calibration_<sensor>.csv
        Ex: calibration_flex6.csv
        """
        base_dir = os.path.join(os.getcwd(), 'calibrations', 'flex')
        if not os.path.isdir(base_dir):
            return
        loaded = 0
        try:
            for fname in os.listdir(base_dir):
                if not fname.startswith('calibration_') or not fname.endswith('.csv'):
                    continue
                sensor_name = fname[len('calibration_'):-4]  # remove prefixo e .csv
                # Ignora arquivos de fsr por enquanto (future: calibrar força)
                if sensor_name not in self.sensor_backend:
                    continue
                path = os.path.join(base_dir, fname)
                try:
                    ok = self.sensor_backend[sensor_name].load_calibration_from_file(path)
                    if ok:
                        loaded += 1
                except Exception as e:
                    if hasattr(self, 'page_dev'):
                        self.page_dev.add_line(f"Falha carregar calib {sensor_name}: {e}")
            if loaded and hasattr(self, 'page_dev'):
                self.page_dev.add_line(f"{loaded} calibrações aplicadas no startup.")
        except Exception as e:
            if hasattr(self, 'page_dev'):
                self.page_dev.add_line(f"Erro ao varrer calibrações: {e}")

    def apply_stylesheet(self):
        # Define paletas
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
        btn_text_color = theme['side_item'] if self.current_theme == 'Light' else '#dde2e7'
        # Monta QSS escapando chaves com duplicação
        qss = (
            f"QMainWindow {{ background-color: {theme['bg']}; }}\n"
            f"#TopBar {{ background: {theme['top']}; border-bottom:1px solid {theme['top_border']}; }}\n"
            "#StartupOverlay { background: rgba(0,0,0,0.65); }\n"
            f"QTableView {{ background:{theme['card_bg']}; border:1px solid {theme['card_border']}; border-radius:14px; gridline-color:{theme['card_border']}; }}\n"
            f"QHeaderView::section {{ background:{theme['side_bg']}; padding:6px 4px; border:0; color:{theme['side_item']}; }}\n"
            f"QTableView::item:selected {{ background:{theme['accent_a']}; color:#fff; }}\n"
            f"QToolButton {{ background: transparent; font-size:18px; padding:4px 10px; border:0; color:{theme['text']}; }}\n"
            f"QToolButton:hover {{ background: {theme['btn_bg_hover']}; border-radius:10px; }}\n"
            f"QListWidget#Sidebar {{ background:{theme['side_bg']}; border:1px solid {theme['side_border']}; border-radius:18px; padding:12px; }}\n"
            f"QListWidget#Sidebar::item {{ margin:4px 4px; padding:10px 14px; color:{theme['side_item']}; border-radius:12px; font-size:14px; }}\n"
            f"QListWidget#Sidebar::item:selected {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {theme['accent_a']}, stop:1 {theme['accent_b']}); color:#fff; }}\n"
            f"QListWidget#Sidebar::item:hover:!selected {{ background:{theme['side_hover']}; }}\n"
            f"QFrame#StatusCard {{ background:{theme['card_bg']}; border:1px solid {theme['card_border']}; border-radius:18px; }}\n"
            f"QFrame#SensorCard {{ background:{theme['sensor_bg']}; border:1px solid {theme['sensor_border']}; border-radius:14px; }}\n"
            f"QTextEdit {{ background:{theme['text_edit_bg']}; border:1px solid {theme['text_edit_border']}; border-radius:14px; color:{theme['text']}; padding:8px; }}\n"
            f"QProgressBar {{ background:{theme['sensor_bg']}; border:1px solid {theme['sensor_border']}; border-radius:10px; height:22px; color:{theme['text']}; }}\n"
            f"QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {theme['progress_a']}, stop:1 {theme['progress_b']}); border-radius:10px; }}\n"
            f"QLabel[class='card-title'] {{ color:{theme['muted']}; letter-spacing:1px; }}\n"
            f"QLabel[class='card-value'] {{ color:{theme['text']}; }}\n"
            f"QLabel[class='brand'] {{ font-size:18px; font-weight:600; color:{theme['text']}; }}\n"
            f"QLabel[class='badge'] {{ background:{theme['badge_bg']}; padding:4px 12px; border-radius:14px; color:#fff; font-size:12px; }}\n"
            f"QLabel[class='section-title'] {{ font-size:14px; font-weight:600; color:{theme['text']}; }}\n"
            f"QLabel[class='sensor-label'] {{ font-weight:600; color:{theme['label_sensor']}; }}\n"
            f"QComboBox, QSpinBox, QLineEdit {{ background:{theme['input_bg']}; border:1px solid {theme['input_border']}; border-radius:10px; padding:6px 10px; color:{theme['text']}; }}\n"
            "QComboBox::drop-down { border:0; }\n"
            f"QCheckBox {{ color:{theme['text']}; }}\n"
            f"QCheckBox::indicator {{ width:18px; height:18px; }}\n"
            f"QCheckBox::indicator:unchecked {{ border:1px solid {theme['checkbox_border']}; background:{theme['checkbox_bg']}; border-radius:6px; }}\n"
            f"QCheckBox::indicator:checked {{ border:1px solid {theme['checkbox_border_sel']}; border-radius:6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {theme['accent_a']}, stop:1 {theme['accent_b']}); }}\n"
            f"QScrollBar:vertical {{ background:{theme['side_bg']}; width:10px; margin:4px; border-radius:5px; }}\n"
            f"QScrollBar::handle:vertical {{ background:{theme['card_border']}; border-radius:5px; min-height:40px; }}\n"
            f"QScrollBar::handle:vertical:hover {{ background:{theme['accent_a']}; }}\n"
            "QScrollBar::add-line, QScrollBar::sub-line { height:0; }\n"
            f"QPushButton {{ background:{theme['btn_bg']}; border:1px solid {theme['btn_border']}; border-radius:12px; color:{btn_text_color}; padding:8px 16px; font-weight:500; }}\n"
            f"QPushButton:hover {{ background:{theme['btn_bg_hover']}; }}\n"
            f"QPushButton:pressed {{ background:{theme['btn_bg_press']}; }}\n"
            # Segmented control styling
            f"QFrame#Segmented {{ background:{theme['side_bg']}; border:1px solid {theme['side_border']}; border-radius:18px; }}\n"
            f"QFrame#Segmented > QPushButton {{ background:transparent; border:0; border-radius:14px; padding:6px 18px; color:{btn_text_color}; font-weight:600; }}\n"
            f"QFrame#Segmented > QPushButton:hover {{ background:{theme['btn_bg_hover']}; }}\n"
            f"QFrame#Segmented > QPushButton[selected='true'] {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {theme['accent_a']}, stop:1 {theme['accent_b']}); color:#fff; }}\n"
        )
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
            original = it.data(Qt.ItemDataRole.UserRole) or ''
            mapping = {
                'Dashboard':'🏠','Pacientes':'👥','Sensores':'🧪','Calibração':'🛠','Testes':'📊','Jogos':'🎮','Histórico':'🗂','Config':'⚙','Dev':'</>'
            }
            glyph = mapping.get(original, '•')
            it.setIcon(self.make_icon(glyph))
        self.apply_stylesheet()

    def update_session_badge(self):
        self.session_badge.setText(f"Sessão: {self.session.id}" if self.session else "Sessão: --")

    def simulate_ble_connect(self):
        self.fake_ble_connected = True
        self.page_dashboard.card_ble.update_value("Conectado")
        self.page_dev.add_line("BLE conectado")

    def switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def start_session(self):
        if self.session:
            return
        sid = f"sess_{int(time.time())}"
        self.session = AppSession(id=sid, start_time=time.time())
        self.page_dashboard.card_session.update_value("ATIVA")
        self.update_session_badge()
        self.page_dev.add_line(f"Sessão {sid} iniciada")

    def _update_sensors_loop(self):
        current_time = time.time()
        # Atualiza leitura do goniômetro (thread externa preenche self.goniometer.angle)
        if self.goniometer and getattr(self.goniometer, 'dll', None):
            try:
                self.latest_readings['goniometer_angle'] = float(self.goniometer.get_angle())
            except Exception:
                # Mantém valor anterior em caso de erro momentâneo
                pass
        if self.sensor_backend:
            # Alimenta valores dos latest_readings (preenchidos pelo BLE notification handler no futuro) nas curves
            for name, st in self.sensors.items():
                if name.startswith('flex'):
                    v = self.latest_readings.get(f"{name}_angle", 0.0)
                elif name.startswith('fsr'):
                    v = self.latest_readings.get(f"{name}_force", 0.0)
                elif name == GONIOMETRO_NAME:
                    v = self.latest_readings.get('goniometer_angle', 0.0)
                else:
                    v = 0.0
                st.last_value = v
                st.values.append(v)
                if len(st.values) > 500:
                    st.values.pop(0)
                self.page_sensors.push_value(name, v)
        else:
            # fallback para simulação antiga
            for name, st in self.sensors.items():
                if name.startswith('flex'):
                    v = 30 + 15*math.sin(current_time*2 + hash(name)%10)
                else:
                    v = 5 + 3*math.sin(current_time*1.5 + hash(name)%7)
                st.last_value = v
                st.values.append(v)
                if len(st.values)>500: st.values.pop(0)
                self.page_sensors.push_value(name, v)
        # Sparklines
        flex_vals = [self.sensors[n].last_value for n in self.sensors if n.startswith('flex')]
        fsr_vals = [self.sensors[n].last_value for n in self.sensors if n.startswith('fsr')]
        if flex_vals:
            self.page_dashboard.spark_flex.push(sum(flex_vals)/len(flex_vals))
        if fsr_vals:
            self.page_dashboard.spark_fsr.push(sum(fsr_vals)/len(fsr_vals))
        # Atualiza painel antigo se ativo
        if hasattr(self, 'page_sensors'):
            self.page_sensors.update_unified_plot(current_time, self.latest_readings)
        # Atualiza plot de calibração em tempo real
        if hasattr(self, 'page_calib'):
            try:
                self.page_calib.update_live_plot(current_time)
            except Exception:
                pass

    # ---------- Extensão Config (BLE / Filter) ----------
    def _extend_settings_with_ble_and_filter(self):
        # Inserir widgets extras abaixo do formulário existente
        from PyQt6.QtWidgets import QVBoxLayout, QListWidget, QHBoxLayout
        host_layout = self.page_settings.layout()
        # Container visual
        ble_title = QLabel("Conexão Bluetooth")
        ble_title.setProperty('class','section-title')
        host_layout.addRow(ble_title)
        btn_row = QHBoxLayout()
        self.btn_ble_scan = QPushButton("Atualizar")
        self.btn_ble_connect = QPushButton("Conectar")
        self.btn_ble_disconnect = QPushButton("Desconectar")
        self.btn_ble_disconnect.setEnabled(False)
        for b in (self.btn_ble_scan,self.btn_ble_connect,self.btn_ble_disconnect):
            btn_row.addWidget(b)
        host_layout.addRow(btn_row)
        self.list_ble = QListWidget(); self.list_ble.setMaximumHeight(140)
        host_layout.addRow(self.list_ble)
        self.lbl_ble_status = QLabel("Status: Desconectado")
        host_layout.addRow(self.lbl_ble_status)
        # Suavização
        smooth_title = QLabel("Filtro de Suavização (alpha)")
        smooth_title.setProperty('class','section-title')
        host_layout.addRow(smooth_title)
        self.slider_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_alpha.setRange(1,100)
        # Força valor inicial 0.50 independentemente do backend
        self.slider_alpha.setValue(50)
        if self.sensor_backend:
            for s in self.sensor_backend.values():
                s.alpha = 0.5
        self.lbl_alpha_val = QLabel(f"{0.50:.2f}")
        row_alpha = QHBoxLayout(); row_alpha.addWidget(self.slider_alpha,1); row_alpha.addWidget(self.lbl_alpha_val)
        host_layout.addRow(row_alpha)
        self.slider_alpha.valueChanged.connect(self._alpha_changed)
        # Ligações botões BLE (placeholders; implementação real virá com scan async)
        self.btn_ble_scan.clicked.connect(self._ble_scan)
        self.btn_ble_connect.clicked.connect(self._ble_connect)
        self.btn_ble_disconnect.clicked.connect(self._ble_disconnect)
        # Estado
        self._ble_manager = None
        self._ble_device_list = []
        # Carrega UUID do serviço pela config.json (fallback para definido)
        self._ble_target_uuid = self._load_ble_service_uuid()
        self._ble_last_device = self._load_last_ble_device()
        self._ble_thread = None

    def _alpha_changed(self, val: int):
        alpha = val/100.0
        self.lbl_alpha_val.setText(f"{alpha:.2f}")
        for sensor in (self.sensor_backend or {}).values():
            sensor.alpha = alpha
        self.page_dev.add_line(f"Alpha ajustado para {alpha:.2f}")

    class _BleScanWorker(QObject):
        finished = pyqtSignal(list)
        def run(self):
            import asyncio
            try:
                from bleak import BleakScanner
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                devices = loop.run_until_complete(BleakScanner.discover())
                loop.close()
            except Exception:
                devices = []
            self.finished.emit(devices)

    def _ble_scan(self):
        # Worker em QThread para varredura BLE
        self.page_dev.add_line("Varredura BLE iniciada...")
        self.list_ble.clear(); self.list_ble.addItem("Buscando...")
        self._ble_scan_thread = QThread()
        self._ble_scan_worker = MainWindow._BleScanWorker()
        self._ble_scan_worker.moveToThread(self._ble_scan_thread)
        self._ble_scan_thread.started.connect(self._ble_scan_worker.run)
        self._ble_scan_worker.finished.connect(self._ble_scan_thread.quit)
        self._ble_scan_worker.finished.connect(self._populate_ble_devices)
        self._ble_scan_thread.start()

    def _populate_ble_devices(self, devices: list):
        self._ble_device_list = devices
        self.list_ble.clear()
        for d in devices:
            self.list_ble.addItem(f"{d.name or 'Desconhecido'} ({d.address})")
        self.page_dev.add_line(f"Scan BLE concluído: {len(devices)} dispositivos")
        # Se há um último dispositivo salvo, tenta conectar automaticamente
        if getattr(self, '_auto_reconnect_pending', False) and getattr(self, '_auto_reconnect_target', ''):
            target_addr = self._auto_reconnect_target
            match = None
            for d in devices:
                if d.address == target_addr:
                    match = d
                    break
            if match:
                self.page_dev.add_line(f"Auto reconectar BLE: {match.address}")
                self._connect_to_device(match)
                self._auto_reconnect_pending = False
            else:
                # Agenda nova tentativa de scan em 1.5s
                QTimer.singleShot(1500, self._auto_reconnect_scan)

    def _ble_connect(self):
        sel = self.list_ble.currentRow()
        if sel < 0 or sel >= len(self._ble_device_list):
            self.page_dev.add_line("Nenhum dispositivo selecionado")
            return
        device = self._ble_device_list[sel]
        self._connect_to_device(device)

    def _connect_to_device(self, device):
        from threading import Thread
        from Modules.ble_manager import BLEManager
        self.page_dev.add_line(f"Conectando a {device.address}...")
        self.lbl_ble_status.setText("Status: Conectando...")
        def _notify(sender, data: bytes):
            try:
                decoded = data.decode('utf-8')
                parts = decoded.split(', ')
                for part in parts:
                    if '=' not in part: continue
                    name, vstr = part.split('=')
                    voltage = float(vstr.rstrip('V'))
                    sid = name.lower()
                    # -------- Mapeamento lógico flex3 <-> flex8 --------
                    # Para atender necessidade de inversão dos canais físicos, trocamos
                    # a identificação antes de alimentar backend / leituras.
                    # Assim: dado vindo como flex3 passa a ser tratado como flex8 e vice‑versa.
                    # (Reversível removendo bloco.)
                    if sid == 'flex3':
                        sid = 'flex8'
                    elif sid == 'flex8':
                        sid = 'flex3'
                    if sid in self.sensor_backend:
                        filt_v = self.sensor_backend[sid].apply_filter(voltage)
                        self.latest_readings[f"{sid}_voltage"] = filt_v
                        if sid.startswith('flex'):
                            ang = self.sensor_backend[sid].get_angle(filt_v)
                            self.latest_readings[f"{sid}_angle"] = ang
                        elif sid.startswith('fsr'):
                            force = self.sensor_backend[sid].get_force(filt_v)
                            self.latest_readings[f"{sid}_force"] = force
            except Exception as e:
                self.page_dev.add_line(f"Erro notif: {e}")
        self._ble_manager = BLEManager(device.address, self._ble_target_uuid, _notify)
        self._ble_thread = Thread(target=self._ble_manager.start_loop, daemon=True)
        self._ble_thread.start()
        self.lbl_ble_status.setText(f"Status: Conectado ({device.address})")
        self.btn_ble_connect.setEnabled(False); self.btn_ble_disconnect.setEnabled(True)
        # Atualiza o card de dashboard com o mesmo texto do status
        self.page_dashboard.card_ble.update_value(f"Conectado ({device.address})")
        # Persiste último dispositivo
        self._save_last_ble_device(device.address)

    def _ble_disconnect(self):
        if self._ble_manager:
            self._ble_manager.stop_loop()
            self._ble_manager = None
        self.lbl_ble_status.setText("Status: Desconectado")
        self.btn_ble_connect.setEnabled(True); self.btn_ble_disconnect.setEnabled(False)
        # Mantém o dashboard sincronizado com o status
        self.page_dashboard.card_ble.update_value("Desconectado")
        self.page_dev.add_line("BLE desconectado")

    def update_dashboard(self):
        if not self.session:
            # autoinicia sessão para demonstração
            self.start_session()
        self.page_dashboard.card_calib.update_value("v1 (simulada)")
        self.update_goniometer_status()

    def update_goniometer_status(self):
        status = "Conectado" if (self.goniometer and getattr(self.goniometer, 'dll', None)) else "Desconectado"
        self.page_dashboard.card_gonio.update_value(status)

    # ---------- Config helpers ----------
    def _config_path(self):
        return os.path.join(os.getcwd(), 'config.json')
    def _read_config(self):
        try:
            with open(self._config_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    def _write_config(self, data: dict):
        try:
            with open(self._config_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if hasattr(self, 'page_dev'):
                self.page_dev.add_line(f"Falha escrevendo config: {e}")
    def _load_ble_service_uuid(self) -> str:
        cfg = self._read_config()
        return cfg.get('bleServiceUuid', 'abcdef01-1234-5678-1234-56789abcdef0')
    def _load_last_ble_device(self) -> str:
        cfg = self._read_config()
        return cfg.get('lastBleDevice', '')
    def _save_last_ble_device(self, address: str):
        cfg = self._read_config()
        cfg['lastBleDevice'] = address
        if 'bleServiceUuid' not in cfg:
            cfg['bleServiceUuid'] = self._ble_target_uuid
        self._write_config(cfg)
    def _try_auto_reconnect_ble(self):
        # Status inicial consistente
        self.lbl_ble_status.setText("Status: Desconectado")
        self.page_dashboard.card_ble.update_value("Desconectado")
        last = self._load_last_ble_device()
        if not last:
            return
        # Dispara um scan e tenta reconectar ao encontrar (até 3 tentativas)
        self._auto_reconnect_pending = True
        self._auto_reconnect_attempts = 0
        self._auto_reconnect_target = last
        self._auto_reconnect_scan()

    def _auto_reconnect_scan(self):
        if getattr(self, '_auto_reconnect_attempts', 0) >= 3:
            self.lbl_ble_status.setText("Status: Dispositivo não encontrado")
            self.page_dashboard.card_ble.update_value("Dispositivo não encontrado")
            self._auto_reconnect_pending = False
            return
        self._auto_reconnect_attempts += 1
        self.page_dev.add_line(f"Auto-reconexão BLE tentativa {self._auto_reconnect_attempts}...")
        self._ble_scan()

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
                'Dashboard':'🏠','Pacientes':'👥','Sensores':'🧪','Calibração':'🛠','Testes':'📊','Jogos':'🎮','Histórico':'🗂','Config':'⚙','Dev':'</>'
            }
            it.setIcon(self.make_icon(mapping.get(label,'•')))
        self.apply_stylesheet()
        self.page_dev.add_line(f"Tema alterado para: {theme}")
        # Propaga tema para o plot antigo se existir
        try:
            if hasattr(self, 'page_sensors') and hasattr(self.page_sensors, 'unified_plot'):
                self.page_sensors.unified_plot.apply_theme(theme)
        except Exception:
            pass

    # --------------- Startup Overlay Handling ---------------
    def show_startup_overlay(self):
        self.overlay = StartupOverlay(self, self._overlay_continue)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay') and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())
    def _overlay_continue(self, paciente: str, fisio: str, cond: str, reg: str):
        # Apenas log – não integra com resto ainda
        self.page_dev.add_line(f"Sessão para {paciente} / {fisio} ({cond})")
        # Poderia adicionar dinamicamente na lista de pacientes (mock)
        new_id = f"P{len(MOCK_PATIENTS)+1:03d}"
        MOCK_PATIENTS.append(Patient(new_id, paciente, 30, 'N', cond, fisio, reg))
        # Atualiza tabela se página pacientes aberta
        if hasattr(self, 'page_patients'):
            self.page_patients.model.layoutAboutToBeChanged.emit()
            self.page_patients.model.patients = MOCK_PATIENTS
            self.page_patients.model.layoutChanged.emit()
        self.start_session()

    def closeEvent(self, event):
        if QMessageBox.question(self, "Sair", "Deseja realmente sair?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
            event.ignore()
            return
        # Tenta encerrar BLE e goniômetro de forma limpa
        try:
            self._shutdown_ble()
        except Exception:
            pass
        try:
            if self.goniometer and getattr(self.goniometer, 'dll', None):
                self.goniometer.stop_reading()
        except Exception:
            pass
        event.accept()

    def _shutdown_ble(self):
        """Finaliza o loop BLE para evitar ficar ativo após fechar a janela."""
        try:
            if self._ble_manager:
                self._ble_manager.stop_loop()
                # Aguardar brevemente a thread terminar
                if getattr(self, '_ble_thread', None):
                    self._ble_thread.join(timeout=2.0)
                self._ble_manager = None
                self._ble_thread = None
        except Exception:
            pass

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
