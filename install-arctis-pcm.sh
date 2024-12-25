#     Copyright (C) 2022  birdybirdonline & awth13 - see LICENSE.md
#     @ https://github.com/birdybirdonline/Linux-Arctis-7-Plus-ChatMix
    
#     Contact via Github in the first instance
#     https://github.com/birdybirdonline
#     https://github.com/awth13

#!/bin/bash

source ./pyusb.sh

CONFIG_DIR="system-config/"
SYSTEMD_CONFIG="arctis-pcm.service"
UDEV_CONFIG="200-steelseries-arctis.rules"
SCRIPT="Arctis_ChatMix.py"
ARCTIS_DEVICES_FOLDER="arctis_devices"

SCRIPT_DIR="$HOME/.local/bin/"
SYSTEMD_DIR="$HOME/.config/systemd/user/"
UDEV_DIR="/etc/udev/rules.d/"

function cleanup {
    echo
    echo "Cleaning up:"
    sudo rm -vf "${UDEV_DIR}${UDEV_CONFIG}"
    rm -f "$UDEV_CONFIG"
    rm -vf "${SCRIPT_DIR}${SCRIPT}"
    rm -vrf "${SCRIPT_DIR}${ARCTIS_DEVICES_FOLDER}"
    rm -vf "${SYSTEMD_DIR}${SYSTEMD_CONFIG}"
    systemctl --user disable "$SYSTEMD_CONFIG"
}

if [[ -v UNINSTALL ]]; then
    echo "Uninstalling Arctis ChatMix."
    echo "You may need to provide your sudo password for removing udev rule."
    cleanup ; exit 0
fi

echo "Installing Arctis ChatMix."
echo "Installing script to ${SCRIPT_DIR}${SCRIPT}."
if [[ ! -d "$SCRIPT_DIR" ]]; then
    mkdir -vp $SCRIPT_DIR || \
        { echo "FATAL: Failed to create $SCRIPT_DIR" ; cleanup ; exit 1;}
fi
cp "${SCRIPT}" "${SCRIPT_DIR}"
cp -r "${ARCTIS_DEVICES_FOLDER}" "${SCRIPT_DIR}"

echo
echo "Installing udev rule to ${UDEV_DIR}${UDEV_CONFIG}."
echo "You may need to provide your sudo password for this step."
envsubst < "${CONFIG_DIR}${UDEV_CONFIG}" > "$UDEV_CONFIG"
sudo cp "$UDEV_CONFIG" "$UDEV_DIR" || \
    { echo "FATAL: Failed to copy $UDEV_CONFIG" ; cleanup ; exit 1;}
sudo udevadm control --reload
rm -f "$UDEV_CONFIG"

echo
echo "Installing systemd unit to ${SYSTEMD_DIR}${SYSTEMD_CONFIG}."
if [[ ! -d "$SYSTEMD_DIR" ]]; then
    mkdir -vp $SYSTEMD_DIR || \
        { echo "FATAL: Failed to create $SCRIPT_DIR" ; cleanup ; exit 1;}
fi
cp "${CONFIG_DIR}${SYSTEMD_CONFIG}" "$SYSTEMD_DIR"


echo
echo "Reloading systemd daemons (user)."
systemctl --user daemon-reload 2>/dev/null

echo
echo "Enabling systemd unit $SYSTEMD_CONFIG."
systemctl --user enable "$SYSTEMD_CONFIG" 2>/dev/null
