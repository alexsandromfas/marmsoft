"""Real-time plotting test for Arduino Nano scale (HX711) on COM9.

Standalone (isolated) script: does not import project modules.

Expected Arduino sketch output: a single integer per line (grams) at 57600 baud every ~100 ms.

Features:
- Auto-detect (default COM9, override with --port)
- Graceful reconnect if device temporarily unavailable
- Real-time Matplotlib plot with rolling window
- Optional CSV logging (--log file.csv)
- Keyboard shortcuts in the plot window:
    t : send 't' to Arduino to tare
    q or ESC : quit
- Basic stats (min/mean/max, last value) displayed in plot title
teste
teste
teste

Usage (from repository root):
    python -m tests.scale_realtime           # uses COM9
    python -m tests.scale_realtime --port COM7 --baud 57600 --window 300
    python -m tests.scale_realtime --log pesos.csv

Requirements: pyserial, matplotlib, numpy
"""
from __future__ import annotations

import argparse
import threading
import time
import sys
import queue
import csv
from dataclasses import dataclass
from typing import Optional, List

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

try:
    import serial  # type: ignore
    from serial import SerialException  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception as e:  # pragma: no cover
    print("pyserial não encontrado. Instale com: pip install pyserial")
    raise


def list_available_ports(full: bool = False):
    """Return list of serial port info objects (pyserial list_ports)."""
    try:
        ports = list(list_ports.comports())  # type: ignore
    except Exception:
        return [] if full else []
    return ports


def classify_port(p) -> Optional[str]:  # type: ignore
    """Heuristic classification string if this port looks like an Arduino Nano / HX711 interface.

    Heuristics:
      - Description or manufacturer contains: 'arduino', 'wch', 'ch340', 'ftdi'
      - HWID contains known VID/PID pairs (e.g., 1A86:7523 for CH340, 0403:6001 for FTDI)
    Returns a short reason string or None.
    """
    txt = ' '.join([str(getattr(p, a, '') or '') for a in ('description','manufacturer','product','hwid')]).lower()
    if any(k in txt for k in ('arduino','ch340','wchusb','wch','ftdi')):
        if 'ch340' in txt or 'wch' in txt:
            return 'Possível Arduino (CH340)'
        if 'ftdi' in txt:
            return 'Possível Arduino (FTDI)'
        if 'arduino' in txt:
            return 'Arduino identificado'
        return 'Provável conversor USB-Serial'
    # VID/PID fallback patterns
    hwid = (getattr(p, 'hwid', '') or '').lower()
    if any(v in hwid for v in ('1a86:7523','0403:6001')):
        return 'VID/PID típico de Arduino/Conversor'
    return None


def probe_weight_stream(port: str, baud: int, max_time: float = 1.2, min_samples: int = 3) -> bool:
    """Open the port briefly and try to read lines that parse as integer grams.

    Returns True if pattern matches (>= min_samples integers within plausible range)."""
    try:
        ser = serial.Serial(port, baud, timeout=0.25)
    except Exception:
        return False
    start = time.time()
    count = 0
    try:
        while time.time() - start < max_time:
            try:
                line = ser.readline().decode(errors='ignore').strip()
            except Exception:
                continue
            if not line:
                continue
            try:
                val = int(float(line))
            except ValueError:
                continue
            # Plausible grams range (reject obvious noise / huge numbers)
            if -200 <= val <= 50000:
                count += 1
                if count >= min_samples:
                    return True
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return False


@dataclass
class SerialConfig:
    port: str = "COM9"
    baud: int = 57600
    timeout: float = 1.0
    reconnect_interval: float = 2.0


