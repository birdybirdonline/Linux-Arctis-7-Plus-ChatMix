from logging import Logger
import math

import usb.core


class Arctis7Plus:

    @staticmethod
    def manage_chatmix_input_data(data: list[int]) -> tuple[int, int]:
        return data[1], data[2]
