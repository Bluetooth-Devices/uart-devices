import asyncio
import logging

from uart_devices import BluetoothDevice, NotAUARTDeviceError

logging.basicConfig(level=logging.INFO)
logging.getLogger("usb_devices").setLevel(logging.DEBUG)


async def run() -> None:
    """Run the example."""
    loop = asyncio.get_running_loop()
    for i in range(0, 9):
        dev = BluetoothDevice(i)
        try:
            await loop.run_in_executor(None, dev.setup)
        except NotAUARTDeviceError:
            print(f"hci{i} is not a USB device")
            continue
        except FileNotFoundError:
            print(f"hci{i} not found")
            continue
        assert dev.uart_device is not None  # noqa: S101
        print(
            f"hci{i} manufacturer: {dev.uart_device.manufacturer}, "
            f"product: {dev.uart_device.product}, "
        )


asyncio.run(run())
