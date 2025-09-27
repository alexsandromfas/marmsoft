"""User interface for recording calibration data for sensors."""

import customtkinter as ctk
import threading
import csv
import time

class CalibrationManager:
    """Provide windows for creating and applying calibration curves."""

    def __init__(self, root, sensors, latest_readings):
        """Store references to widgets and sensor objects."""
        self.root = root
        self.sensors = sensors
        self.latest_readings = latest_readings

    def open_calibration_window(self, sensor_name):
        """Open a recording window for ``sensor_name``."""
        sensor = self.sensors[sensor_name]

        is_recording = False
        data_points = []

        def start_stop_recording():
            nonlocal is_recording
            if not is_recording:
                is_recording = True
                record_button.configure(text="Parar Gravação")
                data_points.clear()
                threading.Thread(target=record_data).start()
            else:
                is_recording = False
                record_button.configure(text="Iniciar Gravação")

        def record_data():
            while is_recording:
                voltage = self.latest_readings.get(f"{sensor_name}_voltage", 0.0)
                angle = self.latest_readings['goniometer_angle']
                data_points.append((voltage, angle))
                time.sleep(0.05)

        def calibrate():
            nonlocal is_recording
            is_recording = False
            record_button.configure(text="Iniciar Gravação")

            if not data_points:
                print("Nenhum dado gravado para calibração.")
                return

            data_points.sort(key=lambda x: x[1])
            csv_filename = f"calibration_{sensor_name}.csv"
            with open(csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Voltage', 'Angle'])
                writer.writerows(data_points)
            print(f"Dados de calibração salvos em {csv_filename}")

            sensor.calibrate_with_data_points(data_points)
            print(f"Calibração concluída para {sensor_name}!")
            calibration_window.destroy()

        calibration_window = ctk.CTkToplevel(self.root)
        calibration_window.title(f"Calibração - {sensor_name.upper()}")

        ctk.CTkLabel(calibration_window, text="Calibração com Múltiplos Pontos").pack(pady=10)

        record_button = ctk.CTkButton(calibration_window, text="Iniciar Gravação", command=start_stop_recording)
        record_button.pack(pady=10)

        calibrate_button = ctk.CTkButton(calibration_window, text="Calibrar", command=calibrate)
        calibrate_button.pack(pady=10)
