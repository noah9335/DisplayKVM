# OLED "HELLO WORLD" ON POCKETBEAGLE (PBB) OPENWRT

# initial setup

Write image to SD card using Paragon Backup & Recovery 17 CE, Job-202212291002410_2022-12-29_10-03-17 [see /OpenWRT/Image]

Insert SD card into PBB, and provide internet conenction (e.g. USB to TCP/IP adapter, adjust /etc/config/network via console as relevant and /etc/init.d/network restart) [example attached]

SSH port is default 22, USR is root, PWD... im not putting that on a public repo.

# Expanding filesystem and partition

"using parted" guide from https://openwrt.org/docs/guide-user/installation/openwrt_x86


	opkg update

    opkg install wget
    
    opkg install lsblk
        lsblk
    verify type and disk name #likely trivial with this imlementation but should increase compatability, also prevents accidently removing the boot section or something.


	opkg install parted
	parted /dev/mmcblk0 (refer to above disk name, and dont touch the boot partition...)
		p
		resizepart 2 100%
		q
	reboot
	opkg update
	opkg install losetup resize2fs
	losetup /dev/loop0 /dev/mmcblk0p2 2> /dev/null
	resize2fs -f /dev/loop0
	reboot

# setup python & oled support 

guide https://learn.adafruit.com/monochrome-oled-breakouts/python-setup

	opkg update
	opkg install python3-pip python3-pillow python3-numpy python3-dev gcc		#python3-pillow used instead of python3-pil
	pip3 install adafruit-circuitpython-ssd1306
	
	opkg install git-http			#normal git does not work
	git clone https://github.com/adafruit/adafruit-beaglebone-io-python.git		#reference https://pypi.org/project/Adafruit-BBIO/
	cd adafruit-beaglebone-io-python/
	python3 setup.py install


cd /root

# method 1

wget https://raw.githubusercontent.com/noah9335/DisplayKVM/main/OpenWRT/modifed_hello_world.py

if successful, skip to final compatability mods

# method 2

nano hello_world.py		#copy example from https://learn.adafruit.com/monochrome-oled-breakouts/python-setup 

# example file modifications (modified file is in repo, titiled modified_hello_world.py)

Line 19 change to
	oled_reset = None

Line 28 change to
	i2c = busio.I2C("I2C2_SCL", "I2C2_SDA")			#Note! "I2C2_SCL", "I2C2_SDA" for bus 2; and "I2C1_SCL", "I2C1_SDA" for bus 1

Insert new line after line 14
	import busio

# final compatability mods			

nano /usr/lib/python3.10/site-packages/adafruit_platformdetect/board.py

Change line 43

	self._board_id = "BEAGLEBONE_POCKETBEAGLE"

 python3 hello_world.py

 # potentially unessacary
nano /usr/lib/python3.10/site-packages/board.py		
														
Insert new line after line 26						
														
board_id = "BEAGLEBONE_POCKETBEAGLE"