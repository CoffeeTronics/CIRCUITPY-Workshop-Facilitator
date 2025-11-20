"""
This demo will initialize the display using displayio and draw a solid black
background, a Microchip "Meatball" logo, and move the logo around the screen from the IMU data
"""
import time
import board
import adafruit_icm20x
import displayio
import adafruit_imageload
import digitalio
import microcontroller
import neopixel

def DisableAutoReload():
    import supervisor
    supervisor.runtime.autoreload = False
    print("Auto-reload is currently disabled.")
    print("After saving your code, press the RESET button.")
    
# uncomment this if auto-reload is causing issues from your editor     
#DisableAutoReload()

# Change this to True to show debug print statements
Debug = False

pixel_pin = board.NEOPIXEL
num_pixels = 5

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)

# Turn off NeoPixels in case they were set on by a previous program
pixels.fill(0x000000)
pixels.show()

# Starting in CircuitPython 9.x fourwire will be a seperate internal library
# rather than a component of the displayio library
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
# from adafruit_display_text import label
from adafruit_st7789 import ST7789

i2c = board.I2C()  # uses board.SCL and board.SDA

try:
    icm = adafruit_icm20x.ICM20948(i2c, 0x69)
except:
    print("No ICM20948 found at default address 0x69. Trying alternate address 0x68.")
    icm = adafruit_icm20x.ICM20948(i2c, 0x68)

if Debug:
    print("Create pin called 'backlight' for LCD backlight on PA06")
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT
if Debug:
    print("Turn TFT Backlight On")
backlight.value = False # Backlight is Active LOW

# Release any resources currently in use for the displays
if Debug:
    print("Release displays")
displayio.release_displays()

if Debug:
    print("Create SPI Object for display")
spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135
LOGO_WIDTH = 32
LOGO_HEIGHT = 30

if Debug:
    print("Create DisplayBus")
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(
    display_bus, rotation=90, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, rowstart=40, colstart=53
)

# Load the sprite sheet (bitmap)
if Debug:
    print("Load Sprite sheet")
sprite_sheet, palette = adafruit_imageload.load("/Meatball_32x30_16color.bmp",
                                                bitmap=displayio.Bitmap,
                                                palette=displayio.Palette)

# Create a sprite (tilegrid)
if Debug:
    print("Create Sprite")
sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                            width=1,
                            height=1,
                            tile_width=LOGO_WIDTH,
                            tile_height=LOGO_HEIGHT)

# Create a Group to hold the sprite
if Debug:
    print("Create Group to hold Sprite")
group = displayio.Group(scale=1)

# Add the sprite to the Group
if Debug:
    print("Append Sprite to Group")
group.append(sprite)

# Add the Group to the Display
if Debug:
    print("Add Group to Display")
display.root_group = group

# Set sprite location
if Debug:
    print("Set Sprite Initial Location")
group.x = 150
group.y = 70

X_pos = 150
Y_pos = 70

# Adjust drift values to keep Meatball stable when on flat level surface
drift_X = 0.15
drift_Y = 0.7

while True:

    X, Y, Z = icm.acceleration

    if Debug:
        print("X: {:.2f}".format(X))
        print("Y: {:.2f}".format(Y))
        print("Z: {:.2f}".format(Z))
        print("")

    X_pos += int(X + drift_X)
    Y_pos -= int(Y + drift_Y)
    
    if Debug:
        print("X + drift_X", X + drift_X)
        print("Y + drift_Y", Y + drift_Y)

    if X_pos >= DISPLAY_WIDTH - LOGO_WIDTH:
        group.x = DISPLAY_WIDTH - LOGO_WIDTH
        X_pos = DISPLAY_WIDTH - LOGO_WIDTH
    else:
        group.x = X_pos

    if X_pos <= 0:
        group.x = 0
        X_pos = 0
    else:
        group.x = X_pos

    if Y_pos >= DISPLAY_HEIGHT - LOGO_HEIGHT:
        group.y = DISPLAY_HEIGHT - LOGO_HEIGHT
        Y_pos = DISPLAY_HEIGHT - LOGO_HEIGHT
    else:
        group.y = Y_pos

    if Y_pos <= 0:
        group.y = 0
        Y_pos = 0
    else:
        group.y = Y_pos

    time.sleep(0.02)
