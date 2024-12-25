from logging import Logger
import math

import usb.core

from arctis_devices.device_manager import DeviceManager
from arctis_devices.udev_device import UdevDevice


class Arctis7Plus(DeviceManager):

    @staticmethod
    def get_udev_device() -> UdevDevice:
        return UdevDevice('Arctis 7+', 0x1038, 0x220e, 7, ['FL', 'FR'], Arctis7Plus.manage_chatmix_input_data)

    @staticmethod
    def manage_chatmix_input_data(data: list[int]) -> tuple[int, int]:
        return data[1], data[2]