class SerialReader(threading.Thread):
    """Background thread that continuously reads lines and pushes ints to a queue."""
    def __init__(self, cfg: SerialConfig, out_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.out = out_queue
        self.stop_event = stop_event
        self._ser: Optional[serial.Serial] = None  # type: ignore

    def _open(self):
        try:
            self._ser = serial.Serial(self.cfg.port, self.cfg.baud, timeout=self.cfg.timeout)
            # small flush
            time.sleep(0.2)
            if self._ser.in_waiting:
                try:
                    self._ser.reset_input_buffer()
                except Exception:
                    pass
            print(f"[Serial] Conectado em {self.cfg.port} @ {self.cfg.baud} bps")
        except Exception as e:
            print(f"[Serial] Falha ao conectar {self.cfg.port}: {e}")
            self._ser = None

    def _close(self):
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
            print("[Serial] Porta fechada")

    def run(self):  # pragma: no cover (real IO)
        while not self.stop_event.is_set():
            if not self._ser:
                self._open()
                if not self._ser:
                    # wait then retry
                    time.sleep(self.cfg.reconnect_interval)
                    continue
            try:
                line = self._ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue
                # Accept either integer or float then cast to int grams
                try:
                    val = int(float(line))
                except ValueError:
                    continue
                self.out.put((time.time(), val))
            except SerialException as e:
                print(f"[Serial] Erro de leitura: {e}; tentando reconectar...")
                self._close()
                time.sleep(self.cfg.reconnect_interval)
            except Exception as e:
                print(f"[Serial] Erro inesperado: {e}")
                time.sleep(0.2)
        self._close()

    def send_tare(self):  # pragma: no cover
        if self._ser and self._ser.is_open:
            try:
                self._ser.write(b't')
                print("[Serial] Comando tare enviado (t)")
            except Exception as e:
                print(f"[Serial] Falha enviar tare: {e}")


class RealTimePlot:
    def __init__(self, window_size: int = 300, target_fps: int = 20, y_pad: float = 50.0):
        self.window_size = window_size
        self.target_fps = target_fps
        self.y_pad = y_pad
        self.x_data: List[float] = []
        self.y_data: List[int] = []
        self._last_draw = 0.0
        self._interval = 1.0 / target_fps
        self.fig, self.ax = plt.subplots(figsize=(8, 4.5))
        self.line, = self.ax.plot([], [], lw=1.8, color='#1e88e5', label='Peso (g)')
        self.ax.set_xlabel('Tempo (s)')
        self.ax.set_ylabel('Peso (g)')
        self.ax.grid(alpha=0.25, linestyle='--')
        self.ax.legend(loc='upper left')
        self.start_t = time.time()
        # Stats text box
        self.text_box = self.ax.text(0.01, 0.98, '', transform=self.ax.transAxes,
                                     va='top', ha='left', fontsize=9,
                                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))
        # Placeholder for button (created later when serial is available)
        self._tare_button_widget: Optional[Button] = None

    def add_tare_button(self, send_tare_callback):
        """Add a Tare button to the figure (only once)."""
        if self._tare_button_widget is not None:
            return
        # Create an axes area for the button (right top corner)
        btn_ax = self.fig.add_axes([0.84, 0.86, 0.12, 0.08])  # [left, bottom, width, height]
        self._tare_button_widget = Button(btn_ax, 'Tara', color='#dddddd', hovercolor='#eeeeee')
        self._tare_button_widget.label.set_fontsize(10)
        def _clicked(_event):  # pragma: no cover
            send_tare_callback()
        self._tare_button_widget.on_clicked(_clicked)

    def on_key(self, event, serial_reader: SerialReader):  # pragma: no cover
        if event.key in ('q', 'escape'):
            plt.close(self.fig)
        elif event.key.lower() == 't':
            serial_reader.send_tare()

    def update_from_queue(self, q: queue.Queue):
        updated = False
        while True:
            try:
                t, v = q.get_nowait()
            except queue.Empty:
                break
            self.x_data.append(t - self.start_t)
            self.y_data.append(v)
            updated = True
        if not updated:
            return False
        # Trim
        if len(self.x_data) > self.window_size:
            self.x_data = self.x_data[-self.window_size:]
            self.y_data = self.y_data[-self.window_size:]
        return True

    def redraw(self):
        if not self.x_data:
            return
        self.line.set_data(self.x_data, self.y_data)
        xmin = max(0.0, self.x_data[-1] - max(5, self.window_size * 0.1))
        xmax = self.x_data[-1] + 0.2
        y_arr = np.array(self.y_data[-self.window_size:])
        ymin = float(np.min(y_arr)) - self.y_pad
        ymax = float(np.max(y_arr)) + self.y_pad
        if ymin == ymax:
            ymax = ymin + 1.0
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)
        last = y_arr[-1]
        mean = float(np.mean(y_arr))
        mx = float(np.max(y_arr))
        mn = float(np.min(y_arr))
        self.text_box.set_text(f"Último: {last:.0f} g\nMédia: {mean:.1f} g\nMin: {mn:.0f} g | Max: {mx:.0f} g")
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def loop(self, data_queue: queue.Queue, stop_event: threading.Event):  # pragma: no cover
        plt.ion()
        while not stop_event.is_set() and plt.fignum_exists(self.fig.number):
            changed = self.update_from_queue(data_queue)
            now = time.time()
            if changed and (now - self._last_draw) >= self._interval:
                self.redraw()
                self._last_draw = now
            plt.pause(0.01)
        plt.ioff()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Real-time scale plot (Arduino Nano HX711)')
    p.add_argument('--port', default='COM9', help='Porta serial. Lista interativa será exibida (a menos que --no-select).')
    p.add_argument('--baud', type=int, default=57600, help='Baud rate (default: 57600)')
    p.add_argument('--window', type=int, default=300, help='Tamanho da janela (n amostras)')
    p.add_argument('--fps', type=int, default=15, help='Taxa máxima de atualização do gráfico')
    p.add_argument('--log', default='', help='Arquivo CSV para salvar (opcional)')
    p.add_argument('--no-select', action='store_true', help='Pula seleção interativa de porta (usa diretamente --port)')
    p.add_argument('--probe', action='store_true', help='Ativa detecção ativa: abre portas e tenta identificar fluxo de pesos.')
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None):  # pragma: no cover
    args = parse_args(argv)
    # ------ Seleção interativa de porta ------
    def interactive_select(current_hint: str) -> str:
        ports = list_available_ports(full=True)
        if not ports:
            print('Nenhuma porta serial detectada. Mantendo porta informada:', current_hint)
            return current_hint
        print('\nPortas seriais disponíveis:')
        annotated = []
        for i, pinfo in enumerate(ports):
            reason = classify_port(pinfo)
            annotated.append((pinfo, reason))
        # Optional active probing
        probe_results = {}
        if args.probe:
            print('\n[Probe] Testando fluxo de dados por até 1.2s por porta...')
            for pinfo, reason in annotated:
                ok = probe_weight_stream(pinfo.device, args.baud)
                probe_results[pinfo.device] = ok
        for i, (pinfo, reason) in enumerate(annotated):
            tags = []
            if reason:
                tags.append(reason)
            if args.probe and probe_results.get(pinfo.device):
                tags.append('Fluxo peso detectado')
            tag_str = f" ({'; '.join(tags)})" if tags else ''
            print(f'  [{i}] {pinfo.device}{tag_str}')
        print('\nDigite o índice da porta desejada, ou digite o nome manualmente (ex: COM7).')
        print(f'Pressione ENTER para usar a porta atual ({current_hint}).')
        while True:
            sel = input('Seleção porta > ').strip()
            if sel == '':
                print(f'[Port] Usando {current_hint}')
                return current_hint
            # índice numérico
            if sel.isdigit():
                idx = int(sel)
                if 0 <= idx < len(annotated):
                    chosen = annotated[idx][0].device
                    print(f'[Port] Selecionado {chosen}')
                    return chosen
                else:
                    print('Índice inválido.')
                    continue
            # nome direto
            if sel in [p.device for p,_ in annotated]:
                print(f'[Port] Selecionado {sel}')
                return sel
            # permite tentar porta não listada (ex: interface recém plugada)
            confirm = input(f'Porta "{sel}" não está na lista. Tentar assim mesmo? (s/N) ').strip().lower()
            if confirm == 's':
                print(f'[Port] Usando {sel}')
                return sel
            else:
                continue

    chosen_port = args.port
    if not args.no_select:
        chosen_port = interactive_select(args.port)

    cfg = SerialConfig(port=chosen_port, baud=args.baud)
    data_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    reader = SerialReader(cfg, data_queue, stop_event)
    reader.start()

    plotter = RealTimePlot(window_size=args.window, target_fps=args.fps)
    plotter.fig.canvas.mpl_connect('key_press_event', lambda e: plotter.on_key(e, reader))
    # Add tare button (calls serial 't')
    plotter.add_tare_button(reader.send_tare)

    csv_file = None
    writer = None
    if args.log:
        try:
            csv_file = open(args.log, 'w', newline='', encoding='utf-8')
            writer = csv.writer(csv_file)
            writer.writerow(['timestamp_epoch', 'tempo_rel_s', 'peso_g'])
            print(f'[LOG] Gravando em {args.log}')
        except Exception as e:
            print(f'[LOG] Falha ao abrir {args.log}: {e}')
            writer = None

    try:
        plotter.loop(data_queue, stop_event)
    finally:
        stop_event.set()
        if csv_file:
            # drena fila final
            while not data_queue.empty():
                try:
                    ts, v = data_queue.get_nowait()
                except queue.Empty:
                    break
                if writer:
                    writer.writerow([f'{ts:.6f}', f'{ts - plotter.start_t:.3f}', v])
            csv_file.close()
        print('Encerrado.')


if __name__ == '__main__':  # pragma: no cover
    main()
