"""Versão Qt do PlotManager original (CustomTkinter) mantendo a mesma lógica.
Substitui apenas o backend de canvas para FigureCanvasQTAgg e encaixa em um layout Qt.
"""
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from collections import deque
import matplotlib.pyplot as plt

class PlotManager:
    """Gerenciador de plots em Qt (antigo *QtOld* renomeado).

    Mantém API: set_mode, update, clear, update_displayed_sensors, apply_theme,
    set_show_legend, set_show_voltage. Foi renomeado de PlotManagerQtOld após
    unificação dos nomes de arquivo.
    """
    def __init__(self, parent, time_window=10, sensors=None, displayed_sensors=None):
        self.time_window = time_window
        self.sensors = sensors or {}
        self.displayed_sensors = displayed_sensors if displayed_sensors is not None else set(self.sensors.keys())
        self.plot_mode = "flex"  # "flex" ou "fsr"

        self.time_history = deque()
        self.voltage_histories = {sid: deque() for sid in self.sensors.keys()}
        self.angle_histories = {sid: deque() for sid in self.sensors.keys() if sid.startswith('flex')}
        self.force_histories = {sid: deque() for sid in self.sensors.keys() if sid.startswith('fsr')}
        self.goniometer_history = deque()

        self.fig = Figure(figsize=(12, 6), dpi=100)
        # Inicializa tema (default dark) - poderá ser alterado via apply_theme
        self._theme = 'Dark'
        self._bg_dark = "#1A1F27"
        self._bg_light = '#ffffff'
        self._fg_dark = '#ffffff'
        self._fg_light = '#1e1e1e'
        self._grid_dark = '#2d3640'
        self._grid_light = '#d5dbe2'
        self._spine_dark = '#4a525c'
        self._spine_light = '#b7c2cc'
        self.fig.patch.set_facecolor(self._bg_dark)
        self.ax_voltage = self.fig.add_subplot(1, 2, 1)
        self.ax_detail = self.fig.add_subplot(1, 2, 2)
        # Ajusta margens: bottom maior para caber legenda abaixo do gráfico detalhado
        self.fig.subplots_adjust(left=0.06, right=0.97, top=0.90, bottom=0.22, wspace=0.28)
        # Aplicará estilos depois através de apply_theme
        self._show_legend = True
        self._show_voltage = True

        colors = plt.cm.tab10.colors
        sensor_list = sorted(self.sensors.keys())
        self.sensor_colors = {sid: colors[i % 10] for i, sid in enumerate(sensor_list)}

        self.voltage_lines = {sid: self.ax_voltage.plot([], [], label=f"{sid.upper()} Voltage", color=self.sensor_colors[sid])[0] for sid in self.sensors.keys()}
        self.angle_lines = {sid: self.ax_detail.plot([], [], label=sid.upper(), color=self.sensor_colors[sid])[0] for sid in self.angle_histories.keys()}
        self.force_lines = {sid: self.ax_detail.plot([], [], label=sid.upper(), color=self.sensor_colors[sid])[0] for sid in self.force_histories.keys()}
        self.line_goniometer_angle = self.ax_detail.plot([], [], label="GONIÔMETRO", color="black")[0]
        # Configura textos iniciais do eixo de tensão (cores definidas em apply_theme)
        self.ax_voltage.set_title("Tensão (V) x Tempo")
        self.ax_voltage.set_xlabel("Tempo (s)")
        self.ax_voltage.set_ylabel("Tensão (V)")
        self.ax_voltage.set_ylim(0, 4)
        self.set_flex_mode_labels()
        # Cria canvas antes de aplicar tema para evitar AttributeError
        self.canvas = FigureCanvasQTAgg(self.fig)
        # Aplica tema inicial
        self.apply_theme('Dark')
        # Adiciona ao layout Qt do parent
        from PyQt6.QtWidgets import QVBoxLayout
        if parent.layout() is None:
            parent.setLayout(QVBoxLayout())
        parent.layout().addWidget(self.canvas)
    # (Legenda interna padrão do matplotlib será usada; versão externa removida)

    def set_mode(self, mode):
        self.plot_mode = mode

    def set_flex_mode_labels(self):
        fg = self._fg_dark if self._theme == 'Dark' else self._fg_light
        self.ax_detail.set_title("Ângulo (°) x Tempo", color=fg)
        self.ax_detail.set_xlabel("Tempo (s)", color=fg)
        self.ax_detail.set_ylabel("Ângulo (°)", color=fg)
        self.ax_detail.set_ylim(-10, 300)

    def set_fsr_mode_labels(self):
        fg = self._fg_dark if self._theme == 'Dark' else self._fg_light
        self.ax_detail.set_title("Força x Tempo", color=fg)
        self.ax_detail.set_xlabel("Tempo (s)", color=fg)
        self.ax_detail.set_ylabel("Força (kgf)", color=fg)
        self.ax_detail.set_ylim(-10, 400)

    def update(self, current_time, latest_readings):
        self.time_history.append(current_time)
        for sid in self.sensors.keys():
            self.voltage_histories[sid].append(latest_readings.get(f'{sid}_voltage', 0.0))
        for sid in self.angle_histories.keys():
            self.angle_histories[sid].append(latest_readings.get(f'{sid}_angle', 0.0))
        for sid in self.force_histories.keys():
            self.force_histories[sid].append(latest_readings.get(f'{sid}_force', 0.0))
        self.goniometer_history.append(latest_readings.get('goniometer_angle', 0.0))

        while self.time_history and (current_time - self.time_history[0]) > self.time_window:
            self.time_history.popleft()
            for sid in self.sensors.keys():
                self.voltage_histories[sid].popleft()
                if sid in self.angle_histories: self.angle_histories[sid].popleft()
                if sid in self.force_histories: self.force_histories[sid].popleft()
            if self.goniometer_history: self.goniometer_history.popleft()

        if not self.time_history:
            return
        times = [t - self.time_history[0] for t in self.time_history]

        # Atualiza sempre a coleção correta de voltagem de acordo com o modo
        if self.plot_mode == 'flex':
            target_prefix = 'flex'
        else:
            target_prefix = 'fsr'
        for sid in self.sensors.keys():
            line = self.voltage_lines[sid]
            if not sid.startswith(target_prefix):
                # Oculta sensores do outro grupo no gráfico de tensão
                line.set_visible(False)
                continue
            if sid in self.displayed_sensors:
                line.set_data(times, self.voltage_histories[sid])
                line.set_visible(True)
            else:
                line.set_visible(False)

        if self.plot_mode == "flex":
            self.set_flex_mode_labels()
            for sid in self.angle_histories.keys():
                l = self.angle_lines[sid]
                if sid in self.displayed_sensors:
                    l.set_data(times, self.angle_histories[sid]); l.set_visible(True)
                else: l.set_visible(False)
            for sid in self.force_histories.keys():
                self.force_lines[sid].set_visible(False)
            if 'goniometer' in self.displayed_sensors:
                self.line_goniometer_angle.set_data(times, self.goniometer_history)
                self.line_goniometer_angle.set_visible(True)
            else:
                self.line_goniometer_angle.set_visible(False)
        else:
            self.set_fsr_mode_labels()
            for sid in self.force_histories.keys():
                l = self.force_lines[sid]
                if sid in self.displayed_sensors:
                    l.set_data(times, self.force_histories[sid]); l.set_visible(True)
                else: l.set_visible(False)
            for sid in self.angle_histories.keys():
                self.angle_lines[sid].set_visible(False)
            self.line_goniometer_angle.set_visible(False)

        # Limpa qualquer legenda anterior
        self.fig.legends.clear()
        if self._show_legend:
            handles = []
            labels = []
            if self.plot_mode == 'flex':
                for sid in self.angle_histories.keys():
                    if sid in self.displayed_sensors and self.angle_lines[sid].get_visible():
                        handles.append(self.angle_lines[sid]); labels.append(sid.upper())
                if self.line_goniometer_angle.get_visible():
                    handles.append(self.line_goniometer_angle); labels.append('GONIÔMETRO')
            else:
                for sid in self.force_histories.keys():
                    if sid in self.displayed_sensors and self.force_lines[sid].get_visible():
                        handles.append(self.force_lines[sid]); labels.append(sid.upper())
            if handles:
                # Uma única linha (todos lado a lado) e centralizado no rodapé da figura.
                ncol = len(handles)
                leg = self.fig.legend(
                    handles,
                    labels,
                    loc='lower center',
                    bbox_to_anchor=(0.5, 0.015),  # centra na largura total da figura
                    framealpha=0.85,
                    fontsize=9,
                    ncol=ncol,
                    borderaxespad=0.6,
                    columnspacing=1.0,
                    handlelength=2.0,
                )
                if self._theme == 'Dark':
                    leg.get_frame().set_facecolor('#1A1F27')
                    leg.get_frame().set_edgecolor('#3a424c')
                    for txt in leg.get_texts():
                        txt.set_color('#ffffff')
                else:
                    leg.get_frame().set_facecolor('#ffffff')
                    leg.get_frame().set_edgecolor('#b7c2cc')
                    for txt in leg.get_texts():
                        txt.set_color('#1e1e1e')
        self.ax_detail.set_xlim(0, self.time_window)
        if self._show_voltage:
            self.ax_voltage.set_xlim(0, self.time_window)
            self.ax_voltage.set_visible(True)
        else:
            # ocupa toda a largura com ax_detail
            self.ax_voltage.set_visible(False)
            # redesenha layout simples: fazer ax_detail ocupar grade inteira
            try:
                self.ax_detail.change_geometry(1,1,0,0)
            except Exception:
                pass
        self.canvas.draw()

    def clear(self):
        self.time_history.clear()
        for sid in self.sensors.keys():
            self.voltage_histories[sid].clear()
            if sid in self.angle_histories: self.angle_histories[sid].clear()
            if sid in self.force_histories: self.force_histories[sid].clear()
        self.goniometer_history.clear()
        self.fig.legends.clear(); self.canvas.draw()

    def update_displayed_sensors(self, displayed):
        self.displayed_sensors = displayed

    def set_show_legend(self, flag: bool):
        self._show_legend = flag
    def set_show_voltage(self, flag: bool):
        self._show_voltage = flag

    # ---- Tema dinâmico ----
    def apply_theme(self, theme: str):
        """Atualiza cores de fundo, textos, grid e legendas conforme tema global."""
        self._theme = theme
        dark = (theme == 'Dark')
        bg = self._bg_dark if dark else self._bg_light
        fg = self._fg_dark if dark else self._fg_light
        grid = self._grid_dark if dark else self._grid_light
        spine = self._spine_dark if dark else self._spine_light
        self.fig.patch.set_facecolor(bg)
        for ax in (self.ax_voltage, self.ax_detail):
            ax.set_facecolor(bg)
            ax.title.set_color(fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.tick_params(colors=fg if not dark else '#d0d4d8')
            for s in ax.spines.values():
                s.set_color(spine)
            # Redefine grid
            ax.grid(color=grid, linestyle='--', linewidth=0.6, alpha=0.6)
        # Reaplica labels de modo para garantir cor atual
        if self.plot_mode == 'flex':
            self.set_flex_mode_labels()
        else:
            self.set_fsr_mode_labels()
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

# Backward compatibility alias (caso algum código externo ainda importe)
PlotManagerQtOld = PlotManager
