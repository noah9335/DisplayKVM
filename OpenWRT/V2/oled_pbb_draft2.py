
import board
import digitalio
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# noah modifications
import sys
import socket
import signal
import itertools
import logging
import datetime
import time
import netifaces

# Define the Reset Pin
oled_reset = None

# Change these
# to the right size for your display!
WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 5

# Use for I2C.
i2c = busio.I2C("I2C2_SCL", "I2C2_SDA")
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)

# Clear display.
oled.fill(0)
oled.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new("1", (oled.width, oled.height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a white background
##draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

# Draw a smaller inner rectangle
##draw.rectangle(
##    (BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
##    outline=0,
##    fill=0,
##)

# Load default font.
#font = ImageFont.load_default()
font = ImageFont.truetype("m3x6.ttf", 16)

## noah modifications to print IP

def _get_ip() -> tuple[str, str]:
    try:
        gws = netifaces.gateways()
        if "default" in gws:
            for proto in [socket.AF_INET, socket.AF_INET6]:
                if proto in gws["default"]:
                    iface = gws["default"][proto][1]
                    addrs = netifaces.ifaddresses(iface)
                    return (iface, addrs[proto][0]["addr"])

        for iface in netifaces.interfaces():
            if not iface.startswith(("lo", "docker")):
                addrs = netifaces.ifaddresses(iface)
                for proto in [socket.AF_INET, socket.AF_INET6]:
                    if proto in addrs:
                        return (iface, addrs[proto][0]["addr"])
    except Exception:
        # _logger.exception("Can't get iface/IP")
        pass
    return ("<no-iface>", "<no-ip>")

iface, ip = _get_ip()
print(f"Interface: {iface}, IP Address: {ip}")

##SW INSERT UPS CODE START

import smbus
#import RPi.GPIO    
import time
import logging

# Config Register (R/W)
_REG_CONFIG                 = 0x00

# SHUNT VOLTAGE REGISTER (R)
_REG_SHUNTVOLTAGE           = 0x01

# BUS VOLTAGE REGISTER (R)
_REG_BUSVOLTAGE             = 0x02

# POWER REGISTER (R)
_REG_POWER                  = 0x03

# CURRENT REGISTER (R)
_REG_CURRENT                = 0x04

# CALIBRATION REGISTER (R/W)
_REG_CALIBRATION            = 0x05

INA219_CONFIG_BADCRES_9BIT =  0x0000 # 9-bit bus res = 0..511
INA219_CONFIG_BADCRES_10BIT = 0x0080 # 10-bit bus res = 0..1023
INA219_CONFIG_BADCRES_11BIT = 0x0100 # 11-bit bus res = 0..2047
INA219_CONFIG_BADCRES_12BIT = 0x0180 # 12-bit bus res = 0..4097

class BusVoltageRange:
    """Constants for ``bus_voltage_range``"""
    RANGE_16V               = 0x00      # set bus voltage range to 16V
    RANGE_32V               = 0x01      # set bus voltage range to 32V (default)

class Gain:
    """Constants for ``gain``"""
    DIV_1_40MV              = 0x00      # shunt prog. gain set to  1, 40 mV range
    DIV_2_80MV              = 0x01      # shunt prog. gain set to /2, 80 mV range
    DIV_4_160MV             = 0x02      # shunt prog. gain set to /4, 160 mV range
    DIV_8_320MV             = 0x03      # shunt prog. gain set to /8, 320 mV range

class ADCResolution:
    """Constants for ``bus_adc_resolution`` or ``shunt_adc_resolution``"""
    ADCRES_9BIT_1S          = 0x00      #  9bit,   1 sample,     84us
    ADCRES_10BIT_1S         = 0x01      # 10bit,   1 sample,    148us
    ADCRES_11BIT_1S         = 0x02      # 11 bit,  1 sample,    276us
    ADCRES_12BIT_1S         = 0x03      # 12 bit,  1 sample,    532us
    ADCRES_12BIT_2S         = 0x09      # 12 bit,  2 samples,  1.06ms
    ADCRES_12BIT_4S         = 0x0A      # 12 bit,  4 samples,  2.13ms
    ADCRES_12BIT_8S         = 0x0B      # 12bit,   8 samples,  4.26ms
    ADCRES_12BIT_16S        = 0x0C      # 12bit,  16 samples,  8.51ms
    ADCRES_12BIT_32S        = 0x0D      # 12bit,  32 samples, 17.02ms
    ADCRES_12BIT_64S        = 0x0E      # 12bit,  64 samples, 34.05ms
    ADCRES_12BIT_128S       = 0x0F      # 12bit, 128 samples, 68.10ms

class Mode:
    """Constants for ``mode``"""
    POWERDOW                = 0x00      # power down
    SVOLT_TRIGGERED         = 0x01      # shunt voltage triggered
    BVOLT_TRIGGERED         = 0x02      # bus voltage triggered
    SANDBVOLT_TRIGGERED     = 0x03      # shunt and bus voltage triggered
    ADCOFF                  = 0x04      # ADC off
    SVOLT_CONTINUOUS        = 0x05      # shunt voltage continuous
    BVOLT_CONTINUOUS        = 0x06      # bus voltage continuous
    SANDBVOLT_CONTINUOUS    = 0x07      # shunt and bus voltage continuous


class INA219:
    def __init__(self, i2c_bus=2, addr=0x43):
        self.bus = smbus.SMBus(i2c_bus)
        self.addr = addr
#        self.GPIO = RPi.GPIO
        
        # Set chip to known config values to start
        self._cal_value = 0
        self._currentDivider_mA = 0 
        self._powerMultiplier_mW = 0
        self.set_calibration_32V_2A()

    def read(self,address):
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return ((data[0] * 256 ) + data[1])

    def write(self,address,data):
        temp = [0,0]
        temp[1] = data & 0xFF
        temp[0] =(data & 0xFF00) >> 8
        self.bus.write_i2c_block_data(self.addr,address,temp)

    def set_calibration_32V_2A(self):
        """	Configures to INA219 to be able to measure up to 32V and 2A
            of current.  Each unit of current corresponds to 100uA, and
            each unit of power corresponds to 2mW. Counter overflow
            occurs at 3.2A.
            These calculations assume a 0.1 ohm resistor is present
        """
        # By default we use a pretty huge range for the input voltage,
        # which probably isn't the most appropriate choice for system
        # that don't use a lot of power.  But all of the calculations
        # are shown below if you want to change the settings.  You will
        # also need to change any relevant register settings, such as
        # setting the VBUS_MAX to 16V instead of 32V, etc.

        # VBUS_MAX = 32V             (Assumes 32V, can also be set to 16V)
        # VSHUNT_MAX = 0.32          (Assumes Gain 8, 320mV, can also be 0.16, 0.08, 0.04)
        # RSHUNT = 0.1               (Resistor value in ohms)

        # 1. Determine max possible current
        # MaxPossible_I = VSHUNT_MAX / RSHUNT
        # MaxPossible_I = 3.2A

        # 2. Determine max expected current
        # MaxExpected_I = 2.0A

        # 3. Calculate possible range of LSBs (Min = 15-bit, Max = 12-bit)
        # MinimumLSB = MaxExpected_I/32767
        # MinimumLSB = 0.000061              (61uA per bit)
        # MaximumLSB = MaxExpected_I/4096
        # MaximumLSB = 0,000488              (488uA per bit)

        # 4. Choose an LSB between the min and max values
        #    (Preferrably a roundish number close to MinLSB)
        # CurrentLSB = 0.0001 (100uA per bit)

        # 5. Compute the calibration register
        # Cal = trunc (0.04096 / (Current_LSB * RSHUNT))
        # Cal = 4096 (0x1000)


        self._cal_value = 4096

        # 6. Calculate the power LSB
        # PowerLSB = 20 * CurrentLSB
        # PowerLSB = 0.002 (2mW per bit)

        # 7. Compute the maximum current and shunt voltage values before overflow
        #
        # Max_Current = Current_LSB * 32767
        # Max_Current = 3.2767A before overflow
        #
        # If Max_Current > Max_Possible_I then
        #    Max_Current_Before_Overflow = MaxPossible_I
        # Else
        #    Max_Current_Before_Overflow = Max_Current
        # End If
        #
        # Max_ShuntVoltage = Max_Current_Before_Overflow * RSHUNT
        # Max_ShuntVoltage = 0.32V
        #
        # If Max_ShuntVoltage >= VSHUNT_MAX
        #    Max_ShuntVoltage_Before_Overflow = VSHUNT_MAX
        # Else
        #    Max_ShuntVoltage_Before_Overflow = Max_ShuntVoltage
        # End If

        # 8. Compute the Maximum Power
        # MaximumPower = Max_Current_Before_Overflow * VBUS_MAX
        # MaximumPower = 3.2 * 32V
        # MaximumPower = 102.4W

        # Set multipliers to convert raw current/power values
        self._currentDivider_mA = 1.0; # Current LSB = 100uA per bit (1000/100 = 10)
        self._powerMultiplier_mW = 20; # Power LSB = 1mW per bit (2/1)

        # Set Calibration register to 'Cal' calculated above
        self.write(_REG_CALIBRATION,self._cal_value)

        # Set Config register to take into account the settings above
        self.bus_voltage_range = BusVoltageRange.RANGE_32V
        self.gain = Gain.DIV_8_320MV
        self.bus_adc_resolution = INA219_CONFIG_BADCRES_12BIT
        self.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.mode = Mode.SANDBVOLT_CONTINUOUS
        self.config = self.bus_voltage_range << 13 | \
                      self.gain << 11 | \
                      self.bus_adc_resolution | \
                      self.shunt_adc_resolution << 3 | \
                      self.mode
        self.write(_REG_CONFIG,self.config)

    def getShuntVoltage_mV(self):
        # self.write(_REG_CALIBRATION,self._cal_value)
        value = self.read(_REG_SHUNTVOLTAGE)
        if value > 32767:
            value -= 65535
        return value * 0.01

    def getBusVoltage_V(self):
        # self.write(_REG_CALIBRATION,self._cal_value)
        self.read(_REG_BUSVOLTAGE)
        return (self.read(_REG_BUSVOLTAGE) >> 3) * 0.004

    def getCurrent_mA(self):
        self.write(_REG_CALIBRATION,self._cal_value)
        value = self.read(_REG_CURRENT)
        if value > 32767:
            value -= 65535
        return (value / self._currentDivider_mA)

    def getPower_mW(self):
        self.write(_REG_CALIBRATION,self._cal_value)
        value = self.read(_REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._powerMultiplier_mW

    def test(self):
        low = 0
        bus_voltage = self.getBusVoltage_V()             # voltage on V- (load side)
        # shunt_voltage = self.getShuntVoltage_mV() / 1000 # voltage between V+ and V- across the shunt
        current = self.getCurrent_mA()                   # current in mA
        power = self.getPower_mW() / 1000                # power in W
        p = (bus_voltage - 3)/1.2*100
        if(p > 100):p = 100
        if(p < 0):p = 0
        # INA219 measure bus voltage on the load side. So PSU voltage = bus_voltage + shunt_voltage
        #print("PSU Voltage:   {:6.3f} V".format(bus_voltage + shunt_voltage))
        #print("Shunt Voltage: {:9.6f} V".format(shunt_voltage))
##        print("Load Voltage:  {:6.3f} V".format(bus_voltage))
##        print("Current:       {:6.3f} A".format(current/1000))
##        print("Power:         {:6.3f} W".format(power))
##        print("Percent:       {:3.1f}%".format(p))
ina = INA219(i2c_bus = 2,addr = 0x43)
#ina.test()

##SW INSERT UPS CODE END

# Draw Some Text
while True:
    oled.fill(0)
    oled.show()
    image = Image.new('1', (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    menu = 'UPS STATUS'
    left, top, right, bottom = font.getbbox(menu)
    menu_text_width = right - left
    menu_text_height = bottom - top

    draw.text(
        (oled.width // 2 - menu_text_width // 2, -4),
        menu,
        font=font,
        fill=255,
    )

    voltage = str(ina.getBusVoltage_V())
    voltage = voltage[:5]
    current = str(ina.getCurrent_mA() / 1000 )
    power = str(ina.getPower_mW() / 1000 )
    bus_voltage = ina.getBusVoltage_V()
    percent = (bus_voltage - 3)/1.2*100
    if(percent > 100):percent = 100
    if(percent < 0):percent = 0
    percent = str(percent)
    percent = percent[:5]

    draw.line(
        (0,7, oled.width,7),
        fill=255,
        width=1,
    )

    draw.line(
        (oled.width // 2,7, oled.width // 2,oled.height),
        fill=255,
        width=1,
    )

    draw.multiline_text(
        (0,4),
        'Volt : ' + voltage + ' V\nCurr : ' + current + ' A\nPwr : ' + power + ' W',
        font=font,
        fill=255,
        spacing=-3,
    )

    draw.multiline_text(
        (oled.width // 2 + 4,4),
        'Batt : ' + percent + ' %\nIface : ' + iface + '\nIP : ' + ip,
        font=font,
        fill=255,
        spacing=-3,
    )

#    draw.text(
#        (0, 3),
#        'Volt : ' + voltage + ' V',
#        font=font,
#        fill=255,
#    )
#    draw.text(
#        (0, 10),
#        'Curr : ' + current + ' A',
#        font=font,
#        fill=255,
#    )
#    draw.text(
#        (0, 17),
#        'Pwr  : ' + power + ' W',
#        font=font,
#        fill=255,
#    )
#    draw.text(
#        (0, 24),
#        'Batt : ' + percent + ' %',
#        font=font,
#        fill=255,
#    )

    # Display image
    oled.image(image)
    oled.show()
    time.sleep(3)