"""Provide basic filtering and calibration utilities for sensors."""

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
            header = next(reader, None)
            if not header:
                return False
            # Suporta modo antigo (Voltage,Angle) e genérico (x,y)
            data_points = []
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    x = float(row[0]); y = float(row[1])
                except ValueError:
                    continue
                data_points.append((x, y))
        self.calibrate_with_data_points(data_points)
        print(f"Dados de calibração carregados de {csv_filename}")
        return True

    def load_fsr_calibration_from_file(self, csv_filename: str) -> bool:
        """Load FSR calibration from a combined CSV with columns including 'tensao' and 'forca'.

        Expected header contains 'tensao' and 'forca' (case-insensitive). Builds a polynomial mapping
        voltage (tensão) -> force (força).
        """
        if not os.path.exists(csv_filename):
            print(f"Arquivo de calibração FSR {csv_filename} não encontrado.")
            return False
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return False
            cols = [h.strip().lower() for h in header]
            try:
                i_tensao = cols.index('tensao')
                i_forca = cols.index('forca')
            except ValueError:
                # tenta variantes inglesas
                try:
                    i_tensao = cols.index('voltage')
                    i_forca = cols.index('force')
                except ValueError:
                    print("Cabeçalho não possui 'tensao/forca' ou 'voltage/force'.")
                    return False
            pairs = []
            for row in reader:
                if len(row) <= max(i_tensao, i_forca):
                    continue
                try:
                    v = float(row[i_tensao]); f = float(row[i_forca])
                except ValueError:
                    continue
                pairs.append((v, f))
        if not pairs:
            print("Nenhum par válido v,f encontrado no CSV de calibração FSR.")
            return False
        self.calibrate_with_data_points(pairs)
        print(f"Calibração FSR aplicada a partir de {csv_filename}")
        return True
