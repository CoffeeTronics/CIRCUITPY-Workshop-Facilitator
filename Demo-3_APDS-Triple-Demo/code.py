'''
Project 3: APDS9960 Proximity, Gesture, Color
This sensor has 3 functions:
   - Proximity
   - Gesture Detect
   - Color Detect
This project uses a state machine operated by the Cap Touch button to switch between the 3 functions.
When in the Proximity function, an audio tone is generated that is inversely proportional to the distance measured
When in the Gesture function, 4 gestures are supported by the device: Up, Down, Left, Right. Each gesture is mapped to a WAV file
so that the WAV file is played when that gesture is detected.
When in the Color function, the sensor reads the RGB makeup of objects placed close to it. The display prints the RGB components, and
the NeoPixels reproduce the color sensed.  
'''

import time
import board
import touchio
import digitalio
import displayio
from adafruit_apds9960.apds9960 import APDS9960
from audiocore import WaveFile
from audioio import AudioOut
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import microcontroller
import neopixel
from analogio import AnalogOut
from micropython import const
import sys

def DisableAutoReload():
   import supervisor
   supervisor.runtime.autoreload = False
   print("Autoreload disabled. After saving code, use CTRL-D, then CTRL-C to run your code")
   
# Uncomment this if you have problems with your editor autosaving causing frequent restarts   
# DisableAutoReload()

# Used for debugging, change to False to disable debugging print statements
DEBUG = True

# CAP1 is the capacitive touch pin
cap_touch_pad = board.CAP1  
# Configure Cap Touch pad as an input with touchio
cap_touch = touchio.TouchIn(cap_touch_pad)

# Configure onboard LED as OUTPUT
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Set initial states for Cap Touch pad
current_captouch_state = False
last_captouch_state = False

# States for switching between prox theremin/gesture WAV/color detect and match
GESTURE_WAV_STATE = 1
PROX_THEREMIN_STATE = 2
COLOR_STATE = 3

# Set initial state for demos
# Task: Decide on a starting state
# Your code here:
demo_state = GESTURE_WAV_STATE

# Booleans used to run each demo after cap touch button press
# Task: Figure out the starting state for all demos 
runGestureDemo = False      # delete this!
runProxDemo = False         # delete this!
runColorDemo = False        # delete this!

# Turn off all NeoPixels in case they were turned on by previous program
NEOPIXEL_OFF = const(0x000000)
pixel_pin = board.NEOPIXEL
num_pixels = 5
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=False)
pixels.fill(NEOPIXEL_OFF)
pixels.show()

# RGB Color measurement values are 16-bit. However NeoPixels use 8-bit values.
# To translate between RGB Color values and NeoPixel values requires a bitshift to the RIGHT of 8 places
NUM_BITSHIFTS_NEOPIXEL = 8

# FourWire is used for SPI bus
from fourwire import FourWire
# ST7789 is the display driver used for our TFT display
from adafruit_st7789 import ST7789

# Release any resources from previously used displays
if DEBUG:
    print("Release any previously used displays")
displayio.release_displays()

try:
    i2c = board.I2C()       # use board.SCL and board.SDA pins
    apds = APDS9960(i2c)    # create instance of apds object for prox, gesture, color sensor
except:
    print("APDS9960 breakout board not found! Connect it to the QWIIC connector and press reset button!")
    sys.exit()

# Five gestures are detected by the sensor:
# No gesture (0x0), up swipe (0x1), down swipe (0x2), left swipe (0x3), right swipe (0x4)
NO_GESTURE = 0x0
UP_GESTURE = 0x1
DOWN_GESTURE = 0x2
LEFT_GESTURE = 0x3
RIGHT_GESTURE = 0x4

# Instantiate SPI object for SPI bus using SPI peripheral
if DEBUG:
    print("Create SPI Object for display")
spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

if DEBUG:
    print("Create pin called 'backlight' for LCD backlight on PA06")
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT
if DEBUG:
    print("Turn TFT Backlight On")
# Backlight is Active LOW
backlight.value = False

if DEBUG:
    print("Create DisplayBus")
# set up SPI display. Display dimensions are 240x135
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(display_bus, rotation=90, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT,
                 rowstart=40, colstart=53)

# Task: Set text label colors - display uses 8-bit values for RGB: 0xRRGGBB or (RR, GG, BB)
# Your code here:
CONST_TEXT_COLOR_WHITE = const(0xFFFFFF)
CONST_TEXT_COLOR_RED = const(0xFF0000)
CONST_TEXT_COLOR_GREEN = const(0x00FF00)
CONST_TEXT_COLOR_BLUE = const(0x0000FF)
# Add any other colors you like

# Set font and text labels
font = bitmap_font.load_font("/Helvetica-Bold-16.bdf")
text_area1 = label.Label(font, text="APDS-9960 demo", color=CONST_TEXT_COLOR_WHITE)
text_area2 = label.Label(font, text="3 Projects in 1:", color=CONST_TEXT_COLOR_WHITE)
text_area3 = label.Label(font, text="Prox, Gesture, Color", color=CONST_TEXT_COLOR_WHITE)
text_area4 = label.Label(font, text="Use Cap Touch button", color=CONST_TEXT_COLOR_WHITE)

