# code.py — Snake with CAP1 (A5) AI toggle + accelerometer steering + mode NeoPixel
#
# Adds a thin green border around the gameplay area (1 physical pixel).
# Keeps score/high-score > 10, shows Game Over overlay, NVM high-score.
# Plays 210.wav when food is eaten, 140.wav on Game Over.
#
import time
import board
import digitalio
import touchio
import displayio
import nvm
import struct
import microcontroller

import supervisor
supervisor.runtime.autoreload = True

# --- IMU (ICM-20948) ---
import adafruit_icm20x  # ensure adafruit_icm20x.mpy/.py is in /lib

# =========================
# AUDIO (same setup as your Gesture demo: WaveFile + AudioOut(board.DAC))
# =========================
# Gesture demo uses: from audiocore import WaveFile; from audioio import AudioOut; audio = AudioOut(board.DAC)
# We keep file handles open so playback is reliable on all builds.
try:
    from audiocore import WaveFile
    from audioio import AudioOut
    audio = AudioOut(board.DAC)  # use the on-board DAC pin feeding the amp

    _wav210_f = open("AudioFiles/210.wav", "rb")  # food sfx
    _wav210 = WaveFile(_wav210_f)

    _wav140_f = open("AudioFiles/140.wav", "rb")  # game over sfx
    _wav140 = WaveFile(_wav140_f)

    def _audio_play(w):
        try:
            if audio.playing:
                audio.stop()
        except Exception:
            pass
        try:
            audio.play(w)
        except Exception as e:
            print("Audio play error:", e)

    def sfx_food():
        _audio_play(_wav210)

    def sfx_gameover():
        _audio_play(_wav140)

except Exception as e:
    print("Audio init failed:", e)
    def sfx_food(): pass
    def sfx_gameover(): pass

# =========================
# Mode NeoPixel (status LED)
# =========================
try:
    import neopixel
    _modepix = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)
except Exception:
    _modepix = None

BLUE  = (0, 0, 255)
GREEN = (0, 255, 0)
OFF   = (0, 0, 0)

def _set_mode_pixel(demo_mode: bool):
    if not _modepix:
        return
    _modepix[0] = GREEN if demo_mode else BLUE

# =========================
# INPUTS
# =========================
cap_touch = touchio.TouchIn(board.A5)
last_captouch_state = False
DEMO_MODE = False

try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
except Exception:
    led = None

def flash_led(n=3, on_s=0.05, off_s=0.05):
    if not led: return
    for _ in range(n):
        led.value = True;  time.sleep(on_s)
        led.value = False; time.sleep(off_s)

# =========================
# DISPLAY (ICM20948_IMU_Meatball style)
# =========================
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
from adafruit_st7789 import ST7789

# Backlight on PA06
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT

displayio.release_displays()

spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

backlight.value = False

WIDTH = 240
HEIGHT = 135
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(display_bus, rotation=90, width=WIDTH, height=HEIGHT, rowstart=40, colstart=53)

# ===== High Score via NVM =====
NVM_MAGIC = b"HSv1"
NVM_FMT   = "<4sH"
NVM_SIZE  = struct.calcsize(NVM_FMT)

high_score = 0

def _nvm_available():
    return getattr(microcontroller, "nvm", None) is not None

def load_high_score():
    global high_score
    if not _nvm_available() or len(microcontroller.nvm) < NVM_SIZE:
        high_score = 0
        return
    raw = bytes(microcontroller.nvm[0:NVM_SIZE])
    try:
        magic, hs = struct.unpack(NVM_FMT, raw)
        high_score = hs if magic == NVM_MAGIC else 0
    except Exception:
        high_score = 0

def save_high_score():
    if not _nvm_available() or len(microcontroller.nvm) < NVM_SIZE:
        return
    microcontroller.nvm[0:NVM_SIZE] = struct.pack(
        NVM_FMT, NVM_MAGIC, min(high_score, 65535)
    )

# =========================
# RENDER SURFACE
# =========================
GRID_W = 24
GRID_H = 18
BG_RGB     = 0x101018
SNAKE_RGB  = 0x33FF55
HEAD_RGB   = 0x00DDFF
FOOD_RGB   = 0xFF3355

