"""FSR dynamic calibration manager (tensão -> força) usando célula de carga.

Este módulo foi simplificado: remove fluxo antigo de importação de referência externa (Instron)
e passa a fornecer utilidades para:
 - Ajustar curva tensão->força (polinomial 2º grau ou racional quadrática com F(0)=0)
 - Persistir / carregar CSV com pontos (tensao,forca) e metadados (#MODEL, #COEFFICIENTS)
 - Carregar função de calibração para uso em tempo real.
"""

from __future__ import annotations

import os
import csv
from typing import Tuple, List, Dict, Optional

import numpy as np


class FSRCalibrador:
    """Gerencia calibração dinâmica de FSR (registro de pares tensão/força e ajuste)."""

    def __init__(self):
        pass

    @staticmethod
    def rational_zero(v, a, b, d, e):
        """Rational model with F(0)=0 forced: F(V) = (a V^2 + b V) / (d V + e)."""
        return (a * np.square(v) + b * v) / (d * v + e)

    # Fluxo de importação externo removido.

    def carregar_calibracao_csv(self, csv_filename: str) -> Optional[callable]:
        """Carrega uma calibração FSR a partir de CSV combinado.

        Preferência:
        1) Se houver linhas de metadados com '#MODEL' e '#COEFFICIENTS', monta a função
           diretamente desses coeficientes.
        2) Caso contrário, tenta carregar pontos (tensao, forca) e ajustar polinômio de 2º grau.
        """
        import csv
        if not os.path.exists(csv_filename):
            return None
        model = None
        coefs: Optional[List[float]] = None
        pares: List[Tuple[float, float]] = []
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return None
            cols = [h.strip().lower() for h in header]
            # tenta encontrar índices de colunas de dados (tensao/forca)
            i_tensao = cols.index('tensao') if 'tensao' in cols else (cols.index('voltage') if 'voltage' in cols else -1)
            i_forca  = cols.index('forca')  if 'forca'  in cols else (cols.index('force')   if 'force'   in cols else -1)
            for row in reader:
                if not row:
                    continue
                tag = str(row[0]).strip()
                if tag.upper() == '#MODEL' and len(row) >= 2:
                    model = row[1].strip().lower()
                    continue
                if tag.upper() == '#COEFFICIENTS' and len(row) >= 2:
                    try:
                        coefs = [float(c) for c in row[1:] if str(c).strip() != '']
                    except ValueError:
                        coefs = None
                    continue
                # dados normais
                if i_tensao >= 0 and i_forca >= 0 and len(row) > max(i_tensao, i_forca):
                    try:
                        v = float(row[i_tensao]); ff = float(row[i_forca])
                    except ValueError:
                        continue
                    pares.append((v, ff))
        # Se houver coeficientes + modelo, monta função diretamente
        if model and coefs:
            if model in ('poly2', 'polynomial2', 'polynomial'):
                return np.poly1d(coefs)
            if model in ('rational_q', 'rational', 'rational_zero') and len(coefs) >= 4:
                a, b, d, e = coefs[:4]
                return lambda v: FSRCalibrador.rational_zero(np.asarray(v), a, b, d, e)
        # Fallback: ajustar polinômio 2º de pontos
        if not pares:
            return None
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

    def salvar_calibracao(self, caminho_csv: str, tensoes: List[float], forcas: List[float], model: str, coefs: List[float]) -> None:
        """Salva pares tensão/força e metadados da curva."""
        os.makedirs(os.path.dirname(caminho_csv) or '.', exist_ok=True)
        with open(caminho_csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['tensao','forca'])
            for v, ff in zip(tensoes, forcas):
                w.writerow([f"{v:.6f}", f"{ff:.6f}"])
            w.writerow(['#MODEL', model])
            if coefs:
                w.writerow(['#COEFFICIENTS', *[f"{c:.16g}" for c in coefs]])

    def append_coeficientes_csv(self, caminho_csv: str, poly: np.poly1d) -> None:
        import csv
        coefs = getattr(poly, 'c', None)
        if coefs is None or len(coefs) == 0:
            return
        with open(caminho_csv, 'a', newline='') as f:
            w = csv.writer(f)
            w.writerow(['#COEFFICIENTS', *[f"{c:.16g}" for c in coefs]])

    # --------------------- Ajuste (fit) de curvas ---------------------
    def ajustar_curva(self, v: List[float], f: List[float], model: str = 'poly2') -> Tuple[callable, List[float], str]:
        """Ajusta curva tensão->força.

        model:
          - 'poly2': polinomial de 2º grau (np.polyfit)
          - 'rational_q': racional quadrática com F(0)=0, parâmetros [a,b,d,e]

        Retorna (funcao, coeficientes, model).
        """
        v_arr = np.asarray(v, dtype=float)
        f_arr = np.asarray(f, dtype=float)
        # Limpeza básica: remover pontos muito próximos de zero (repouso) para melhor ajuste
        mask_nonzero = ~((v_arr <= 0.01) & (f_arr <= 0.01))
        v1 = v_arr[mask_nonzero]; f1 = f_arr[mask_nonzero]
        # Ordenar
        order = np.argsort(v1)
        v1 = v1[order]; f1 = f1[order]
        # Ancorar origem (0,0)
        if v1.size == 0 or v1[0] > 1e-6:
            v_fit = np.concatenate([[0.0], v1])
            f_fit = np.concatenate([[0.0], f1])
        else:
            v_fit = v1; f_fit = f1
        m = model.lower().strip()
        if m == 'rational_q':
            try:
                import importlib
                curve_fit = importlib.import_module('scipy.optimize').curve_fit
            except Exception:
                # fallback para poly2 se scipy indisponível
                coefs = np.polyfit(v_fit, f_fit, deg=2)
                func = np.poly1d(coefs)
                return func, list(map(float, coefs)), 'poly2'
            p0 = [0.1, 0.1, 0.1, 1.0]
            params, _cov = curve_fit(FSRCalibrador.rational_zero, v_fit, f_fit, p0=p0, maxfev=30000)
            a, b, d, e = [float(x) for x in params]
            func = lambda vv: FSRCalibrador.rational_zero(np.asarray(vv), a, b, d, e)
            return func, [a, b, d, e], 'rational_q'
        else:
            # poly2
            coefs = np.polyfit(v_fit, f_fit, deg=2)
            func = np.poly1d(coefs)
            return func, list(map(float, coefs)), 'poly2'

