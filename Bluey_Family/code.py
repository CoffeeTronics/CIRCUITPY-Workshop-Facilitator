# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This code simply displays an image of the children's character Bluey and their family.
The point is to show to quality of the display that is being used in this kit. 
"""
import board
import displayio
import adafruit_imageload
import digitalio
import microcontroller
from fourwire import FourWire
# from adafruit_display_text import label
from adafruit_st7789 import ST7789

# Change this to True to show debug print statements
Debug = True

if Debug:
    print("Create pin called 'backlight' for LCD backlight on PA06")
# backlight = digitalio.DigitalInOut(board.LCD_LEDA)
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT

# Release any resources currently in use for the displays
if Debug:
    print("Release displays")
displayio.release_displays()

if Debug:
    print("Create SPI Object for display")
spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

if Debug:
    print("Turn Display Backlight On")
backlight.value = False # backlight is Active LOW

# Display dimensions: 240 x 135
# Logo Dimensions: 32 x 30
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135
LOGO_WIDTH = 240 #32
LOGO_HEIGHT = 135 #30

if Debug:
    print("Create DisplayBus")
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(display_bus, rotation=90, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, rowstart=40, colstart=53)

# Load the sprite sheet (bitmap)
if Debug:
    print("Load Sprite sheet")
sprite_sheet, palette = adafruit_imageload.load("/Bluey_Family/Bluey_Family.bmp",        #"/Meatball_32x30_16color.bmp",
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
group.x = int((DISPLAY_WIDTH / 2) - (LOGO_WIDTH / 2))   #150
group.y = int((DISPLAY_HEIGHT / 2) - (LOGO_HEIGHT / 2))   #70



while True:
    pass







