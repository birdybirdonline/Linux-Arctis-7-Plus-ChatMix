#!/bin/bash

pip install pyusb
cp Arctis_7_Plus_ChatMix.py $HOME/.local/bin
cd system-config
cp 91-steelseries-artcis-7.rules /lib/udev/rules.d
cp arctis.service $HOME/.config/systemd/user

systemctl --user enable arctis.service &