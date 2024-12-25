
from abc import ABC, abstractmethod

from arctis_devices.udev_device import UdevDevice


class DeviceManager(ABC):
    @abstractmethod
    def get_udev_device(self) -> UdevDevice:
        pass
