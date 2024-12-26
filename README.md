# Linux-Arctis-ChatMix

##***Important Licensing Notice**##

`Linux-Arctis-Chatmix` uses the GPL license. While the GPL license does permit commercial use,
it is **strongly discouraged** to reuse the work herein for any for-profit purpose as it relates to the usage
of a third party proprietary hardware device. 

The device itself has not been reverse-engineered for this purpose, nor has the proprietary GG Sonar Software typically
required to use it. 


## Overview
<br>
The SteelSeries Arctis series of headsets include a hardware modulation knob for 'chatmix' on the headset.
This allows the user to 'mix' the volume of two different devices on their system, named "Game" and "Chat".

On older Arctis models (e.g. Arctis 7), the headset would be detected as two individual hardware devices by
the host operating system and would assign them as such accordingly, allowing the user to specify which device to
use and where.

**Typical use case:** "Chat" for voicechat in games and VOIP/comms software, and "Game" for system / music etc.

On the Arctis 7+ model (and others), this two-device differentiation no longer exists, and the host OS will only recognize a single device.
If the user wishes to utilize the chatmix modulation knob, they *must* install the SteelSeries proprietary GG software. This
software does not currently support Linux.

This script provides a basic workaround for this problem for Linux users. It creates a Virtual Audio Cable (VAC) pair called "(DEVICE NAME) Chat"
and "(DEVICE NAME) Game" respectively, which the user can then assign accordingly as they would have done with an older Arctis model. 
The script listens to the headset's USB dongle signals and interprets them in a way that can be meaningfully converted
to adjust the audio when the user moves the dial on the headset.

### Two Versions ###

`install-arctis-pcm.sh` installs a daemon which ensures the chatmix dial controls the ChatMix balance on the headset.

Alternatively, use `install-AllSound_ChatMix.sh` installs a different version which will control the ChatMix balance
on *any* default system device, e.g. speakers etc.

For both versions at startup of the daemon the user must disconnect and reconnect the USB dongle from the machine. 

For the AllSound version, ensure the device you wish to output sound to is set as the default device before reconnecting the dongle.

For the Arctis version, the headset will be automatically set to the default device when the daemon starts.

<br>

## Requirements
<br>

The service itself depends on the [PyUSB](https://github.com/walac/pyusb) package. This package will be checked upon the install process, and in case the user will be prompted if he/she wants to install it at user-space. If you want to install it on a system level, it is suggested to install a distro's package, avoiding to run `pip` without the `--user` flag (it might compromise the operating system!).

In order for the VAC to be initialized and for the volumes to be controlled, the system requires **Pipewire** (and the underlying **PulseAudio**)
which are both fairly common on modern Linux systems out of the box.

<br>

## Installation
<br>

Python 3 & [PyUSB](https://github.com/pyusb/pyusb) required. 

Run `install-arctis-pcm.sh` as your desktop user in the project root directory. You may need to provide your `sudo` password during installation for copying the udev rule for your device.

**DISCONNECT DEVICE BEFORE INSTALLING**

To uninstall, set the `UNINSTALL` environment variable while calling the install script, e.g.,

```bash
UNINSTALL= ./install-arctis-pcm.sh
```

**RECONNECT DEVICE ONCE INSTALL IS COMPLETE**

There may be a short delay before the device becomes available after reconnecting. Use `systemctl --user status arctis-pcm.service` to check the service
is running properly.

<br>

## Implementation - How it works
<br>

The service first initializes the VAC by making direct calls to PulseWire `pw-cli` to create `nodes` and link them to the default audio device.

The service relies on the [PyUSB](https://github.com/walac/pyusb) package to read interrupt transfers from the headset's USB dongle.

For the Arctic 7+ device, the headset sends three bytes, the second and third of which are the volume values for the dial's two directions (toward 'Chat' down, toward 'Game' up).

The volumes are processed by the service and passed to the audio system via `pactl`.

The service will automatically set "(DEVICE NAME) Game" as the default device on startup.


## Supported devices

- **Arctis 7+** (original development by [birdybirdonline](https://github.com/birdybirdonline))
- **Arctis Nova Pro Wireless** (developed by [Giacomo Furlan](https://github.com/elegos)). The volume is managed by the GameDAC, while the mix is managed from a software point of view.

## How to add the support to a new device

The software is elastic enough to support other devices. In order you need to:

- Add a new set of rules in [system-config/200-steelseries-arctis.rules](system-config/200-steelseries-arctis.rules) -> if having troubles with udev selector (see: composite USB device), you might start from `udevadm info --attribute-walk --name=/dev/input/by-id/usb-SteelSeries_Arctis_[your specific device here]`.
- Add a new [DeviceManager](arctis_devices/device_manager.py) in [arctis_devices](arctis_devices).
- Register the new device manager in [arctis_devices/config.py](arctis_devices/config.py) under the `udev_devices` variable.

If your work does the job, consider forking the repository and open a pull request.

### Do I need to configure the `UdevDevice.device_initializer` for my new device?

It depents on your device, actually. For example the Arctis Nova Pro Wireless' GameDAC requires it, otherwise you won't be able to manage the channels mix. If you're confused on how that device's `init_device` calls was made, it's ok: these packets have been sniffed via WireShark on Windows, and they're pretty much arcane data yet. Via a try and error approach, they worked out on Linux too, enabling the game/chat mixer on the DAC.

### Help! I don't know how to configure the `UdevDevice`!

- `name`: the name of the device (see the current devices to get an idea)
- `vendor_id` / `product_id`: they're the couple ID values (ID xxxx:yyyy) found doing a simple `lsusb|grep -i arctis`
- `chatmix_hid_interface`: try and error. If you stop in debug exploring the device itself, it should be a Human Interface Device, which limits the options (in case of the Arctis Nova Pro Wireless there are two HID interfaces).
- `audio_position`: typically `['FL', 'FR']` (which is Front Left, Front Right)
- `read_volume_data`: how to read the input data, the response is a tuple of integer numbers representing a percentage for game channel, chat channel (for example `return 100, 100`). Suggestion: just print the data and see the pattern. Printing the data will show the numbers as integers.
- `device_initializer`: optional function to initialize the device once connected to the computer, for example to enable the GameDAC's mixer function. See previous section for details.


# Acknowledgements

With great thanks to:
- [awth13](https://github.com/awth13), especially for contributions in creation of our rules.d and systemd configuration and for wrestling with ALSA in our early attempts
- [Alexandra Zaharia's](https://github.com/alexandra-zaharia) excellent [article](https://alexandra-zaharia.github.io/posts/stopping-python-systemd-service-cleanly) for the clear advice on good practices for sigterm SIGINT/SIGTERM & logging
- [PyUSB's creators](https://github.com/pyusb) for [PyUSB](https://github.com/pyusb/pyusb) itself
- [Giacomo Furlan](https://github.com/elegos) for making the solution work on different headset models
- Honorable mention: [this reddit thread for clueing me in to reading the USB input!](https://www.reddit.com/r/steelseries/comments/s4uzos/arctis_7_on_linux_sonar_workaround/hu51jjy/)
