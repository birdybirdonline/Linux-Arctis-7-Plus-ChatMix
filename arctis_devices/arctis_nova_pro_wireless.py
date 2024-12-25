from logging import Logger
import math

import usb.core


class ArctisNovaProWireless:
    volume: float

    game_mix: int
    chat_mix: int

    def __init__(self):
        self.volume = 100  # Volume is always 100, it is managed by the GameDAC directly
        self.game_mix = 100  # Default to equally mixed (should be set during interface configuration)
        self.chat_mix = 100  # Default to equally mixed (should be set during interface configuration)

    @staticmethod
    def packet_0_filler(packet: list[int], size: int):
        return [*packet, *[0 for _ in range(size - len(packet))]]

    def init_device(self, device: usb.core.Device, logger: Logger):
        '''
        Initializes the GameDAC Gen2, enabling the mixer.
        Kinda obscure, but seems to work on my machine (tm).
        (Packets and sequence taken from the Arctis Nova Pro Wireless via Wireshark)
        '''
        commands = [
            # Command, expects response

            # Series of queries / responses
            ([0x06, 0xb0], True),
            ([0x06, 0xb0], True),
            ([0x06, 0x20], True),
            ([0x06, 0x20], True),
            ([0x06, 0x10], True),
            ([0x06, 0x10], True),
            ([0x06, 0xb0], True),
            ([0x06, 0xb0], True),
            ([0x06, 0x10], True),
            ([0x06, 0x3b], False),  # Correction?
            ([0x06, 0xb0], True),
            ([0x06, 0x8d, 0x01], True),
            ([0x06, 0x20], True),
            ([0x06, 0x20], True),
            ([0x06, 0x20], True),
            ([0x06, 0x80], True),
            ([0x06, 0x3b], False),  # Correction?
            ([0x06, 0xb0], True),
            # Burst of commands (device init?)
            ([0x06, 0x8d, 0x01], False),
            ([0x06, 0x33, 0x14, 0x14, 0x14], False),
            ([0x06, 0xc3], False),
            ([0x06, 0x2e], False),
            ([0x06, 0xc1, 0x05], False),
            ([0x06, 0x85, 0x0a], False),
            ([0x06, 0x37, 0x0a], False),
            ([0x06, 0xb2], False),
            ([0x06, 0x47, 0x64, 0x00, 0x64], False),
            ([0x06, 0x83, 0x01], False),
            ([0x06, 0x89, 0x00], False),
            ([0x06, 0x27, 0x02], False),
            ([0x06, 0xb3], False),
            ([0x06, 0x39], False),
            ([0x06, 0xbf, 0x0a], False),
            ([0x06, 0x43, 0x01], False),
            ([0x06, 0x69, 0x00], False),
            ([0x06, 0x3b, 0x00], False),
            ([0x06, 0x8d, 0x01], False),
            ([0x06, 0x49, 0x01], False),
            ([0x06, 0xb7, 0x00], False),
            # Another series of queries (perhaps for confirmation?)
            ([0x06, 0xb7, 0x00], True),
            ([0x06, 0xb0, 0x00], True),
            ([0x06, 0xb7, 0x00], True),
            ([0x06, 0xb0, 0x00], True),
            ([0x06, 0x20, 0x00], True),
            ([0x06, 0xb7, 0x00], True),
            ([0x06, 0xb0, 0x00], True),
        ]

        # 8th interface, 2nd endpoint. The 1st one is for receiving data from the DAC
        commands_endpoint_address = device[0].interfaces()[7].endpoints()[1].bEndpointAddress

        for command in commands:
            device.write(commands_endpoint_address, ArctisNovaProWireless.packet_0_filler(command[0], 91))
            # Ignore the responses for now, as I haven't figured out yet their significance.

    @staticmethod
    def _normalize_chatmix_volume(volume: int) -> int:
        '''
        Normalize the raw volume to a value between 0 and 1
        '''
        volume = volume / 56  # number between 0 and 1
        volume = 1 - volume  # invert

        # Apply a logarithmic trend (like how it seems to be working on Windows via GG software)
        volume = max(volume, 1e-6)  # avoid log(0)
        volume = math.log10(volume * 9 + 1)

        return volume

    def manage_chatmix_input_data(self, data: list[int]) -> tuple[int, int]:
        # Volume control is
        if data[0] == 0x07 and data[1] == 0x25:
            self.volume = ArctisNovaProWireless._normalize_chatmix_volume(data[2])

        elif data[0] == 0x07 and data[1] == 0x45:
            self.game_mix = data[2]  # Ranges from 0 to 100
            self.chat_mix = data[3]  # Ranges from 0 to 100

        volume = (self.volume if self.volume is not None else 1)

        return int(round(volume * (self.game_mix if self.game_mix is not None else 100), 0)), \
            int(round(volume * (self.chat_mix if self.chat_mix is not None else 100), 0))
