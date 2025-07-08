"""Tkinter tools for recording and analysing flex sensor tests."""

import customtkinter as ctk
import threading
import time
import csv
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class Tests:
    """Provide a UI for collecting calibration and comparison metrics."""

    def __init__(self, root, sensors, latest_readings, goniometer):
        """Create the tests window manager.

        Parameters
        ----------
        root : tkinter.Tk
            Parent window.
        sensors : dict
            Mapping of sensor identifiers to :class:`SensorData` objects.
        latest_readings : dict
            Shared dictionary where latest values are stored.
        goniometer : GoniometerManager
            Instance used to retrieve angle references.
        """
        self.root = root
        self.sensors = sensors
        self.latest_readings = latest_readings
        self.goniometer = goniometer
        self.selected_sensor = None
        self.is_recording = False
        self.recorded_data = []
        self.start_time = None
        self.sample_count = 0

    def open_tests_window(self):
        """Create and display the sensor testing window."""
        self.test_window = ctk.CTkToplevel(self.root)
        self.test_window.title("Testes dos Flex Sensors")

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.test_window)
        self.main_frame.pack(fill="both", expand=True)

        # Interface inicial: seleção do sensor
        ctk.CTkLabel(self.main_frame, text="Selecione o Flex Sensor para Teste:").pack(pady=10)

        for sensor_name in self.sensors.keys():
            sensor_button = ctk.CTkButton(
                self.main_frame, text=sensor_name.upper(),
                command=lambda s=sensor_name: self.select_sensor(s)
            )
            sensor_button.pack(pady=5)

    def select_sensor(self, sensor_name):
        """Prepare the interface to record data for ``sensor_name``."""
        # Limpa a interface atual
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.selected_sensor = sensor_name
        self.is_recording = False
        self.recorded_data = []
        self.start_time = None
        self.sample_count = 0

        # Nova interface com botões e labels
        ctk.CTkLabel(self.main_frame, text=f"Teste do {sensor_name.upper()}").pack(pady=10)

        self.record_button = ctk.CTkButton(self.main_frame, text="Gravar", command=self.start_recording)
        self.record_button.pack(pady=5)

        self.stop_button = ctk.CTkButton(self.main_frame, text="Parar Gravação", command=self.stop_recording, state="disabled")
        self.stop_button.pack(pady=5)

        self.show_button = ctk.CTkButton(self.main_frame, text="Mostrar Gráficos e Métricas", command=self.show_results, state="disabled")
        self.show_button.pack(pady=5)

        self.time_label = ctk.CTkLabel(self.main_frame, text="Tempo: 0.00 s")
        self.time_label.pack(pady=5)

        self.sample_label = ctk.CTkLabel(self.main_frame, text="Amostras coletadas: 0")
        self.sample_label.pack(pady=5)

        self.update_timer()

    def start_recording(self):
        """Begin collecting sensor data until ``stop_recording`` is called."""
        if not self.is_recording:
            self.is_recording = True
            self.record_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.start_time = time.time()
            self.sample_count = 0
            self.recorded_data = []
            self.record_data()

    def stop_recording(self):
        """Finish the current recording session and save the data."""
        if self.is_recording:
            self.is_recording = False
            self.record_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.show_button.configure(state="normal")
            self.save_data_to_csv()

    def record_data(self):
        """Append a single sample of sensor and goniometer data."""
        if self.is_recording:
            current_time = time.time() - self.start_time
            flex_voltage = self.latest_readings[f"{self.selected_sensor}_voltage"]
            flex_angle = self.latest_readings[f"{self.selected_sensor}_angle"]
            goniometer_angle = self.latest_readings['goniometer_angle']
            self.recorded_data.append({
                'time': current_time,
                'flex_voltage': flex_voltage,
                'flex_angle': flex_angle,
                'goniometer_angle': goniometer_angle
            })
            self.sample_count += 1
            # Agendar próxima leitura
            self.main_frame.after(50, self.record_data)  # Ajuste o intervalo conforme necessário

    def update_timer(self):
        """Update time and sample counters during recording."""
        if self.is_recording:
            elapsed_time = time.time() - self.start_time
            self.time_label.configure(text=f"Tempo: {elapsed_time:.2f} s")
            self.sample_label.configure(text=f"Amostras coletadas: {self.sample_count}")
        self.main_frame.after(100, self.update_timer)

    def save_data_to_csv(self):
        """Persist recorded data to a CSV file in ``data_tests``."""
        # Criar diretório de dados se não existir
        data_dir = 'data_tests'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        filename = f'{data_dir}/test_{self.selected_sensor}_{int(time.time())}.csv'
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['time', 'flex_voltage', 'flex_angle', 'goniometer_angle']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for data_point in self.recorded_data:
                writer.writerow(data_point)
        print(f"Dados salvos em {filename}")
        self.data_filename = filename  # Salva o nome do arquivo para uso posterior

    def show_results(self):
        """Display plots and metrics calculated from the recorded data."""
        if not self.recorded_data:
            print("Nenhum dado para mostrar.")
            return

        # Extrair dados
        times = [d['time'] for d in self.recorded_data]
        flex_voltages = [d['flex_voltage'] for d in self.recorded_data]
        flex_angles = [d['flex_angle'] for d in self.recorded_data]
        goniometer_angles = [d['goniometer_angle'] for d in self.recorded_data]

        # Calcular métricas
        flex_array = np.array(flex_angles)
        goniometer_array = np.array(goniometer_angles)
        mae = np.mean(np.abs(flex_array - goniometer_array))
        rmse = np.sqrt(np.mean((flex_array - goniometer_array) ** 2))
        pearson_corr = np.corrcoef(flex_array, goniometer_array)[0, 1]
        # Correlação cruzada
        cross_corr = np.correlate(
            flex_array - np.mean(flex_array),
            goniometer_array - np.mean(goniometer_array),
            mode='full'
        )
        max_cross_corr = np.max(cross_corr)

        # Janela para resultados
        result_window = ctk.CTkToplevel(self.test_window)
        result_window.title("Resultados do Teste")

        # Configurar a janela para tela cheia
        result_window.state('zoomed')

        # Exibir métricas
        metrics_text = f"""Métricas:
MAE: {mae:.2f}
RMSE: {rmse:.2f}
Correlação de Pearson: {pearson_corr:.2f}
Correlação Cruzada (máximo): {max_cross_corr:.2f}
"""
        metrics_label = ctk.CTkLabel(result_window, text=metrics_text, font=("Arial", 14))
        metrics_label.pack(pady=10)

        # Criar frames para organização dos gráficos
        plots_frame = ctk.CTkFrame(result_window)
        plots_frame.pack(fill='both', expand=True)

        # Criar a figura do Matplotlib
        fig = Figure(figsize=(12, 6), dpi=100)

        # Gráfico 1: Ângulo do flex sensor vs Tensão do flex sensor
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.plot(flex_voltages, flex_angles, '.', label='Ângulo vs Tensão')
        ax1.set_title('Ângulo do Flex Sensor vs Tensão')
        ax1.set_xlabel('Tensão (V)')
        ax1.set_ylabel('Ângulo (°)')
        ax1.legend()
        ax1.grid(True)

        # Gráfico 2: Ângulo do flex sensor e Ângulo do goniômetro vs Tempo
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.plot(times, flex_angles, label='Ângulo Flex Sensor')
        ax2.plot(times, goniometer_angles, label='Ângulo Goniômetro')
        ax2.set_title('Ângulo do Flex Sensor e Goniômetro vs Tempo')
        ax2.set_xlabel('Tempo (s)')
        ax2.set_ylabel('Ângulo (°)')
        ax2.legend()
        ax2.grid(True)

        # Adicionar a figura ao canvas do Tkinter
        canvas = FigureCanvasTkAgg(fig, master=plots_frame)
        canvas.get_tk_widget().pack(fill='both', expand=True)
        canvas.draw()

        # Botão para fechar a janela de resultados
        close_button = ctk.CTkButton(result_window, text="Fechar", command=result_window.destroy)
        close_button.pack(pady=10)
