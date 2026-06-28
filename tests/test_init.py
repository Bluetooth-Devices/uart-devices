import threading

import pytest

from uart_devices import (
    BLUETOOTH_DEVICE_PATH,
    UART_DEVICE_PATH,
    BluetoothDevice,
    NotAUARTDeviceError,
    UARTDevice,
)


def test_bluetooth_device():
    assert BluetoothDevice(0)
    assert BluetoothDevice(1)


def test_bluetooth_device_paths():
    device = BluetoothDevice(2)
    assert device.hci == 2
    assert device.path == BLUETOOTH_DEVICE_PATH / "hci2"
    assert device.device_path == BLUETOOTH_DEVICE_PATH / "hci2" / "device"
    assert device.uart_device is None


def test_uart_device():
    assert UARTDevice("serial0-0")
    with pytest.raises(NotAUARTDeviceError):
        UARTDevice("x")


def test_uart_device_attributes():
    device = UARTDevice("serial0-0")
    assert device.id_str == "serial0-0"
    assert device.manufacturer is None
    assert device.product is None
    assert device.path == UART_DEVICE_PATH / "serial0-0"


def _write_uevent(uart_path, content):
    uart_path.mkdir(parents=True)
    (uart_path / "uevent").write_text(content)


def test_uart_device_setup_parses_uevent(monkeypatch, tmp_path):
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", tmp_path)
    _write_uevent(
        tmp_path / "serial0-0",
        "OF_COMPATIBLE_0=brcm,bcm43438-bt\n"
        "MODALIAS=of:NbluetoothT(null)Cbrcm,bcm43438-bt\n",
    )
    device = UARTDevice("serial0-0")
    device.path = tmp_path / "serial0-0"
    device.setup()
    assert device.manufacturer == "brcm"
    assert device.product == "bcm43438-bt"


def test_uart_device_setup_missing_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", tmp_path)
    _write_uevent(tmp_path / "serial0-0", "DRIVER=foo\nOTHER=bar\n")
    device = UARTDevice("serial0-0")
    device.path = tmp_path / "serial0-0"
    device.setup()
    assert device.manufacturer is None
    assert device.product is None


def test_uart_device_setup_modalias_without_comma(monkeypatch, tmp_path):
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", tmp_path)
    _write_uevent(tmp_path / "serial0-0", "MODALIAS=plainvalue\n")
    device = UARTDevice("serial0-0")
    device.path = tmp_path / "serial0-0"
    device.setup()
    assert device.product is None


@pytest.mark.asyncio
async def test_uart_device_async_setup(monkeypatch, tmp_path):
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", tmp_path)
    _write_uevent(
        tmp_path / "serial0-0",
        "OF_COMPATIBLE_0=brcm,bcm43438-bt\nMODALIAS=of:foo,bcm43438-bt\n",
    )
    device = UARTDevice("serial0-0")
    device.path = tmp_path / "serial0-0"
    await device.async_setup()
    assert device.manufacturer == "brcm"
    assert device.product == "bcm43438-bt"


def test_bluetooth_device_setup(monkeypatch, tmp_path):
    bt_root = tmp_path / "bluetooth"
    uart_root = tmp_path / "serial"
    bt_root.mkdir()
    uart_root.mkdir()

    uart_dev_dir = uart_root / "serial0-0"
    _write_uevent(
        uart_dev_dir,
        "OF_COMPATIBLE_0=brcm,bcm43438-bt\nMODALIAS=of:foo,bcm43438-bt\n",
    )

    hci_dir = bt_root / "hci0"
    hci_dir.mkdir()
    (hci_dir / "device").symlink_to(uart_dev_dir)

    monkeypatch.setattr("uart_devices.BLUETOOTH_DEVICE_PATH", bt_root)
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", uart_root)

    device = BluetoothDevice(0)
    device.path = hci_dir
    device.device_path = hci_dir / "device"
    device.setup()

    assert isinstance(device.uart_device, UARTDevice)
    assert device.uart_device.id_str == "serial0-0"
    assert device.uart_device.manufacturer == "brcm"
    assert device.uart_device.product == "bcm43438-bt"


@pytest.mark.asyncio
async def test_bluetooth_device_async_setup(monkeypatch, tmp_path):
    bt_root = tmp_path / "bluetooth"
    uart_root = tmp_path / "serial"
    bt_root.mkdir()
    uart_root.mkdir()

    uart_dev_dir = uart_root / "serial0-0"
    _write_uevent(
        uart_dev_dir,
        "OF_COMPATIBLE_0=brcm,bcm43438-bt\nMODALIAS=of:foo,bcm43438-bt\n",
    )

    hci_dir = bt_root / "hci0"
    hci_dir.mkdir()
    (hci_dir / "device").symlink_to(uart_dev_dir)

    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", uart_root)

    device = BluetoothDevice(0)
    device.path = hci_dir
    device.device_path = hci_dir / "device"
    await device.async_setup()

    assert device.uart_device is not None
    assert device.uart_device.manufacturer == "brcm"


@pytest.mark.asyncio
async def test_uart_device_async_setup_runs_off_event_loop_thread(
    monkeypatch, tmp_path
):
    """async_setup offloads the blocking read to a worker thread."""
    monkeypatch.setattr("uart_devices.UART_DEVICE_PATH", tmp_path)
    _write_uevent(tmp_path / "serial0-0", "OF_COMPATIBLE_0=brcm,bcm43438-bt\n")
    device = UARTDevice("serial0-0")
    device.path = tmp_path / "serial0-0"

    main_thread = threading.get_ident()
    setup_thread: dict[str, int] = {}
    original_setup = UARTDevice.setup

    def tracking_setup(self: UARTDevice) -> None:
        setup_thread["id"] = threading.get_ident()
        original_setup(self)

    monkeypatch.setattr(UARTDevice, "setup", tracking_setup)

    await device.async_setup()

    assert setup_thread["id"] != main_thread
    assert device.manufacturer == "brcm"
