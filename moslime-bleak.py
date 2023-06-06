import asyncio
from asyncio import sleep, Task, Event
from typing import List, Union

from bleak import BleakClient
from sanic import Sanic, response
from sanic.server import AsyncioServer

class SlimeNetThread:

    # polls the imu queue and handles dispatch at fixed rates and some errors

    def __init__(self, packetThread) -> None:
        self.packetThread = packetThread

    async def run(self) -> None:
        await self.packetThread.readyToTransmit.wait()
        dumbIdiotThing = (1000/50)/1000  # <- stupid
        while True:
            print('+ Current data to be sent to Slime: +')
            for i, buffer in enumerate(await self.packetThread.getBuffer()):
                print('IMU ' + str(i) + ':', None if buffer is None else bytes.hex(bytes(buffer)))
            print('=====')
            await sleep(dumbIdiotThing)


class MocopiCommThread:

    # bt handling and speaking mocopi commands, imu data queue
    # https://bleak.readthedocs.io/en/latest/backends/linux.html?highlight=asyncio#parallel-access

    def __init__(self) -> None:
        self.notifiers = {}
        self.assignments = {}
        self.readyToTransmit = Event()
        self.imuData: List[Union[bytearray, None]] = []  # not threadsafe but fine bc the queue is lossy by design

    async def add_tracker(self, mac: str):
        client = BleakClient(mac)
        macBytes = bytes.fromhex(mac.replace(':', ''))
        await client.connect()
        print('connected', mac)
        # await client.pair(protection_level=1)
        assignedNumber = len(self.imuData)
        self.assignments[macBytes] = assignedNumber
        self.imuData.append(None)
        self.notifiers[macBytes] = lambda char, data: self.imuData.__setitem__(assignedNumber, data)
        print('start', mac)
        await client.write_gatt_char("0000ff01-0000-1000-8000-00805f9b34fb", b'\x7e\x03\x18\xd6\x01\x00\x00')
        print('begin notif', mac)
        await client.start_notify("25047e64-657c-4856-afcf-e315048a965b", self.notifiers.get(macBytes))
        print('streaming from', mac)

    async def run(self) -> None:
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Head
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Wrist L
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Wrist R
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Hip
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Ankle L
        await self.add_tracker("3C:38:F4:xx:xx:xx")  # Ankle R
        print('ALL TRACKERS ADDED')
        self.readyToTransmit.set()
        while True:
            await sleep(10)

    async def getBuffer(self):  # retrieve data from lossy buffer for serialization
        return self.imuData.copy()


class MoslimePcapThread:

    def __init__(self) -> None:
        pass

    async def run(self) -> None:
        while True:
            print('hello from mopcap')
            await sleep(1)


webHandler: Sanic = Sanic("MoSlime")


@webHandler.route("/")
async def test(request):
    return response.html(
        "<html>" +
        "   <h1>= Mocopi Tracker Assignment =</h1>" +
        "   <h2>IMPORTANT: When a Mocopi tracker is turned on, the center will flash blue and you will have ~30 seconds"
        " to assign it using the serial number on the back.<br>If you do not assign the tracker within the time frame"
        " and/or the serial number is not listed, turn the tracker off, back on, then refresh the page.</h2>" +
        "   <h3>Tracker 1 (\"Head\" or Any)</h3>" +
        "   <form action=\"/\" method=\"POST\">" +
        "       <select name=\"assign1\">" +
        "           <option value=\"\">Select a tracker</option>" +
        "           <option value=\"0FFBB\">0FFBB</option>" +
        "       </select>" +
        "       <input type=\"submit\" value=\"Apply/Assign\" />" +
        "   </form>" +
        "</html>"
    )


async def main():
    webThread: AsyncioServer
    if webThread := await webHandler.create_server(port=8080, host="0.0.0.0", return_asyncio_server=True):
        mocopiCommThread = MocopiCommThread()
        slimeNetThread = SlimeNetThread(mocopiCommThread)  # can also use the pcap class as it'll be inheriting
        await asyncio.gather(mocopiCommThread.run(), slimeNetThread.run(), webThread.startup())
        await webThread.serve_forever()


if __name__ == "__main__":
    asyncio.new_event_loop()
    asyncio.run(main())