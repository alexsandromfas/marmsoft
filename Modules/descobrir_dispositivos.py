"""Utility script to list nearby BLE devices."""

import asyncio
from bleak import BleakScanner

async def discover_devices():
    """Print available BLE device names and addresses."""
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Nome: {device.name}, Endereço: {device.address}")

asyncio.run(discover_devices())
