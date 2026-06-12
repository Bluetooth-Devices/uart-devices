(usage)=

# Usage

Assuming that you've followed the {ref}`installations steps <installation>`, you're now ready to use this package.

Start by importing it:

```python
import uart_devices
```

## Overview

`uart_devices` resolves the UART device backing a Bluetooth HCI adapter on Linux
by reading sysfs (`/sys/class/bluetooth` and `/sys/bus/serial/devices`). It is
useful when you need the manufacturer and product of the serial transport behind
a `hciX` interface — for example, distinguishing an on-board UART Bluetooth
adapter from a USB dongle.

The package exposes three names:

- `BluetoothDevice` — wraps an HCI adapter (`hci0`, `hci1`, …) and resolves its
  backing UART device.
- `UARTDevice` — represents the UART device itself and its parsed metadata.
- `NotAUARTDeviceError` — raised when the resolved device is not a UART device.

## Resolving a Bluetooth adapter

Construct a `BluetoothDevice` with the HCI index and call `setup()` to populate
its `uart_device`:

```python
from uart_devices import BluetoothDevice

dev = BluetoothDevice(0)  # hci0
dev.setup()

uart = dev.uart_device
assert uart is not None
print(uart.manufacturer)  # e.g. "brcm"
print(uart.product)       # e.g. "bcm43438-bt"
```

`setup()` reads the `device` symlink under the adapter's sysfs path, so the
adapter must exist. If it does not, a `FileNotFoundError` is raised.

### Async usage

`setup()` performs blocking filesystem reads. In an asyncio application, use
`async_setup()`, which runs the work in the default executor:

```python
import asyncio
from uart_devices import BluetoothDevice


async def main() -> None:
    dev = BluetoothDevice(0)
    await dev.async_setup()
    if dev.uart_device is not None:
        print(dev.uart_device.manufacturer, dev.uart_device.product)


asyncio.run(main())
```

## Working with a UART device directly

If you already know the serial device id string (for example `serial0-0`), you
can construct a `UARTDevice` and read its metadata yourself:

```python
from uart_devices import UARTDevice

uart = UARTDevice("serial0-0")
uart.setup()
print(uart.manufacturer, uart.product)
```

The id string must contain a `-`; otherwise the constructor raises
`NotAUARTDeviceError`. `UARTDevice` also exposes `async_setup()` with the same
executor behavior as `BluetoothDevice`.

`manufacturer` and `product` are parsed from the device's `uevent` file
(`OF_COMPATIBLE_0` and `MODALIAS` respectively) and default to `None` when those
fields are absent.

## Enumerating adapters

A common pattern is to probe a range of HCI indices and skip adapters that are
not UART-backed or not present:

```python
import asyncio
from uart_devices import BluetoothDevice, NotAUARTDeviceError


async def run() -> None:
    for i in range(9):
        dev = BluetoothDevice(i)
        try:
            await dev.async_setup()
        except NotAUARTDeviceError:
            print(f"hci{i} is not a UART device")
            continue
        except FileNotFoundError:
            print(f"hci{i} not found")
            continue
        assert dev.uart_device is not None
        print(
            f"hci{i} manufacturer: {dev.uart_device.manufacturer}, "
            f"product: {dev.uart_device.product}"
        )


asyncio.run(run())
```

See [`examples/info.py`](https://github.com/bluetooth-devices/uart-devices/blob/main/examples/info.py)
for a runnable version of this pattern.
