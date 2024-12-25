python_exec=$(which python3 2>/dev/null || which python 2>/dev/null)

if [[ "$USER" == root ]]; then
    echo "Please run the install script as non-root user."
    exit 1
fi

# Check for pyusb installation
"${python_exec}" -c 'import usb.core' 2>/dev/null
if [ $? == 1 ]; then
    echo "Install (locally or system-wide) the pyusb Python module first."
    read -p "Do you want to install it locally? [y/N] " response

    if [[ "${response}" == [yY] ]]; then
        "${python_exec}" -m pip install --user pyusb
    else
        echo "To install locally, run: ${python_exec} -m pip install --user pyusb"
        exit 2
    fi
fi
