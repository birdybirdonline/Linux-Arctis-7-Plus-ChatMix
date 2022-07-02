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
        # identify the arctis 7+ device
        try:
            self.dev=usb.core.find(idVendor=0x1038, idProduct=0x220e)
        except Exception:
            print(traceback.format_exc())
            print("""Failed to identify the Arctis 7+ device. Please ensure it is connected.\n
            Please note: This program only supports the '7+' model.""")

        # select its interface and USB endpoint, and capture the endpoint address
        try:
            # interface index 7 of the Arctis 7+ is the USB HID for the ChatMix dial;
            # its actual interface number on the device itself is 5.
            self.interface = self.dev[0].interfaces()[7]
            self.interface_num = self.interface.bInterfaceNumber
            self.endpoint = self.interface.endpoints()[0]
            self.addr = self.endpoint.bEndpointAddress

        except Exception:
            print(traceback.format_exc())
            print("Failure to identify relevant USB device's interface or endpoint. Shutting down...")
            quit()

        # detach if the device is active
        if self.dev.is_kernel_driver_active(self.interface_num):
            self.dev.detach_kernel_driver(self.interface_num)

        try:
            self.VAC = self._init_VAC()
        except:
            print(traceback.format_exc())
            print("Failed to start VAC!")

    def _init_log(self):
        log = logging.getLogger(__name__)
        log.setLevel(logging.DEBUG)
        stdout_handler = log.StreamHandler()
        stdout_handler.setLevel(log.DEBUG)
        stdout_handler.setFormatter(log.Formatter('%(levelname)8s | %(message)s'))
        log.addHandler(stdout_handler)     

    def _init_VAC(self):
        '''Get name of default sink, establish virtual sink
        and pipe its output to the default sink'''

        # get the default sink id from pactl
        try:
            # use grep to identify the sink with arctis in the name, case insensitive
            try:
                pactl_grep = os.popen("pactl list short sinks | grep -i Arctis").readlines()
            except:
                print("Couldn't find an Arctis device. Terminating...")
                self.dieGracefully()
                
            # split the arctis line 
            tabs_pattern = re.compile(r'\t')
            tabs_re = re.split(tabs_pattern, pactl_grep[0])

            try:
                arctis_pattern = re.compile(r'arctis',flags=re.IGNORECASE)
                arctis_re = re.search(arctis_pattern, tabs_re[1])
                default_sink = arctis_re.string
                print(default_sink)
            except:
                print("Something wrong with Arctis definition in pactl list short sinks")
                self.dieGracefully()

        except Exception:
            print(traceback.format_exc())
            print(""""Failure detecting default sink - likely your soundcard isn't 
            recognized by ALSA or there is a permissions error""")

        # Destroy virtual sinks if they already existed incase of previous failure:
        try:
            os.system("pw-cli destroy Arctis_Game")
            os.system("pw-cli destroy Arctis_Chat")
        except:
            print("VACs do not already exist. Creating...")

        # Instantiate our virtual sinks - Arctis_Chat and Arctis_Game
        try:
            os.system("""pw-cli create-node adapter '{ 
                factory.name=support.null-audio-sink 
                node.name=Arctis_Game 
                node.description="Arctis 7+ Game" 
                media.class=Audio/Sink 
                monitor.channel-volumes=true 
                object.linger=true 
                audio.position=[FL FR]
                }' 
            """)

            os.system("""pw-cli create-node adapter '{ 
                factory.name=support.null-audio-sink 
                node.name=Arctis_Chat 
                node.description="Arctis 7+ Chat" 
                media.class=Audio/Sink 
                monitor.channel-volumes=true 
                object.linger=true 
                audio.position=[FL FR]
                }' 
            """)
        except:
            print("Failure to create node adapter - Arctis_Chat virtual device could not be created")
            self.dieGracefully()

        #route the virtual sink's L and R channels to the default system output
        try:
            print("Assigning VAC sink monitors output to default device...")
            os.system(f"""pw-link "Arctis_Game:monitor_FL" "{default_sink}:playback_FL" """)
            os.system(f"""pw-link "Arctis_Game:monitor_FR" "{default_sink}:playback_FR" """)
            os.system(f"""pw-link "Arctis_Chat:monitor_FL" "{default_sink}:playback_FL" """)
            os.system(f"""pw-link "Arctis_Chat:monitor_FR" "{default_sink}:playback_FR" """)
        except:
            print("Couldn't create the links to pipe LR from VAC to default device")
        
        # set the default sink to Arctis Game
        os.system('pactl set-default-sink Arctis_Game')

    def start_modulator_signal(self):
        '''Listen to the USB device for modulator knob's signal 
        and adjust volume accordingly'''
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
            except KeyboardInterrupt:
                self.dieGracefully()
    
    def __handle_sigterm(self, sig, frame):

        self.dieGracefully()

    def dieGracefully(self):
        '''Kill the process and remove the VACs
        on fatal exceptions or SIGTERM / SIGINT
        '''
        self.log.info('Cleanup')
        print(os.linesep)
        print("_"*45)
        print("Artcis 7+ ChatMix shutting down...")
        print("_"*45)
        os.system("pw-cli destroy Arctis_Game")
        os.system("pw-cli destroy Arctis_Chat")
        sys.exit(0)

# init
if __name__ == '__main__':
    a7p_service = Arctis7PlusChatMix()
    a7p_service.start_modulator_signal()
