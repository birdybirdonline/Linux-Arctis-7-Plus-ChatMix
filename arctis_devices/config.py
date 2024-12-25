from arctis_devices.arctis_7p import Arctis7Plus
from arctis_devices.arctis_nova_pro_wireless import ArctisNovaProWireless
from arctis_devices.udev_device import UdevDevice


udev_devices: list[UdevDevice] = [
    Arctis7Plus.get_udev_device(),
    ArctisNovaProWireless.get_udev_device(),
]
