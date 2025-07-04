# Modules/ble_manager.py

from bleak import BleakClient
import asyncio

class BLEManager:
    def __init__(self, address, characteristic_uuid, notification_handler):
        self.address = address
        self.characteristic_uuid = characteristic_uuid
        self.notification_handler = notification_handler
        self.client = None
        self.loop = None
        self.is_running = False

    async def connect(self):
        print(f"Tentando conectar ao dispositivo: {self.address}")
        async with BleakClient(self.address) as client:
            self.client = client
            try:
                await client.start_notify(self.characteristic_uuid, self.notification_handler)
                print("Conectado ao dispositivo BLE e recebendo notificações.")
                self.is_running = True
                while self.is_running:
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Erro na conexão BLE: {e}")

    def start_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.connect())
        except Exception as e:
            print(f"Erro no loop BLE: {e}")
        finally:
            self.loop.close()

    def stop_loop(self):
        self.is_running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
