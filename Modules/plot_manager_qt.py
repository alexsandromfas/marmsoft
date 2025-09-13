"""Versão Qt do PlotManager antigo (CustomTkinter) usando FigureCanvasQTAgg.
Fornece mesma API básica: set_mode(mode), update(current_time, latest_readings), clear(), update_displayed_sensors(set).
"""
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from collections import deque
import matplotlib.pyplot as plt

class PlotManagerQt:
    def __init__(self, parent, time_window=10, sensors=None, displayed_sensors=None):
        self.time_window = time_window
        self.sensors = sensors or {}
        self.displayed_sensors = displayed_sensors if displayed_sensors is not None else set(self.sensors.keys())
        self.plot_mode = 'flex'
        self.time_history = deque()
        self.voltage_histories = {sid: deque() for sid in self.sensors}
        self.angle_histories = {sid: deque() for sid in self.sensors if sid.startswith('flex')}
        self.force_histories = {sid: deque() for sid in self.sensors if sid.startswith('fsr')}
        self.goniometer_history = deque()

        self.fig = Figure(figsize=(10,5), dpi=100)
        self.ax_voltage = self.fig.add_subplot(1,2,1)
        self.ax_detail = self.fig.add_subplot(1,2,2)
        self.fig.subplots_adjust(wspace=0.4)

        colors = plt.cm.tab10.colors
        sensor_list = sorted(self.sensors.keys())
        sensor_colors = {sid: colors[i % 10] for i, sid in enumerate(sensor_list)}

        self.voltage_lines = {sid: self.ax_voltage.plot([], [], label=f"{sid.upper()} Voltage", color=sensor_colors[sid])[0] for sid in self.sensors}
        self.angle_lines = {sid: self.ax_detail.plot([], [], label=sid.upper(), color=sensor_colors[sid])[0] for sid in self.angle_histories}
        self.force_lines = {sid: self.ax_detail.plot([], [], label=sid.upper(), color=sensor_colors[sid])[0] for sid in self.force_histories}
        self.line_goniometer_angle = self.ax_detail.plot([], [], label="GONIÔMETRO", color='black')[0]

        self.ax_voltage.set_title("Tensão (V) x Tempo")
        self.ax_voltage.set_xlabel("Tempo (s)")
        self.ax_voltage.set_ylabel("Tensão (V)")
        self.ax_voltage.set_ylim(0,4)
        self._set_flex_labels()

        self.canvas = FigureCanvasQTAgg(self.fig)
        parent_layout = parent.layout()
        parent_layout.addWidget(self.canvas)

    def _set_flex_labels(self):
        self.ax_detail.set_title("Ângulo (°) x Tempo")
        self.ax_detail.set_xlabel("Tempo (s)")
        self.ax_detail.set_ylabel("Ângulo (°)")
        self.ax_detail.set_ylim(-10,300)

    def _set_fsr_labels(self):
        self.ax_detail.set_title("Força x Tempo")
        self.ax_detail.set_xlabel("Tempo (s)")
        self.ax_detail.set_ylabel("Força (kgf)")
        self.ax_detail.set_ylim(0,400)

    def set_mode(self, mode):
        self.plot_mode = mode

    def update(self, current_time, latest_readings):
        self.time_history.append(current_time)
        for sid in self.sensors:
            self.voltage_histories[sid].append(latest_readings.get(f'{sid}_voltage',0.0))
        for sid in self.angle_histories:
            self.angle_histories[sid].append(latest_readings.get(f'{sid}_angle',0.0))
        for sid in self.force_histories:
            self.force_histories[sid].append(latest_readings.get(f'{sid}_force',0.0))
        self.goniometer_history.append(latest_readings.get('goniometer_angle',0.0))

        while self.time_history and (current_time - self.time_history[0]) > self.time_window:
            self.time_history.popleft()
            for sid in self.sensors:
                self.voltage_histories[sid].popleft()
                if sid in self.angle_histories: self.angle_histories[sid].popleft()
                if sid in self.force_histories: self.force_histories[sid].popleft()
            if self.goniometer_history: self.goniometer_history.popleft()

        if not self.time_history:
            return
        times = [t - self.time_history[0] for t in self.time_history]

        for sid in self.sensors:
            line = self.voltage_lines[sid]
            if sid in self.displayed_sensors:
                line.set_data(times, self.voltage_histories[sid])
                line.set_visible(True)
            else:
                line.set_visible(False)

        if self.plot_mode == 'flex':
            self._set_flex_labels()
            for sid in self.angle_histories:
                l = self.angle_lines[sid]
                if sid in self.displayed_sensors:
                    l.set_data(times, self.angle_histories[sid]); l.set_visible(True)
                else: l.set_visible(False)
            for sid in self.force_histories:
                self.force_lines[sid].set_visible(False)
            if 'goniometer' in self.displayed_sensors or 'goniometro' in self.displayed_sensors:
                self.line_goniometer_angle.set_data(times, self.goniometer_history)
                self.line_goniometer_angle.set_visible(True)
            else:
                self.line_goniometer_angle.set_visible(False)
        else:
            self._set_fsr_labels()
            for sid in self.force_histories:
                l = self.force_lines[sid]
                if sid in self.displayed_sensors:
                    l.set_data(times, self.force_histories[sid]); l.set_visible(True)
                else: l.set_visible(False)
            for sid in self.angle_histories:
                self.angle_lines[sid].set_visible(False)
            self.line_goniometer_angle.set_visible(False)

        self.fig.legends.clear()
        handles=[]; labels=[]
        if self.plot_mode=='flex':
            for sid in self.angle_histories:
                if sid in self.displayed_sensors:
                    handles.append(self.angle_lines[sid]); labels.append(sid.upper())
            if self.line_goniometer_angle.is_visible():
                handles.append(self.line_goniometer_angle); labels.append('GONIÔMETRO')
        else:
            for sid in self.force_histories:
                if sid in self.displayed_sensors:
                    handles.append(self.force_lines[sid]); labels.append(sid.upper())
        if handles:
            self.fig.legend(handles, labels, loc='upper center')
        self.ax_voltage.set_xlim(0,self.time_window)
        self.ax_detail.set_xlim(0,self.time_window)
        self.canvas.draw()

    def clear(self):
        self.time_history.clear()
        for d in (self.voltage_histories,self.angle_histories,self.force_histories):
            for dq in d.values(): dq.clear()
        self.goniometer_history.clear()
        self.fig.legends.clear(); self.canvas.draw()

    def update_displayed_sensors(self, displayed):
        self.displayed_sensors = displayed
