# code.py — D3 button cycles RGB on NEO_0; hold CAP1 for rainbow
import time
import board
import digitalio
import touchio

try:
    import neopixel
except ImportError:
    raise ImportError("Please copy neopixel.mpy into /lib")

# -----------------------
# Pins / hardware setup
# -----------------------
# Button on D3 (active-low)
button = digitalio.DigitalInOut(board.D3)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP  # not pressed=True, pressed=False

# Capacitive touch on CAP1
touch = touchio.TouchIn(board.CAP1)

# One NeoPixel on NEO_0
pixels = neopixel.NeoPixel(
    board.NEOPIXEL,
    1,
    brightness=0.25,
    auto_write=True,
)

# -----------------------
# Button edge-detect / debounce
# -----------------------
last_btn = True
last_edge_t = 0.0
DEBOUNCE_S = 0.05

#--------------------
# Touch sensor state
#--------------------
last_touch = False
rainbow_mode = False
#--------------------------------------
# Solid color cycle: blue -> green -> red
#--------------------------------------
colors = [ (0, 0, 255),(0, 255, 0),(255, 0, 0)]
colors_text = ["Blue", "Green", "Red"]
color_i = 0
pixels[0] = colors[color_i]

# -----------------------
# Rainbow helpers (adapted from boardtest_neopixel.py)
# -----------------------
def wheel(pos: int):
    # pos 0..255 -> color (R,G,B)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

#--------------------------------------
# Animation phase
#--------------------------------------
rainbow_step = 0

# -----------------------
# Main loop
# -----------------------
while True:
    now = time.monotonic()
    # Read both the Cap touch pad and User button
    cur_btn = button.value  # Active LOW -> True=not pressed, False=pressed
    current_touch = touch.value # Active HIGH -> True=pressed, False=not pressed

    if (current_touch and not last_touch):
        # Rainbow mode while CAP1 is touched
        rainbow_mode = True
        print("Rainbow mode!")
    if (rainbow_mode):    
        pixels[0] = wheel(rainbow_step & 255)  # single-pixel rainbow
        rainbow_step = (rainbow_step + 3) & 255       
        time.sleep(0.02)  # smooth animation
    else:
        # Solid color mode: detect button press to advance color
        if (last_btn is True) and (cur_btn is False) and ((now - last_edge_t) > DEBOUNCE_S):
            last_edge_t = now
            print("Primary color mode!")
            color_i = (color_i + 1) % len(colors)
            pixels[0] = colors[color_i]
        time.sleep(0.01)

    last_btn = cur_btn
    last_touch = current_touch

