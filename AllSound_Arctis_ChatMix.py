"""   Copyright (C) 2022  birdybirdonline & awth13 - see LICENSE.md
    @ https://github.com/birdybirdonline/Linux-Arctis-7-Plus-ChatMix
    
    Contact via Github in the first instance
    https://github.com/birdybirdonline
    https://github.com/awth13
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
    """

import os
import sys
import signal
import logging

import usb.core

from arctis_devices.config import udev_devices

# Ver info
""" AllSound version, which allows the chatmix dial on the headset
    to control the system default device, no matter which one
    """


class ArctisAllSoundChatMix:
    def __init__(self):

        # set to receive signal from systemd for termination
        signal.signal(signal.SIGTERM, self.__handle_sigterm)

        self.log = self._init_log()
        self.log.info("Initializing ac-pcm...")

        # identify the arctis device
        for device in udev_devices:
            try:
                self.dev = usb.core.find(idVendor=device.vendor_id, idProduct=device.product_id)
                if self.dev is None:
                    continue
                self.udev_device = device

                self.log.info(f'Found device {device.name}')

                break
            except Exception as e:
                pass

        if self.dev is None:
            self.log.error(f"""Failed to identify the Arctis device.
            Please ensure it is connected.\n
            Please note: This program supports the following models: {', '.join(udev_devices.keys())}.""")
            self.die_gracefully(trigger="Couldn't find any Arctis model")

        # select its interface and USB endpoint, and capture the endpoint address
        try:
            # interface index of the USB HID for the ChatMix dial might differ from the interface number on the device itself
            self.interface: usb.core.Interface = self.dev[0].interfaces()[self.udev_device.chatmix_hid_interface]
            self.interface_num = self.interface.bInterfaceNumber
            self.endpoint = self.interface.endpoints()[0]
            self.addr = self.endpoint.bEndpointAddress

        except Exception as e:
            self.log.error("""Failure to identify relevant 
            USB device's interface or endpoint. Shutting down...""")
            self.die_gracefully(exc=True, trigger="identification of USB endpoint")

        # detach if the device is active
        if self.dev.is_kernel_driver_active(self.interface_num):
            self.dev.detach_kernel_driver(self.interface_num)

        self.VAC = self._init_VAC()

    def _init_log(self):
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(logging.Formatter('%(levelname)8s | %(message)s'))
        log.addHandler(stdout_handler)
        return (log)

    def _init_VAC(self):
        """Get name of default sink, establish virtual sink
        and pipe its output to the default sink
        """

        # get the default sink id from pactl
        self.system_default_sink = os.popen("pactl get-default-sink").read().strip()
        self.log.info(f"default sink identified as {self.system_default_sink}")

        # Destroy virtual sinks if they already existed incase of previous failure:
        try:
            destroy_a7p_game = os.system("pw-cli destroy ChatMix_Game 2>/dev/null")
            destroy_a7p_chat = os.system("pw-cli destroy ChatMix_Chat 2>/dev/null")
            if destroy_a7p_game == 0 or destroy_a7p_chat == 0:
                raise Exception
        except Exception as e:
            self.log.info("""Attempted to destroy old VAC sinks at init but none existed""")

        # Instantiate our virtual sinks - Arctis_Chat and Arctis_Game
        try:
            self.log.info("Creating VACS...")
            os.system(f"""pw-cli create-node adapter '{{
                factory.name=support.null-audio-sink
                node.name=ChatMix_Game
                node.description="ChatMix Game"
                media.class=Audio/Sink
                monitor.channel-volumes=true
                object.linger=true
                audio.position=[{' '.join(self.udev_device.audio_position)}]
                }}' 1>/dev/null
            """)

            os.system(f"""pw-cli create-node adapter '{{
                factory.name=support.null-audio-sink
                node.name=ChatMix_Chat
                node.description="ChatMix Chat"
                media.class=Audio/Sink
                monitor.channel-volumes=true
                object.linger=true
                audio.position=[{' '.join(self.udev_device.audio_position)}]
                }}' 1>/dev/null
            """)
        except Exception as E:
            self.log.error("""Failure to create node adapter - 
            ChatMix virtual device could not be created""", exc_info=True)
            self.die_gracefully(sink_creation_fail=True, trigger="VAC node adapter")

        # route the virtual sink's L&R channels to the default system output's LR
        try:
            self.log.info("Assigning VAC sink monitors output to default device...")

            os.system(f'pw-link "ChatMix_Game:monitor_FL" '
                      f'"{self.system_default_sink}:playback_FL" 1>/dev/null')

            os.system(f'pw-link "ChatMix_Game:monitor_FR" '
                      f'"{self.system_default_sink}:playback_FR" 1>/dev/null')

            os.system(f'pw-link "ChatMix_Chat:monitor_FL" '
                      f'"{self.system_default_sink}:playback_FL" 1>/dev/null')

            os.system(f'pw-link "ChatMix_Chat:monitor_FR" '
                      f'"{self.system_default_sink}:playback_FR" 1>/dev/null')

        except Exception as e:
            self.log.error("""Couldn't create the links to 
            pipe LR from VAC to default device""", exc_info=True)
            self.die_gracefully(sink_fail=True, trigger="LR links")

    def start_modulator_signal(self):
        """Listen to the USB device for modulator knob's signal 
        and adjust volume accordingly
        """

        if self.udev_device.device_initializer is not None:
            self.log.info('Initializing device...')
            self.udev_device.device_initializer(self.dev, self.log)

        self.log.info("Reading modulator USB input started")
        self.log.info("-"*45)
        self.log.info("ChatMix Enabled!")
        self.log.info("-"*45)
        while True:
            try:
                # read the input of the USB signal. Signal is sent in 64-bit interrupt packets.
                # read_input[1] returns value to use for default device volume
                # read_input[2] returns the value to use for virtual device volume
                read_input = self.dev.read(self.addr, 64)
                volume_data = self.udev_device.read_volume_data(read_input)

                default_device_volume = "{}%".format(volume_data[0])
                virtual_device_volume = "{}%".format(volume_data[1])

                # os.system calls to issue the commands directly to pactl
                os.system(f'pactl set-sink-volume ChatMix_Game {default_device_volume}')
                os.system(f'pactl set-sink-volume ChatMix_Chat {virtual_device_volume}')
            except usb.core.USBTimeoutError:
                pass
            except usb.core.USBError:
                self.log.fatal("USB input/output error - likely disconnect")
                break

    def __handle_sigterm(self, sig, frame):
        self.die_gracefully()

    def die_gracefully(self, sink_creation_fail=False, trigger=None):
        """Kill the process and remove the VACs
        on fatal exceptions or SIGTERM / SIGINT
        """

        self.log.info('Cleanup on shutdown')
        # os.system(f"pactl set-default-sink {self.system_default_sink}")

        # cleanup virtual sinks if they exist
        if sink_creation_fail == False:
            self.log.info("Destroying virtual sinks...")
            os.system("pw-cli destroy ChatMix_Game 1>/dev/null")
            os.system("pw-cli destroy ChatMix_Chat 1>/dev/null")

        if trigger is not None:
            self.log.info("-"*45)
            self.log.fatal("Failure reason: " + trigger)
            self.log.info("-"*45)
            sys.exit(1)
        else:
            self.log.info("-"*45)
            self.log.info("AllSound ChatMix shut down gracefully... Bye Bye!")
            self.log.info("-"*45)
            sys.exit(0)


# init
if __name__ == '__main__':
    arctis_pcm_service = ArctisAllSoundChatMix()
    arctis_pcm_service.start_modulator_signal()