# Set positions for the labels
if DEBUG:
    print("Set text label positions")
text_area1.x = 0
text_area1.y = 20
# The nested group's items can have their own coordinates relative to the nested group
text_area2.x = 0
text_area2.y = 50

text_area3.x = 0
text_area3.y = 80

text_area4.x = 0
text_area4.y = 110

# Create the parent group
parent_group = displayio.Group()

# Add the first label directly to the parent group
parent_group.append(text_area1)
parent_group.append(text_area2)
parent_group.append(text_area3)
parent_group.append(text_area4)
# Show the parent group on the display
display.root_group = parent_group

# Show labels for 2 seconds
time.sleep(2)

# Opens WAV files to play for each gesture - note "rb" stands for "readable binary"
# WAV files need to be Mono 16-bit at 22kHz or less. Use Audacity 
def init_WAV_files():
    # Reinitialize audio object in case it was deinitialized
    global audio
    # This is the pin that will output the WAV file audio
    audio = AudioOut(board.DAC)
    
    # Open WAV files to play for each gesture - note "rb" stands for "readable binary"
    # WAV files need to be Mono 16-bit at 22kHz or less
    global wave_down, wave_up, wave_left, wave_right, wave_silent
    
    wave_file_down = open("AudioFiles/140.wav", "rb")     
    wave_down = WaveFile(wave_file_down)

    wave_file_up = open("AudioFiles/304.wav", "rb")
    wave_up = WaveFile(wave_file_up)

    wave_file_left = open("AudioFiles/210.wav", "rb")
    wave_left = WaveFile(wave_file_left)

    wave_file_right = open("AudioFiles/320.wav", "rb")
    wave_right = WaveFile(wave_file_right)

    wave_file_silent = open("AudioFiles/Silent.wav", "rb")
    wave_silent = WaveFile(wave_file_silent)

    audio.play(wave_silent)

init_WAV_files()

# Map 8-bit value from proximity sensor to 10-bit value for DAC
# Task: Write a function that converts an 8-bit value to a 10-bit value. Make sure it cannot accidentally overflow!
# Your code here:
def map_8bit_to_10bit_clamped(value_8bit):  
    return min(value_8bit << 2, 1023)       # Delete this!

def gesture_wav():
    # Task: Read the gesture from the APDS sensor
    # Documentation here: https://docs.circuitpython.org/projects/apds9960
    # Your code here:
    gesture = apds.gesture()    # Delete this!

    # Save the initial state of last_gesture to avoid spamming the terminal
    last_gesture = NO_GESTURE   

    if (gesture == NO_GESTURE) and (last_gesture != gesture):   # if no gesture, wait for a gesture
        if DEBUG:
            print("No gesture!")
        gesture = apds.gesture()
    # convert gesture reading into human readable format
    elif gesture == UP_GESTURE:
        if DEBUG:
            print("up")
        audio.play(wave_up)
        text_area3.text = "UP"
    elif gesture == DOWN_GESTURE:
        if DEBUG:
            print("down")
        audio.play(wave_down)
        text_area3.text = "DOWN"
    elif gesture == LEFT_GESTURE:
        if DEBUG:
            print("left")
        audio.play(wave_left)
        text_area3.text = "LEFT"
    elif gesture == RIGHT_GESTURE:
        if DEBUG:
            print("right")
        audio.play(wave_right)
        text_area3.text = "RIGHT"

    # Save gesture state for next time through the loop
    last_gesture = gesture

def prox_theremin():
    apds.enable_proximity = True
    apds.enable_gesture = False
    apds.enable_color = False

    prox = apds.proximity # 8-bit value returns 0-255
    # The DAC uses 10-bit values
    dac_input = map_8bit_to_10bit_clamped(prox)
    if DEBUG:
        print("8-bit val:",prox, "10-bit val: ",dac_input,"\n")

    str1 = (f"Prox sensor reading: {prox} \n")
    str2 = (f"DAC output: {dac_input} \n")

    text_area1.color = CONST_TEXT_COLOR_WHITE
    text_area2.color = CONST_TEXT_COLOR_WHITE

    text_area1.text = str1
    text_area2.text = str2

    if dac_input <= 5:
        analog_out.value = 0
    else:
        for i in range (0, 65535, dac_input):
            analog_out.value = i

