"""Wrapper around ``BleakClient`` for handling notifications."""

from bleak import BleakClient
import asyncio

class BLEManager:
    """Manage a BLE connection in a background asyncio loop (robusto ao desligar)."""

    def __init__(self, address, characteristic_uuid, notification_handler):
        self.address = address
        self.characteristic_uuid = characteristic_uuid
        self.notification_handler = notification_handler
        self.client: BleakClient | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.is_running = False
        self._connected = False

    async def _run(self):
        print(f"[BLE] Conectando {self.address} ...")
        try:
            self.client = BleakClient(self.address)
            await self.client.connect()
            # Em versões recentes do Bleak, is_connected é propriedade booleana
            if not bool(self.client.is_connected):
                print("[BLE] Falha ao conectar.")
                return
            await self.client.start_notify(self.characteristic_uuid, self.notification_handler)
            self._connected = True
            self.is_running = True
            print("[BLE] Notificações iniciadas.")
            while self.is_running:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[BLE] Erro: {e}")
        finally:
            await self._cleanup()

    async def _cleanup(self):
        if self.client:
            try:
                if self._connected:
                    try:
                        await self.client.stop_notify(self.characteristic_uuid)
                    except Exception:
                        pass
                if bool(self.client.is_connected):
                    await self.client.disconnect()
            except Exception as e:
                print(f"[BLE] Erro ao desconectar: {e}")
        self._connected = False
        print("[BLE] Loop finalizado.")

    def start_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run())
        finally:
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self.loop.close()

    def stop_loop(self):
        self.is_running = False
        if self.loop and not self.loop.is_closed():
            # Não chamar stop prematuramente; deixar _run sair naturalmente
            pass
