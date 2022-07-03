import os
import sys
import signal
import time
import logging

import traceback
import re
import usb.core


class Arctis7PlusChatMix:
    def __init__(self):

        signal.signal(signal.SIGTERM, self.__handle_sigterm)
        self.log = self._init_log()
        self.log.info("Initializing ac7pcm...")

        # identify the arctis 7+ device
        try:
            self.dev=usb.core.find(idVendor=0x1038, idProduct=0x220e)
        except Exception as e:
            self.log.error("""Failed to identify the Arctis 7+ device.
            Please ensure it is connected.\n
            Please note: This program only supports the '7+' model.""")

        # select its interface and USB endpoint, and capture the endpoint address
        try:
            # interface index 7 of the Arctis 7+ is the USB HID for the ChatMix dial;
            # its actual interface number on the device itself is 5.
            self.interface = self.dev[0].interfaces()[7]
            self.interface_num = self.interface.bInterfaceNumber
            self.endpoint = self.interface.endpoints()[0]
            self.addr = self.endpoint.bEndpointAddress

        except Exception as e:
            self.log.error("""Failure to identify relevant 
            USB device's interface or endpoint. Shutting down...""")
            self.die_gracefully()

        # detach if the device is active
        if self.dev.is_kernel_driver_active(self.interface_num):
            self.dev.detach_kernel_driver(self.interface_num)

        try:
            self.VAC = self._init_VAC()
        except Exception as e:
            self.log.error("Failed to start VAC!", exc_info=True)

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

        # attempt to identify an Arctis sink via pactl
        try:
            self.log.info("identifying Arctis device sink")
            pactl_short_sinks = os.popen("pactl list short sinks").readlines()
            self.log.info(pactl_short_sinks)
            # grab any elements from list of pactl sinks that are Arctis 7
            arctis = re.compile('.*[aA]rctis.*7')
            arctis_sink = list(filter(arctis.match, pactl_short_sinks))[0] 

            # split the arctis line on tabs (which form table given by 'pactl short sinks')
            tabs_pattern = re.compile(r'\t')
            tabs_re = re.split(tabs_pattern, arctis_sink)

            # skip first element of tabs_re (sink's ID which is not persistent)
            arctis_device = tabs_re[1]
            self.log.info(f"Arctis sink identified as {arctis_device}")
            default_sink = arctis_device

        except Exception as e:
            self.log.error("""Something wrong with Arctis definition 
            in pactl list short sinks regex matching.
            Likely no match found for device, check traceback.
            """, exc_info=True)
            self.die_gracefully()


        # Destroy virtual sinks if they already existed incase of previous failure:
        try:
            destroy_a7p_game = os.system("pw-cli destroy Arctis_Game 2>/dev/null")
            destroy_a7p_chat = os.system("pw-cli destroy Arctis_Chat 2>/dev/null")
            if destroy_a7p_game == 0 or destroy_a7p_chat == 0:
                raise Exception
        except Exception as e:
            self.log.info("""Attempted to destroy old VAC sinks at init but none existed""")

        # Instantiate our virtual sinks - Arctis_Chat and Arctis_Game
        try:
            self.log.info("Creating VACS...")
            os.system("""pw-cli create-node adapter '{ 
                factory.name=support.null-audio-sink 
                node.name=Arctis_Game 
                node.description="Arctis 7+ Game" 
                media.class=Audio/Sink 
                monitor.channel-volumes=true 
                object.linger=true 
                audio.position=[FL FR]
                }' 1>/dev/null
            """)

            os.system("""pw-cli create-node adapter '{ 
                factory.name=support.null-audio-sink 
                node.name=Arctis_Chat 
                node.description="Arctis 7+ Chat" 
                media.class=Audio/Sink 
                monitor.channel-volumes=true 
                object.linger=true 
                audio.position=[FL FR]
                }' 1>/dev/null
            """)
        except Exception as E:
            self.log.error("""Failure to create node adapter - 
            Arctis_Chat virtual device could not be created""", exc_info=True)
            self.die_gracefully(sink_creation_fail=True)

        #route the virtual sink's L&R channels to the default system output's LR
        try:
            self.log.info("Assigning VAC sink monitors output to default device...")

            os.system(f'pw-link "Arctis_Game:monitor_FL" '
            f'"{default_sink}:playback_FL" 1>/dev/null')

            os.system(f'pw-link "Arctis_Game:monitor_FR" '
            f'"{default_sink}:playback_FR" 1>/dev/null')

            os.system(f'pw-link "Arctis_Chat:monitor_FL" '
            f'"{default_sink}:playback_FL" 1>/dev/null')

            os.system(f'pw-link "Arctis_Chat:monitor_FR" '
            f'"{default_sink}:playback_FR" 1>/dev/null')

        except Exception as e:
            self.log.error("""Couldn't create the links to 
            pipe LR from VAC to default device""", exc_info=True)
            self.die_gracefully(sink_fail=True)
        
        # set the default sink to Arctis Game
        os.system('pactl set-default-sink Arctis_Game')

    def start_modulator_signal(self):
        """Listen to the USB device for modulator knob's signal 
        and adjust volume accordingly
        """
        
        self.log.info("Reading modulator USB input started")
        print("_"*45)
        print("Arctis 7+ ChatMix Enabled. Ctrl+C to Quit")
        print("_"*45)
        while True:
            try:
                # read the input of the USB signal. Signal is sent in 64-bit interrupt packets.
                # read_input[1] returns value to use for default device volume
                # read_input[2] returns the value to use for virtual device volume
                read_input = self.dev.read(self.addr, 64)
                default_device_volume = "{}%".format(read_input[1])
                virtual_device_volume = "{}%".format(read_input[2])
        
                # os.system calls to issue the commands directly to pactl
                os.system(f'pactl set-sink-volume Arctis_Game {default_device_volume}')
                os.system(f'pactl set-sink-volume Arctis_Chat {virtual_device_volume}')
            except usb.core.USBTimeoutError:
                pass
            except usb.core.USBError:
                self.log.error("USB input/output error - likely disconnect")
                self.die_gracefully()
            except KeyboardInterrupt:
                self.log.info("Keyboard Interrupt signal, terminating...")
                return self.die_gracefully()

    
    def __handle_sigterm(self, sig, frame):
        self.die_gracefully()

    def die_gracefully(self, sink_creation_fail=False):
        """Kill the process and remove the VACs
        on fatal exceptions or SIGTERM / SIGINT
        """
        
        self.log.info('Cleanup on shutdown')
        print(os.linesep)
        print("_"*45)
        print("Artcis 7+ ChatMix shutting down...")
        print("_"*45)
        os.system(f"pactl set-default-sink {self.system_default_sink}")

        # cleanup virtual sinks if they exist
        if sink_creation_fail == False:
            os.system("pw-cli destroy Arctis_Game 1>/dev/null")
            os.system("pw-cli destroy Arctis_Chat 1>/dev/null")
        if not self.dev.is_kernel_driver_active(self.interface_num):
            self.dev.finalize()
        sys.exit(0)

# init
if __name__ == '__main__':
    a7pcm_service = Arctis7PlusChatMix()
    a7pcm_service.start_modulator_signal()