SCALE = max(1, min(WIDTH // GRID_W, HEIGHT // GRID_H))
bmp_w, bmp_h = GRID_W, GRID_H
bitmap = displayio.Bitmap(bmp_w, bmp_h, 4)
palette = displayio.Palette(4)
palette[0] = BG_RGB
palette[1] = SNAKE_RGB
palette[2] = FOOD_RGB
palette[3] = HEAD_RGB

tg = displayio.TileGrid(bitmap, pixel_shader=palette)
game_layer = displayio.Group(
    scale=SCALE,
    x=(WIDTH  - bmp_w * SCALE) // 2,
    y=(HEIGHT - bmp_h * SCALE) // 2,
)
game_layer.append(tg)

root = displayio.Group()
display.root_group = root
root.append(game_layer)
ui = displayio.Group()
root.append(ui)

# ---------- Thin border around gameplay area (green) ----------
BORDER_COLOR = 0x00FF00  # green
try:
    from vectorio import Rectangle as VRectangle
    _use_vectorio = True
except Exception:
    _use_vectorio = False

def _add_green_border():
    width_px  = bmp_w * SCALE
    height_px = bmp_h * SCALE
    x0 = game_layer.x
    y0 = game_layer.y

    border_group = displayio.Group()
    if _use_vectorio:
        pal = displayio.Palette(1); pal[0] = BORDER_COLOR
        border_group.append(VRectangle(pixel_shader=pal, x=x0,               y=y0 - 1,            width=width_px,  height=1))
        border_group.append(VRectangle(pixel_shader=pal, x=x0,               y=y0 + height_px,    width=width_px,  height=1))
        border_group.append(VRectangle(pixel_shader=pal, x=x0 - 1,           y=y0,                width=1,         height=height_px))
        border_group.append(VRectangle(pixel_shader=pal, x=x0 + width_px,    y=y0,                width=1,         height=height_px))
    else:
        pal = displayio.Palette(1); pal[0] = BORDER_COLOR
        top_bmp    = displayio.Bitmap(width_px, 1, 1)
        bottom_bmp = displayio.Bitmap(width_px, 1, 1)
        left_bmp   = displayio.Bitmap(1, height_px, 1)
        right_bmp  = displayio.Bitmap(1, height_px, 1)
        for x in range(width_px):
            top_bmp[x, 0] = 0
            bottom_bmp[x, 0] = 0
        for y in range(height_px):
            left_bmp[0, y] = 0
            right_bmp[0, y] = 0
        border_group.append(displayio.TileGrid(top_bmp,    pixel_shader=pal, x=x0,               y=y0 - 1))
        border_group.append(displayio.TileGrid(bottom_bmp, pixel_shader=pal, x=x0,               y=y0 + height_px))
        border_group.append(displayio.TileGrid(left_bmp,   pixel_shader=pal, x=x0 - 1,           y=y0))
        border_group.append(displayio.TileGrid(right_bmp,  pixel_shader=pal, x=x0 + width_px,    y=y0))

    root.append(border_group)

_add_green_border()
# --------------------------------------------------------------

# =========================
# IMU SETUP (ICM-20948)
# =========================
i2c = board.I2C()
#icm = adafruit_icm20x.ICM20948(i2c, 0x69)
try:
    icm = adafruit_icm20x.ICM20948(i2c, 0x69)
except:
    print("No ICM20948 found at default address 0x69. Trying alternate address 0x68.")
    icm = adafruit_icm20x.ICM20948(i2c, 0x68)

ax_f = 0.0
ay_f = 0.0
LPF_ALPHA = 0.25

# =========================
# GAME STATE
# =========================
UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = (1,  0)

snake = [(GRID_W // 2 + i, GRID_H // 2) for i in range(1, -3, -1)]
direction = RIGHT
food = (GRID_W // 3, GRID_H // 3)
grow = 0

def place_food():
    global food
    start = ((food[0] + 7) % GRID_W, (food[1] + 5) % GRID_H)
    snake_set = set(snake)
    for dy in range(GRID_H):
        for dx in range(GRID_W):
            x = (start[0] + dx) % GRID_W
            y = (start[1] + dy) % GRID_H
            if (x, y) not in snake_set:
                food = (x, y); return

def _neighbors_preferring_food(head, target):
    hx, hy = head; fx, fy = target
    dx = 1 if fx > hx else (-1 if fx < hx else 0)
    dy = 1 if fy > hy else (-1 if fy < hy else 0)
    if abs(fx - hx) >= abs(fy - hy):
        ordered = [(dx, 0), (0, dy), (-dx, 0), (0, -dy)]
    else:
        ordered = [(0, dy), (dx, 0), (0, -dy), (-dx, 0)]
    out = []
    for d in ordered + [RIGHT, LEFT, DOWN, UP]:
        if d not in out: out.append(d)
    return out

def _would_collide(pos, body_set):
    x, y = pos
    return (x < 0) or (y < 0) or (x >= GRID_W) or (y >= GRID_H) or (pos in body_set)

def ai_next_dir(head, body, target, cur_dir):
    body_set = set(body)
    rev = (-cur_dir[0], -cur_dir[1])
    for d in _neighbors_preferring_food(head, target):
        if d == rev: continue
        nx, ny = head[0] + d[0], head[1] + d[1]
        if not _would_collide((nx, ny), body_set): return d
    nx, ny = head[0] + cur_dir[0], head[1] + cur_dir[1]
    if not _would_collide((nx, ny), body_set): return cur_dir
    for d in (RIGHT, DOWN, LEFT, UP):
        if d == rev: continue
        nx, ny = head[0] + d[0], head[1] + d[1]
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H: return d
    return cur_dir

# =========================
# INPUT: CAP1 toggle + IMU tilt steering
# =========================
TILT_THRESH = 2.2

def update_inputs():
    global DEMO_MODE, last_captouch_state, direction, ax_f, ay_f

    cap_now = cap_touch.value
    if cap_now and (not last_captouch_state):
        DEMO_MODE = not DEMO_MODE
        _set_mode_pixel(DEMO_MODE)
        flash_led(3)
        print("DEMO_MODE:", DEMO_MODE)
    last_captouch_state = cap_now

    if DEMO_MODE:
        return

    ax, ay, az = icm.acceleration
    ax_f = (1.0 - LPF_ALPHA) * ax_f + LPF_ALPHA * ax
    ay_f = (1.0 - LPF_ALPHA) * ay_f + LPF_ALPHA * ay

    absx = abs(ax_f); absy = abs(ay_f)
    new_dir = None
    if absx >= absy and absx > TILT_THRESH:
        new_dir = RIGHT if ax_f > 0 else LEFT
    elif absy > TILT_THRESH:
        new_dir = UP if ay_f > 0 else DOWN

    if new_dir is None:
        return

    rev = (-direction[0], -direction[1])
    if new_dir == rev:
        return
    direction = new_dir

# =========================
# GAME OVER overlay (title + score + high for 3s)
# =========================
import terminalio
from adafruit_display_text import bitmap_label

score = 0
score_label = bitmap_label.Label(
    terminalio.FONT,
    text="0",
    color=0xFFFFFF,
    scale=2,
    anchor_point=(1.0, 0.0),
    anchored_position=(WIDTH - 2, 2),
)
ui.append(score_label)

def update_score_label():
    score_label.text = str(score)

def _flash_screen_red(duration=0.15):
    old_bg = palette[0]
    palette[0] = 0xFF0000
    for y in range(GRID_H):
        for x in range(GRID_W):
            bitmap[x, y] = 0
    time.sleep(duration)
    palette[0] = old_bg

def _show_game_over_stats(duration=3.0):
    overlay = displayio.Group()
    title = bitmap_label.Label(
        terminalio.FONT,
        text="Game Over",
        color=0xFFFFFF,
        scale=4,
        anchor_point=(0.5, 0.5),
        anchored_position=(WIDTH // 2, HEIGHT // 2 - 14),
    )
    overlay.append(title)
    stats = bitmap_label.Label(
        terminalio.FONT,
        text=f"Score: {score}   High: {high_score}",
        color=0xFFFFFF,
        scale=2,
        anchor_point=(0.5, 0.0),
        anchored_position=(WIDTH // 2, HEIGHT // 2 + 8),
    )
    overlay.append(stats)
    ui.append(overlay)
    time.sleep(duration)
    ui.remove(overlay)

def game_over_sequence():
    # play the game-over WAV just like the Gesture demo does
    sfx_gameover()
    _flash_screen_red(0.15)
    _show_game_over_stats(3.0)

# =========================
# GAME LOGIC + RENDER
# =========================
def reset_game(reset_score=True):
    global snake, direction, grow, score
    snake = [(GRID_W // 2 + i, GRID_H // 2) for i in range(1, -3, -1)]
    direction = RIGHT
    grow = 0
    if reset_score:
        score = 0
        update_score_label()

def step_game():
    global direction, grow, snake, food, score, high_score
    if DEMO_MODE:
        direction = ai_next_dir(snake[0], snake, food, direction)

    nx = snake[0][0] + direction[0]
    ny = snake[0][1] + direction[1]

    out_of_bounds = (nx < 0) or (ny < 0) or (nx >= GRID_W) or (ny >= GRID_H)
    hit_self = (nx, ny) in snake

    if out_of_bounds:
        game_over_sequence()
        reset_game(reset_score=not DEMO_MODE)
        return
    elif hit_self:
        game_over_sequence()
        reset_game(reset_score=not DEMO_MODE)
        return

    snake.insert(0, (nx, ny))

    if (nx, ny) == food:
        if not DEMO_MODE:
            score += 1
            update_score_label()
            # play the eat-food WAV just like the Gesture demo does
            sfx_food()
            if score > high_score:
                high_score = score
                try:
                    save_high_score()
                except Exception:
                    pass
        grow += 2
        place_food()

    if grow > 0:
        grow -= 1
    else:
        snake.pop()

def render():
    for y in range(GRID_H):
        for x in range(GRID_W):
            bitmap[x, y] = 0
    bitmap[food[0], food[1]] = 2
    for i, (x, y) in enumerate(snake):
        bitmap[x, y] = 3 if i == 0 else 1

load_high_score()

# =========================
# MAIN LOOP
# =========================
_set_mode_pixel(False)

TICK_S = 0.12
last_tick = 0.0
while True:
    update_inputs()
    now = time.monotonic()
    if now - last_tick >= TICK_S:
        last_tick = now
        step_game()
        render()
    time.sleep(0.005)
