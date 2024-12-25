from dataclasses import dataclass, field
from logging import Logger
from typing import Callable

import usb.core


@dataclass
class UdevDevice:
    name: str
    vendor_id: int
    product_id: int
    chatmix_hid_interface: int  # USB HID for the ChatMix dial
    audio_position: list[str]
    read_volume_data: Callable[[list[int]], tuple[int, int]]  # out[0]: Game (%), out[1]: Chat (%)

    device_initializer: Callable[[usb.core.Device, Logger], None] = field(default=None)
