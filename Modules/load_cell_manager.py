"""Load Cell Manager

Gerencia conexão serial com a célula de carga (Arduino + HX711) enviando leituras em gramas
e oferecendo conversão para Newtons e função de tara.

Uso:
    mgr = LoadCellManager(port='COM9', baud=57600, callback=on_value)
    mgr.start()
    ...
    mgr.tare()
    mgr.stop()

O callback recebe assinatura callback(grams:int, newtons:float, timestamp:float).
"""
from __future__ import annotations

import threading, time
from typing import Optional, Callable

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore

GRAM_TO_NEWTON = 0.00980665  # 1 g ≈ 0.00980665 N (massa*g simplificado)


class LoadCellManager:
    def __init__(self, port: str, baud: int = 57600, callback: Optional[Callable[[int, float, float], None]] = None, timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.callback = callback
        self._ser: Optional[serial.Serial] = None  # type: ignore
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_grams: int = 0
        self.last_newtons: float = 0.0
        self.connected = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._close()

    def _open(self):
        if serial is None:
            return
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            self.connected = True
        except Exception:
            self._ser = None
            self.connected = False

    def _close(self):
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None
        self.connected = False

    def tare(self):  # pragma: no cover (depende do hardware)
        if self._ser and self._ser.is_open:
            try:
                self._ser.write(b't')
            except Exception:
                pass

    def _run(self):  # pragma: no cover (hardware loop)
        self._open()
        last_reopen = 0.0
        while not self._stop_evt.is_set():
            if not self._ser:
                if time.time() - last_reopen > 2.0:
                    self._open(); last_reopen = time.time()
                time.sleep(0.2)
                continue
            try:
                line = self._ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue
                try:
                    g = int(float(line))
                except ValueError:
                    continue
                self.last_grams = g
                self.last_newtons = g * GRAM_TO_NEWTON
                if self.callback:
                    self.callback(g, self.last_newtons, time.time())
            except Exception:
                # assume desconexão e tenta de novo
                self._close()
                time.sleep(0.5)

__all__ = ["LoadCellManager", "GRAM_TO_NEWTON"]
