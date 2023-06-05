#!/usr/bin/python3
import asyncio

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

ADDRESS = "3C:38:F4:AE:B6:3D"

CMD_CHARACTERISTIC = "0000ff01-0000-1000-8000-00805f9b34fb"
NOTIF_CHARACTERISTIC = "25047e64-657c-4856-afcf-e315048a965b"


def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """Simple notification handler which prints the data received."""
    print(characteristic, data)


async def main():
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        paired = await client.pair(protection_level=2)
        print(f"Paired: {paired}")

        if client._backend.__class__.__name__ == "BleakClientBlueZDBus":
            await client._backend._acquire_mtu()
        print("MTU:", client.mtu_size)
        await asyncio.sleep(3.0)

        print("Starting tracker")
        await client.write_gatt_char(CMD_CHARACTERISTIC, b'\x7e\x03\x18\xd6\x01\x00\x00')
        await asyncio.sleep(2.0)
        await client.start_notify(NOTIF_CHARACTERISTIC, notification_handler)
        await asyncio.sleep(30.0)


if __name__ == "__main__":
    asyncio.run(main())