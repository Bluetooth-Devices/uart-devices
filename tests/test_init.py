import pytest

from uart_devices import BluetoothDevice, NotAUARTDeviceError, UARTDevice


def test_bluetooth_device():
    assert BluetoothDevice(0)
    assert BluetoothDevice(1)


def test_uart_device():
    assert UARTDevice("serial0-0")
    with pytest.raises(NotAUARTDeviceError):
        UARTDevice("x")


def test_uart_device_setup_parses_uevent(tmp_path):
    device = UARTDevice("serial0-0")
    device.path = tmp_path
    (tmp_path / "uevent").write_text(
        "OF_COMPATIBLE_0=brcm,bcm43438-bt\n"
        "MODALIAS=of:NbluetoothT(null)Cbrcm,bcm43438-bt\n"
        "NO_EQUALS_LINE\n"  # skipped: no '=' separator
        "\n"  # skipped: blank line
    )
    device.setup()
    assert device.manufacturer == "brcm"
    assert device.product == "bcm43438-bt"
