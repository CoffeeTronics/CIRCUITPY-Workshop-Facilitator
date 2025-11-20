import time
import board
import displayio
import digitalio
import microcontroller
from fourwire import FourWire
from adafruit_st7789 import ST7789

# Change this to False to hide debug print statements
Debug = True

if Debug:
    print("Create pin called 'backlight' for LCD backlight on PA06")
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT

# Release any resources that may have been previously in use for the displays
if Debug:
    print("Release displays")
displayio.release_displays()

if Debug:
    print("Create SPI Object for display")
spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

if Debug:
    print("Turn TFT Backlight On")
# Backlight control is Active LOW    
backlight.value = False

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135

if Debug:
    print("Create DisplayBus")
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(
    display_bus, rotation=90, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, rowstart=40, colstart=53
)
x = 0   # This int will be used as an on display counter

while True:
    print("Hello World: ", x)
    x += 1          # increment x
    time.sleep(1)   # wait 1 sec