def color_detect():
    # to read colors, we need to enable color sensor
    apds.enable_proximity = False
    apds.enable_gesture = False
    apds.enable_color = True

    red, green, blue, clear = apds.color_data
    if DEBUG:
        print("Red: ",red, "\t\t", "Green: ",green, "\t\t", "Blue: ",blue, "\t\t", "Clear: ",clear, "\n")

    str1 = (f"RED: {red} \n")
    str2 = (f"GREEN: {green} \n")
    str3 = (f"BLUE: {blue} \n")
    str4 = (f"CLEAR: {clear} ")

    # Print RED color in red, GREEN color in green, BLUE color in blue, and CLEAR as white
    text_area1.color = CONST_TEXT_COLOR_RED
    text_area2.color = CONST_TEXT_COLOR_GREEN
    text_area3.color = CONST_TEXT_COLOR_BLUE
    text_area4.color = CONST_TEXT_COLOR_WHITE

    # Set each text area to its corresoponding string
    text_area1.text = str1
    text_area2.text = str2
    text_area3.text = str3
    text_area4.text = str4

    # To convert a 16-bit value to an 8-bit value, it must be bitshifted to the right 8 places
    BITSHIFT_16BIT_TO_8BIT = const(8)

    red_shifted = red >> BITSHIFT_16BIT_TO_8BIT
    green_shifted = green >> BITSHIFT_16BIT_TO_8BIT
    blue_shifted = blue >> BITSHIFT_16BIT_TO_8BIT

    if DEBUG:
        print("Red shifted: ",red_shifted, "\t", "Green shifted: ",green_shifted, "\t", "Blue shifted: ", blue_shifted, "\t", "Clear: ", clear)

    # Task: The RGB values red_shifted, green_shifted and blue_shifted need to be combined into 1 value to be written to the NeoPixels
    # Your code here:
    neopixel_color = (red_shifted << 16) | (green_shifted << 8) | (blue_shifted)    # Delete this!

    # Match color sensors values on NeoPixels
    pixels.fill(neopixel_color)
    # Turn off Nano pixel
    pixels[0] = NEOPIXEL_OFF
    pixels.show()

    time.sleep(0.5)

while True:
    # Task: Read the Cap Touch pad and store it in current_captouch_state
    # Refer to the docs: https://docs.circuitpython.org/en/latest/shared-bindings/digitalio/
    current_captouch_state = cap_touch.value    # Delete this!

    # State machine uses Cap Touch pad and current state to set next state
    # Task: How to determine whether Cap Touch pad has been touched?
    # Your code here:    
    if (current_captouch_state and not last_captouch_state):    # Delete this!
        if DEBUG:
            print("Touched!")
        led.value = True
        if demo_state == GESTURE_WAV_STATE:     # if we are currently in GESTURE_WAV_STATE, next state is PROX_THEREMIN_STATE
           demo_state = PROX_THEREMIN_STATE
           text_area1.text = "Proximity Theremin"
           text_area2.text = "Move hand toward sensor"
           text_area3.text = "                       "
           text_area4.text = "                       "
           audio.deinit()   # Deinit resources used for outputting WAV file on DAC pin
           analog_out = AnalogOut(board.DAC)    # Init resources for outputting a tone on DAC pin
           # Task: Set booleans to determine which demo to run
           # Your code here:
           runGestureDemo = False   # Delete this!
           runProxDemo = True       # Delete this!
           runColorDemo = False     # Delete this!
           time.sleep(2)
        elif demo_state == PROX_THEREMIN_STATE: # if we are currently in PROX_THEREMIN_STATE, next state is COLOR_STATE
            demo_state = COLOR_STATE
            text_area1.text = "Color Detection"
            text_area2.text = "Place cellophane over sensor"
            text_area3.text = "                            "
            # Task: Set booleans to determine which demo to run
            # Your code here:
            runGestureDemo = False      # delete this!
            runProxDemo = False         # delete this!
            runColorDemo = True         # delete this!
            time.sleep(2)
        elif demo_state == COLOR_STATE:         # if we are currently in COLOR_STATE, next state is GESTURE_WAV_STATE
            demo_state = GESTURE_WAV_STATE
            text_area1.color = CONST_TEXT_COLOR_WHITE
            text_area2.color = CONST_TEXT_COLOR_WHITE
            text_area3.color = CONST_TEXT_COLOR_WHITE
            text_area4.color = CONST_TEXT_COLOR_WHITE
            text_area1.text = "Gesture Detection"
            text_area2.text = "Move hand over sensor"
            text_area3.text = "                            "
            text_area4.text = "                            "
            # Release resources from prox tone
            analog_out.deinit()
            init_WAV_files()
            # Task: Set booleans to determine which demo to run
            # Your code here:
            runGestureDemo = True   # delete this!
            runProxDemo = False     # delete this!
            runColorDemo = False    # delete this!
            time.sleep(2)
        if DEBUG:
            print("Demo State: ", demo_state)

    # Task: write the if statement to detect when the Cap Touch pad has been touched
    # Your code here:
    elif (last_captouch_state and not current_captouch_state):    # delete this!
        if DEBUG:
            print("Released!")
        led.value = False

    if runGestureDemo:
        # To read gestures, we need to enable both proximity AND gesture
        apds.enable_proximity = True
        apds.enable_gesture = True
        apds.enable_color = False
        # Turn NeoPixels off as we have just come from running the Color demo
        pixels.fill(NEOPIXEL_OFF)
        pixels.show()
        gesture_wav()
    elif runProxDemo:
        prox_theremin()
    elif runColorDemo:
        color_detect()

    time.sleep(0.05)

    # Save Cap Touch state for next time through the loop
    last_captouch_state = current_captouch_state
