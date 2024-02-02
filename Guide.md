# Simple guide to intallation

# tools and begining
sudo -i
apt-get update
apt-get full-upgrade
apt-get install nano - installs nano
apt-get install git

# dependancies
apt-get install i2c-tools
apt-get install python3-pip -installs python3 and pip
pip3 install --upgrade setuptools wheel - updates pip and installs setup tools
pip install Adafruit-SSD1306 - installs modules for the display

# i2c verification
i2cdetect -l  - lists i2c buses
i2cdetect -F (bus # e.g. 2) - displays functionality of that bus
i2cdetect -r (bus # e.g. 2) - displays the hardware address e.g. 0x03

# installing example and programs
git clone https://github.com/noah9335/DisplayKVM.git
cd DisplayKVM
cd noah_program
python3 setup.py install
python3 refined_shape.py
