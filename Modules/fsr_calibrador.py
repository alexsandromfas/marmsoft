"""FSR calibration routines: import, clean, align and export force reference data."""

from __future__ import annotations

import os
import csv
from typing import Tuple, List, Dict, Optional

import numpy as np


class FSRCalibrador:
    """Manage calibration for force sensing resistors (FSR)."""

    def __init__(self):
        # future: parameters for thresholds/smoothing can be passed here
        self.noise_threshold_n = 0.005  # valores absolutos abaixo serão truncados para 0 N
        self.time_round_decimals = 3    # arredondar tempo para 0.001 s

    def tratar_referencia(self, csv_path: str, out_dir: str = 'calibracao_fsr/forca_tratados') -> Tuple[List[float], List[float], str]:
        """Importa um CSV bruto de força, limpa e salva a versão tratada.

        Regras de limpeza adotadas (robustas ao formato do arquivo exemplo):
        - Detecta o cabeçalho de dados na linha que começa com 'Tempo;'.
        - Usa colunas 'Tempo' e 'Carga compressiva' (ou 'Carga' se não houver a primeira).
        - Converte vírgula decimal para ponto e remove aspas.
        - Força em Newtons é convertida para valor absoluto e pequenos ruídos (< 0.005 N) viram 0.
        - Tempo é arredondado para 0.001 s; amostras com o mesmo tempo arredondado são agregadas por média.
        - Salva arquivo tratado como CSV (separador vírgula, ponto decimal) com cabeçalho: tempo,forca.

        Retorna (tempos, forcas, caminho_arquivo_tratado).
        """
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(csv_path)

        # Lê todo o arquivo como texto para tratar codificação e delimitadores não usuais
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [ln.strip() for ln in f if ln.strip()]

        # Encontrar linha de cabeçalho (dados) e próxima linha com unidades (ignorada)
        header_idx = None
        for i, ln in enumerate(lines):
            if ln.startswith('Tempo;'):
                header_idx = i
                break
        if header_idx is None or header_idx + 2 >= len(lines):
            raise ValueError('Cabeçalho de dados "Tempo;" não encontrado no arquivo de referência.')

        headers = [h.strip().strip('"') for h in lines[header_idx].split(';')]
        data_lines = lines[header_idx + 2:]

        # Determinar índices das colunas relevantes
        def _find_col(*candidates: str) -> int:
            for cand in candidates:
                if cand in headers:
                    return headers.index(cand)
            return -1

        t_idx = _find_col('Tempo')
        f_idx = _find_col('Carga compressiva', 'Carga')
        if t_idx < 0 or f_idx < 0:
            raise ValueError('Colunas de Tempo e/ou Carga não encontradas no arquivo de referência.')

        # Parse linhas de dados com vírgula decimal
        times_raw: List[float] = []
        forces_raw: List[float] = []
        for ln in data_lines:
            parts = [p.strip().strip('"') for p in ln.split(';')]
            if len(parts) <= max(t_idx, f_idx):
                continue
            t_str = parts[t_idx].replace('.', '').replace(',', '.')  # garante ponto decimal
            f_str = parts[f_idx].replace('.', '').replace(',', '.')
            try:
                t = float(t_str)
                f = abs(float(f_str))
            except ValueError:
                continue
            # Ruído muito pequeno vira zero
            if abs(f) < self.noise_threshold_n:
                f = 0.0
            times_raw.append(t)
            forces_raw.append(f)

        if not times_raw:
            raise ValueError('Nenhuma linha de dados válida encontrada no arquivo de referência.')

        # Arredondamento de tempo e agregação por média
        from collections import defaultdict
        buckets: Dict[float, List[float]] = defaultdict(list)
        for t, f in zip(times_raw, forces_raw):
            tr = round(t, self.time_round_decimals)
            buckets[tr].append(f)
        times = sorted(buckets.keys())
        forces = [sum(buckets[t]) / len(buckets[t]) for t in times]

        # Salvar arquivo tratado
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.basename(csv_path)
        name, _ = os.path.splitext(base)
        out_path = os.path.join(out_dir, f"{name}_tratado.csv")
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['tempo', 'forca'])
            for t, fv in zip(times, forces):
                w.writerow([f"{t:.3f}", f"{fv:.6f}"])

        return times, forces, out_path

    def carregar_calibracao_csv(self, csv_filename: str) -> Optional[np.poly1d]:
        """Lê um CSV combinado com colunas 'tensao' e 'forca' (ou 'voltage'/'force') e
        retorna uma função polinomial de calibração (grau 2) mapeando tensão -> força.

        Compatível com o comportamento atual usado em SensorData.load_fsr_calibration_from_file.
        """
        import csv
        if not os.path.exists(csv_filename):
            return None
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return None
            cols = [h.strip().lower() for h in header]
            try:
                i_tensao = cols.index('tensao')
                i_forca = cols.index('forca')
            except ValueError:
                try:
                    i_tensao = cols.index('voltage')
                    i_forca = cols.index('force')
                except ValueError:
                    return None
            pares: List[Tuple[float, float]] = []
            for row in reader:
                if len(row) <= max(i_tensao, i_forca):
                    continue
                try:
                    v = float(row[i_tensao]); f = float(row[i_forca])
                except ValueError:
                    continue
                pares.append((v, f))
        if not pares:
            return None
        # ajuste polinomial de 2º grau como no código original
        voltages, values = zip(*pares)
        return np.poly1d(np.polyfit(voltages, values, deg=2))

    # --------------------- Alinhamento e Persistência (CSV) ---------------------
    def alinhar_pelo_pico(self, t_forca: List[float], f: List[float], t_tensao: List[float], v: List[float]) -> Tuple[List[float], List[float], float]:
        """Alinha séries pelo pico: retorna (t_tensao_alinhado, v, offset)."""
        import numpy as _np
        if not (t_forca and f and t_tensao and v):
            return t_tensao, v, 0.0
        iF = int(_np.argmax(f)); iV = int(_np.argmax(v))
        tF_peak = t_forca[iF]; tV_peak = t_tensao[iV]
        offset = tF_peak - tV_peak
        t_shifted = [t + offset for t in t_tensao]
        return t_shifted, v, offset

    def exportar_calibracao_combinada(self, out_path: str, t_sel: List[float], v_sel: List[float], f_interp: List[float]) -> None:
        import csv, os
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        with open(out_path, 'w', newline='', encoding='utf-8') as g:
            w = csv.writer(g)
            w.writerow(['tempo','tensao','forca'])
            for t_i, vv, ff in zip(t_sel, v_sel, f_interp):
                w.writerow([f"{t_i:.3f}", f"{vv:.6f}", f"{ff:.6f}"])

    def append_coeficientes_csv(self, caminho_csv: str, poly: np.poly1d) -> None:
        import csv
        coefs = getattr(poly, 'c', None)
        if coefs is None or len(coefs) == 0:
            return
        with open(caminho_csv, 'a', newline='') as f:
            w = csv.writer(f)
            w.writerow(['#COEFFICIENTS', *[f"{c:.16g}" for c in coefs]])

