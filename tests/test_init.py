import pytest

from uart_devices import BluetoothDevice, NotAUARTDeviceError, UARTDevice


def test_bluetooth_device():
    assert BluetoothDevice(0)
    assert BluetoothDevice(1)


def test_uart_device():
    assert UARTDevice("serial0-0")
    with pytest.raises(NotAUARTDeviceError):
        UARTDevice("x")
