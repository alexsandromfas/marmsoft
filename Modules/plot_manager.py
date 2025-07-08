"""Utilities for plotting sensor data in real time."""

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import matplotlib.pyplot as plt

class PlotManager:
    """Manage Matplotlib figures showing sensor values."""

    def __init__(self, parent, time_window=10, sensors=None, displayed_sensors=None):
        """Create plots bound to ``parent``.

        Parameters
        ----------
        parent : tkinter widget
            Widget where the Matplotlib canvas will be placed.
        time_window : int, optional
            Time range (seconds) to display.
        sensors : dict, optional
            Mapping of sensor identifiers to :class:`SensorData`.
        displayed_sensors : set[str], optional
            Subset of ``sensors`` currently shown.
        """
        self.time_window = time_window
        self.sensors = sensors
        self.displayed_sensors = displayed_sensors if displayed_sensors is not None else set(sensors.keys())
        self.plot_mode = "flex"  # "flex" ou "fsr"

        self.time_history = deque()
        self.voltage_histories = {sensor_id: deque() for sensor_id in sensors.keys()}
        self.angle_histories = {sensor_id: deque() for sensor_id in sensors.keys() if sensor_id.startswith('flex')}
        self.force_histories = {sensor_id: deque() for sensor_id in sensors.keys() if sensor_id.startswith('fsr')}
        self.goniometer_history = deque()

        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.ax_voltage = self.fig.add_subplot(1, 2, 1)
        self.ax_detail = self.fig.add_subplot(1, 2, 2)  # ax_detail será ângulo ou força, dependendo do modo
        self.fig.subplots_adjust(wspace=0.4)

        # Definir cores e criar dicionário de cores para cada sensor
        colors = plt.cm.tab10.colors
        sensor_list = sorted(sensors.keys())
        sensor_colors = {}
        for i, sid in enumerate(sensor_list):
            sensor_colors[sid] = colors[i % 10]

        # Criar linhas
        # Cada sensor terá linha de tensão no ax_voltage
        self.voltage_lines = {}
        for sid in self.sensors.keys():
            self.voltage_lines[sid], = self.ax_voltage.plot([], [], label=f"{sid.upper()} Voltage", color=sensor_colors[sid])

        # Para flex: angle_lines
        self.angle_lines = {}
        for sid in self.angle_histories.keys():
            self.angle_lines[sid], = self.ax_detail.plot([], [], label=sid.upper(), color=sensor_colors[sid])

        # Para fsr: force_lines
        self.force_lines = {}
        for sid in self.force_histories.keys():
            self.force_lines[sid], = self.ax_detail.plot([], [], label=sid.upper(), color=sensor_colors[sid])

        # Goniômetro
        self.line_goniometer_angle, = self.ax_detail.plot([], [], label="GONIÔMETRO", color="black", linestyle='solid')

        # Ajuste inicial dos eixos
        self.ax_voltage.set_title("Tensão (V) x Tempo")
        self.ax_voltage.set_xlabel("Tempo (s)")
        self.ax_voltage.set_ylabel("Tensão (V)")
        self.ax_voltage.set_ylim(0, 4)

        # O ax_detail mudará conforme o modo, ajustamos no update
        # Inicialmente modo flex
        self.set_flex_mode_labels()

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True)
        self.canvas.draw()

    def set_mode(self, mode):
        """Switch between ``flex`` and ``fsr`` display modes."""
        self.plot_mode = mode

    def set_flex_mode_labels(self):
        """Configure axis labels for flex sensor plotting."""
        self.ax_detail.set_title("Ângulo (°) x Tempo")
        self.ax_detail.set_xlabel("Tempo (s)")
        self.ax_detail.set_ylabel("Ângulo (°)")
        self.ax_detail.set_ylim(-10, 300)

    def set_fsr_mode_labels(self):
        """Configure axis labels for FSR plotting."""
        self.ax_detail.set_title("Força x Tempo")
        self.ax_detail.set_xlabel("Tempo (s)")
        self.ax_detail.set_ylabel("Força (kgf)")
        self.ax_detail.set_ylim(-10, 400)

        # Ajuste dinâmico no update

    def update(self, current_time, latest_readings):
        """Update all plot lines with the latest sensor values."""
        # Armazenar dados
        self.time_history.append(current_time)
        for sid in self.sensors.keys():
            self.voltage_histories[sid].append(latest_readings.get(f'{sid}_voltage', 0.0))
        for sid in self.angle_histories.keys():
            self.angle_histories[sid].append(latest_readings.get(f'{sid}_angle', 0.0))
        for sid in self.force_histories.keys():
            self.force_histories[sid].append(latest_readings.get(f'{sid}_force', 0.0))
        self.goniometer_history.append(latest_readings.get('goniometer_angle', 0.0))

        # Remover dados antigos
        while self.time_history and (current_time - self.time_history[0]) > self.time_window:
            self.time_history.popleft()
            for sid in self.sensors.keys():
                self.voltage_histories[sid].popleft()
                if sid in self.angle_histories:
                    self.angle_histories[sid].popleft()
                if sid in self.force_histories:
                    self.force_histories[sid].popleft()
            self.goniometer_history.popleft()

        times = [t - self.time_history[0] for t in self.time_history]

        # Atualizar linhas de voltagem sempre
        for sid in self.sensors.keys():
            if sid in self.displayed_sensors:
                self.voltage_lines[sid].set_data(times, self.voltage_histories[sid])
                self.voltage_lines[sid].set_visible(True)
            else:
                self.voltage_lines[sid].set_visible(False)

        # Agora dependendo do modo
        if self.plot_mode == "flex":
            # Ajustar labels do modo flex
            self.set_flex_mode_labels()
            # Somente flex e goniômetro
            # angle_lines visíveis se no displayed_sensors
            for sid in self.angle_histories.keys():
                if sid in self.displayed_sensors:
                    self.angle_lines[sid].set_data(times, self.angle_histories[sid])
                    self.angle_lines[sid].set_visible(True)
                else:
                    self.angle_lines[sid].set_visible(False)

            # force_lines invisíveis
            for sid in self.force_histories.keys():
                self.force_lines[sid].set_visible(False)

            # goniômetro visível se marcado
            if 'goniometer' in self.displayed_sensors:
                self.line_goniometer_angle.set_data(times, self.goniometer_history)
                self.line_goniometer_angle.set_visible(True)
            else:
                self.line_goniometer_angle.set_visible(False)

        else:
            # Modo fsr
            self.set_fsr_mode_labels()
            # Somente fsr sensors
            # force_lines
            max_force = 0
            for sid in self.force_histories.keys():
                if sid in self.displayed_sensors:
                    self.force_lines[sid].set_data(times, self.force_histories[sid])
                    self.force_lines[sid].set_visible(True)
                    # Calcular max force para ajustar limite do eixo
                    local_max = max(self.force_histories[sid]) if len(self.force_histories[sid]) > 0 else 0
                    if local_max > max_force:
                        max_force = local_max
                else:
                    self.force_lines[sid].set_visible(False)

            # angle_lines invisíveis no modo fsr
            for sid in self.angle_histories.keys():
                self.angle_lines[sid].set_visible(False)

            # goniômetro invisível no modo fsr
            self.line_goniometer_angle.set_visible(False)

            # Ajustar limite do eixo de força
            self.ax_detail.set_ylim(0, 10)

        # Atualizar legendas
        visible_handles = []
        visible_labels = []
        if self.plot_mode == "flex":
            # angle + goniômetro
            for sid in self.angle_histories.keys():
                if sid in self.displayed_sensors:
                    visible_handles.append(self.angle_lines[sid])
                    visible_labels.append(sid.upper())
            if 'goniometer' in self.displayed_sensors:
                visible_handles.append(self.line_goniometer_angle)
                visible_labels.append("GONIÔMETRO")
        else:
            # fsr mode
            for sid in self.force_histories.keys():
                if sid in self.displayed_sensors:
                    visible_handles.append(self.force_lines[sid])
                    visible_labels.append(sid.upper())

        self.fig.legends.clear()
        if visible_handles:
            self.fig.legend(visible_handles, visible_labels, loc='center', bbox_to_anchor=(0.5, 0.5), bbox_transform=self.fig.transFigure)

        self.ax_voltage.set_xlim(0, self.time_window)
        self.ax_detail.set_xlim(0, self.time_window)

        self.canvas.draw()

    def clear(self):
        """Remove all stored history and reset the plots."""
        self.time_history.clear()
        for sid in self.sensors.keys():
            self.voltage_histories[sid].clear()
            if sid in self.angle_histories:
                self.angle_histories[sid].clear()
            if sid in self.force_histories:
                self.force_histories[sid].clear()
        self.goniometer_history.clear()

        for line in self.voltage_lines.values():
            line.set_data([], [])
        for line in self.angle_lines.values():
            line.set_data([], [])
        for line in self.force_lines.values():
            line.set_data([], [])
        self.line_goniometer_angle.set_data([], [])

        self.fig.legends.clear()
        self.canvas.draw()

    def update_displayed_sensors(self, displayed_sensors):
        """Change which sensors are currently plotted."""
        self.displayed_sensors = displayed_sensors
