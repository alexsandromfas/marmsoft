"""Provide basic filtering and calibration utilities for sensors.

This module now delegates calibration fitting/loading responsibilities to
specific calibrator managers without changing the public API/behavior.
"""

import numpy as np
import csv
import os
from typing import List, Tuple

from .flex_calibrador import FlexCalibrador
from .fsr_calibrador import FSRCalibrador

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
        """Create a polynomial calibration curve from ``data_points``.

        Behavior preserved: degree-2 polynomial fit as before, now via FlexCalibrador.
        """
        flex_cal = FlexCalibrador(grau=2)
        func = flex_cal.ajustar_com_pontos(data_points)
        self.calibration_function = func

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
        """Load calibration for Flex from ``csv_filename``.

        Prefer saved polynomial coefficients (row starting with '#COEFFICIENTS')
        to avoid re-fitting; if not present, fall back to fitting points as before.
        """
        if not os.path.exists(csv_filename):
            print(f"Arquivo de calibração {csv_filename} não encontrado.")
            return False
        # Primeiro, tenta encontrar linha de coeficientes
        coefs = None
        try:
            with open(csv_filename, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)
                # varre todas as linhas e usa a última ocorrência encontrada
                for row in reader:
                    if not row:
                        continue
                    tag = str(row[0]).strip()
                    if tag.upper() == '#COEFFICIENTS' and len(row) >= 2:
                        try:
                            cand = [float(c) for c in row[1:] if c is not None and str(c).strip() != '']
                            if cand:
                                coefs = cand
                        except ValueError:
                            # ignora linhas inválidas
                            pass
        except Exception:
            coefs = None
        if coefs:
            # Constrói polinômio diretamente a partir dos coeficientes salvos
            self.calibration_function = np.poly1d(coefs)
            print(f"Dados de calibração (coeficientes) carregados de {csv_filename}")
            return True
        # Sem coeficientes – mantém compatibilidade lendo pontos e ajustando via FlexCalibrador
        flex_cal = FlexCalibrador(grau=2)
        func = flex_cal.carregar_de_csv(csv_filename)
        if func is None:
            return False
        self.calibration_function = func
        print(f"Dados de calibração carregados de {csv_filename}")
        return True

    def load_fsr_calibration_from_file(self, csv_filename: str) -> bool:
        """Load FSR calibration from a combined CSV with columns including 'tensao' and 'forca'.

        Behavior preserved; internally delegates parsing/fit to FSRCalibrador and uses a degree-2 fit.
        """
        if not os.path.exists(csv_filename):
            print(f"Arquivo de calibração FSR {csv_filename} não encontrado.")
            return False
        fsr_cal = FSRCalibrador()
        func = fsr_cal.carregar_calibracao_csv(csv_filename)
        if func is None:
            print("Nenhum par válido v,f encontrado no CSV de calibração FSR.")
            return False
        self.calibration_function = func
        print(f"Calibração FSR aplicada a partir de {csv_filename}")
        return True
