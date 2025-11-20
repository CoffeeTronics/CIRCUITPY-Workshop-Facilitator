# code.py — D3 button cycles RGB on NEO_0
import time
import board
import digitalio

try:
    import neopixel
except ImportError:
    raise ImportError("Please copy neopixel.mpy into /lib")

# Button on D3 (active-low)
button = digitalio.DigitalInOut(board.D3)
button.direction = digitalio.Direction.INPUT

# One NeoPixel on NEO_0
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.25, auto_write=True)

# Solid color cycle: blue -> green -> red
colors = [ (0, 0, 255),(0, 255, 0),(255, 0, 0)]
colors_text = ["Blue", "Green", "Red"]
color_i = 0
pixels[0] = colors[color_i]

# initialize button state and last button state
current_button_state = True
last_button_state = True

print("Len colors: ", len(colors))

while True:
    # Read both the Cap touch pad and User button
    current_button_state = button.value  # Active LOW -> True=not pressed, False=pressed

    # Solid color mode: detect button press to advance color
    if (not last_button_state) and (current_button_state):
        # Is there a problem with this?
        color_i = (color_i + 1) % len(colors)
        pixels[0] = colors[color_i]
        print(f"Changed to {colors_text[color_i]}")

    last_button_state = current_button_state


