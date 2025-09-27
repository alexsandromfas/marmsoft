"""Flex sensor calibration helper: fit and load polynomial calibration curves."""

from __future__ import annotations

import os
import csv
from typing import Iterable, List, Tuple, Optional, Callable

import numpy as np


class FlexCalibrador:
    """Gerenciador de calibração para sensores flex."""

    def __init__(self, grau: int = 2):
        self.grau = grau

    def ajustar_com_pontos(self, pontos: Iterable[Tuple[float, float]]) -> Optional[np.poly1d]:
        """Recebe pares (tensao, angulo) e retorna uma função polinomial de calibração.

        Mantém o mesmo comportamento do código atual (np.polyfit grau 2) e não altera E/S pública.
        """
        pares: List[Tuple[float, float]] = list(pontos)
        if not pares:
            return None
        voltages, values = zip(*pares)
        poly = np.poly1d(np.polyfit(voltages, values, deg=self.grau))
        return poly

    def carregar_de_csv(self, caminho_csv: str) -> Optional[np.poly1d]:
        """Carrega pontos de calibração de um CSV e retorna a função polinomial.

        Suporta tanto cabeçalho (ignorado) quanto arquivos apenas com duas colunas numéricas.
        Mantém compatibilidade com `SensorData.load_calibration_from_file` atual.
        """
        if not os.path.exists(caminho_csv):
            return None
        pontos: List[Tuple[float, float]] = []
        with open(caminho_csv, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            if not header:
                # Preserva comportamento antigo: sem cabeçalho, não carrega calibração
                return None
            # tenta ler todas as linhas subsequentes como floats
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    x = float(row[0]); y = float(row[1])
                except ValueError:
                    continue
                pontos.append((x, y))
        if not pontos:
            return None
        return self.ajustar_com_pontos(pontos)

    # --------------------- Persistência (CSV) ---------------------
    def salvar_pontos_csv(self, caminho_csv: str, pontos: Iterable[Tuple[float, float]]) -> None:
        """Salva pontos de calibração em CSV com cabeçalho 'Voltage,Angle'."""
        import csv, os
        os.makedirs(os.path.dirname(caminho_csv) or '.', exist_ok=True)
        with open(caminho_csv, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Voltage','Angle'])
            for x, y in pontos:
                w.writerow([x, y])

    def append_coeficientes_csv(self, caminho_csv: str, poly: np.poly1d) -> None:
        """Anexa linha '#COEFFICIENTS,c2,c1,c0' ao final do CSV."""
        import csv
        coefs = getattr(poly, 'c', None)
        if coefs is None or len(coefs) == 0:
            return
        with open(caminho_csv, 'a', newline='') as f:
            w = csv.writer(f)
            w.writerow(['#COEFFICIENTS', *[f"{c:.16g}" for c in coefs]])
