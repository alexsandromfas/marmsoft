"""Provide basic filtering and calibration utilities for sensors."""

# import numpy as np
# import csv
# import os

# class SensorData:
#     def __init__(self, alpha=0.1):
#         self.alpha = alpha  # Constante do filtro passa-baixa
#         self.filtered_value = 0  # Tensão filtrada
#         self.filtered_angle = 0  # Ângulo filtrado
#         self.calibration_function = None  # Função de calibração

#     def apply_filter(self, raw_value):
#         self.filtered_value = self.alpha * raw_value + (1 - self.alpha) * self.filtered_value
#         return self.filtered_value

#     def calibrate_with_data_points(self, data_points):
#         voltages, angles = zip(*data_points)
#         # Ajuste polinomial de grau 2 para calibração
#         self.calibration_function = np.poly1d(np.polyfit(voltages, angles, deg=2))

#     def get_angle(self, tension):
#         if self.calibration_function is None:
#             return 0
#         # Calcular ângulo usando a função de calibração
#         angle = self.calibration_function(tension)
#         # Aplicar filtro passa-baixa ao ângulo
#         self.filtered_angle = self.alpha * angle + (1 - self.alpha) * self.filtered_angle
#         return self.filtered_angle

#     def load_calibration_from_file(self, csv_filename):
#         if not os.path.exists(csv_filename):
#             print(f"Arquivo de calibração {csv_filename} não encontrado.")
#             return False
#         with open(csv_filename, 'r', newline='') as csvfile:
#             reader = csv.reader(csvfile)
#             next(reader)  # Pular o cabeçalho
#             data_points = [(float(row[0]), float(row[1])) for row in reader]
#         self.calibrate_with_data_points(data_points)
#         print(f"Dados de calibração carregados de {csv_filename}")
#         return True



import numpy as np
import csv
import os

class SensorData:
    """Store filtered readings and calibration for a single sensor."""

    def __init__(self, alpha=0.1):
        """Initialize the sensor with a smoothing factor."""
        self.alpha = alpha  # Constante do filtro passa-baixa
        self.filtered_value = 0  # Tensão filtrada
        self.filtered_angle = 0  # Ângulo filtrado
        self.filtered_force = 0  # Força filtrada (para fsr)
        self.calibration_function = None  # Função de calibração

    def apply_filter(self, raw_value):
        """Low-pass filter ``raw_value`` using ``alpha``."""
        self.filtered_value = self.alpha * raw_value + (1 - self.alpha) * self.filtered_value
        return self.filtered_value

    def calibrate_with_data_points(self, data_points):
        """Create a polynomial calibration curve from ``data_points``."""
        voltages, values = zip(*data_points)
        self.calibration_function = np.poly1d(np.polyfit(voltages, values, deg=2))

    def get_angle(self, tension):
        """Return a filtered angle computed from ``tension``."""
        if self.calibration_function is None:
            return 0
        angle = self.calibration_function(tension)
        self.filtered_angle = self.alpha * angle + (1 - self.alpha) * self.filtered_angle
        return self.filtered_angle

    def get_force(self, tension):
        """Return a filtered force value from ``tension``."""
        if self.calibration_function is None:
            # Fallback if no calibration is available
            return tension * 1000.0
        force = self.calibration_function(tension)
        self.filtered_force = self.alpha * force + (1 - self.alpha) * self.filtered_force
        return self.filtered_force

    def load_calibration_from_file(self, csv_filename):
        """Load calibration points from ``csv_filename``."""
        if not os.path.exists(csv_filename):
            print(f"Arquivo de calibração {csv_filename} não encontrado.")
            return False
        with open(csv_filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Pular o cabeçalho
            data_points = [(float(row[0]), float(row[1])) for row in reader]
        self.calibrate_with_data_points(data_points)
        print(f"Dados de calibração carregados de {csv_filename}")
        return True
