# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""
Donkey Kong for CircuitPython with IMU Control
Tilt board left/right to move, D3 button to jump
Uses bitmap sprites: DK.bmp, princess.bmp, mario.bmp
"""
import time
import board
import adafruit_icm20x
import displayio
import adafruit_imageload
import digitalio
import microcontroller
import neopixel
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle

def DisableAutoReload():
    import supervisor
    supervisor.runtime.autoreload = False
    print("Auto-reload disabled. Press RESET after saving.")
    
DisableAutoReload()

# Change this to True to show debug print statements
Debug = False

# NeoPixel setup
pixel_pin = board.NEOPIXEL
num_pixels = 5
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)
pixels.fill(0x000000)
pixels.show()

# Display setup (from IMU Meatball demo)
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
from adafruit_st7789 import ST7789

# IMU setup
i2c = board.I2C()  # uses board.SCL and board.SDA

try:
    icm = adafruit_icm20x.ICM20948(i2c, 0x68)
    print("ICM20948 found at address 0x68")
except:
    print("No ICM20948 found at default address 0x68. Trying alternate address 0x69.")
    try:
        icm = adafruit_icm20x.ICM20948(i2c, 0x69)
        print("ICM20948 found at address 0x69")
    except:
        print("ERROR: No ICM20948 found!")

# Create backlight pin (Active LOW)
backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
backlight.direction = digitalio.Direction.OUTPUT

# Release any displays
displayio.release_displays()

# Setup SPI display
spi = board.LCD_SPI()
tft_cs = board.LCD_CS
tft_dc = board.D4

backlight.value = False  # Active LOW - turns backlight ON

WIDTH = 240
HEIGHT = 135

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = ST7789(
    display_bus, rotation=90, width=WIDTH, height=HEIGHT, rowstart=40, colstart=53
)

# Jump button setup (D3)
button_jump = digitalio.DigitalInOut(board.D3)
button_jump.direction = digitalio.Direction.INPUT
button_jump.pull = digitalio.Pull.UP

# Game constants
GRAVITY = 1
JUMP_STRENGTH = -12
PLATFORM_HEIGHT = 4

# Sprite dimensions (adjust based on your BMP files)
MARIO_WIDTH = 16
MARIO_HEIGHT = 16
DK_WIDTH = 32
DK_HEIGHT = 32
PRINCESS_WIDTH = 16
PRINCESS_HEIGHT = 16
BARREL_SIZE = 8

# IMU sensitivity (adjust these for better control)
IMU_SENSITIVITY = 1.5  # How much tilt affects movement
IMU_DEADZONE = 0.3     # Ignore small tilts

# Colors
COLOR_BLACK = 0x000000
COLOR_WHITE = 0xFFFFFF
COLOR_RED = 0xFF0000
COLOR_BLUE = 0x0000FF
COLOR_BROWN = 0x8B4513
COLOR_YELLOW = 0xFFFF00
COLOR_PINK = 0xFF69B4
COLOR_GREEN = 0x00FF00

# Load bitmap sprites
if Debug:
    print("Loading sprites...")

# Load splash screen
try:
    splash_bitmap, splash_palette = adafruit_imageload.load(
        "/DK_splash.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    print("Splash screen loaded")
except Exception as e:
    print(f"Error loading DK_splash.bmp: {e}")
    splash_bitmap = None

try:
    # Load Mario sprite
    mario_bitmap, mario_palette = adafruit_imageload.load(
        "/mario.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    if Debug:
        print("Mario sprite loaded")
except Exception as e:
    print(f"Error loading mario.bmp: {e}")
    mario_bitmap = None

try:
    # Load Donkey Kong sprite
    dk_bitmap, dk_palette = adafruit_imageload.load(
        "/DK.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    if Debug:
        print("DK sprite loaded")
except Exception as e:
    print(f"Error loading DK.bmp: {e}")
    dk_bitmap = None

try:
    # Load Princess sprite
    princess_bitmap, princess_palette = adafruit_imageload.load(
        "/princess.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    if Debug:
        print("Princess sprite loaded")
except Exception as e:
    print(f"Error loading princess.bmp: {e}")
    princess_bitmap = None

class Player:
    def __init__(self, x, y, bitmap, palette):
        self.x = x
        self.y = y
        self.vel_y = 0
        self.is_jumping = False
        self.on_ground = False
        
        # Create sprite or fallback to circle
        if bitmap is not None:
            try:
                # Check if bitmap dimensions match expected tile size
                if bitmap.width == MARIO_WIDTH and bitmap.height == MARIO_HEIGHT:
                    # Single sprite - no tiling needed
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette
                    )
                else:
                    # Try to create tiled sprite
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette,
                        width=1,
                        height=1,
                        tile_width=MARIO_WIDTH,
                        tile_height=MARIO_HEIGHT
                    )
            except ValueError as e:
                print(f"Mario sprite error: {e}, using fallback")
                self.sprite = Circle(x, y, MARIO_WIDTH//2, fill=COLOR_RED)
        else:
            self.sprite = Circle(x, y, MARIO_WIDTH//2, fill=COLOR_RED)
        
        self.sprite.x = int(x)
        self.sprite.y = int(y)
        
    def update(self, platforms):
        # Apply gravity
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # Check platform collisions
        self.on_ground = False
        for platform in platforms:
            if (self.x > platform['x'] and 
                self.x < platform['x'] + platform['width'] and
                self.y + MARIO_HEIGHT >= platform['y'] and
                self.y + MARIO_HEIGHT <= platform['y'] + PLATFORM_HEIGHT + 5 and
                self.vel_y >= 0):
                self.y = platform['y'] - MARIO_HEIGHT
                self.vel_y = 0
                self.on_ground = True
                self.is_jumping = False
                
        # Keep player on screen
        if self.y >= HEIGHT - MARIO_HEIGHT:
            self.y = HEIGHT - MARIO_HEIGHT
            self.vel_y = 0
            self.on_ground = True
            self.is_jumping = False
            
        if self.x < 0:
            self.x = 0
        if self.x > WIDTH - MARIO_WIDTH:
            self.x = WIDTH - MARIO_WIDTH
            
        # Update sprite position
        self.sprite.x = int(self.x)
        self.sprite.y = int(self.y)
    
    def move_imu(self, accel_x):
        """Move player based on IMU X acceleration"""
        # Apply deadzone
        if abs(accel_x) < IMU_DEADZONE:
            return
            
        # Move player (positive - tilt right moves right, tilt left moves left)
        self.x += accel_x * IMU_SENSITIVITY
        
    def jump(self):
        if self.on_ground and not self.is_jumping:
            self.vel_y = JUMP_STRENGTH
            self.is_jumping = True
            self.on_ground = False

class Barrel:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_x = 2
        self.vel_y = 0
        self.sprite = Circle(x, y, BARREL_SIZE//2, fill=COLOR_BROWN)
        self.active = True
        
    def update(self, platforms):
        # Move barrel
        self.x += self.vel_x
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # Check platform collisions
        for platform in platforms:
            if (self.x > platform['x'] and 
                self.x < platform['x'] + platform['width'] and
                self.y + BARREL_SIZE//2 >= platform['y'] and
                self.y + BARREL_SIZE//2 <= platform['y'] + PLATFORM_HEIGHT + 5 and
                self.vel_y >= 0):
                self.y = platform['y'] - BARREL_SIZE//2
                self.vel_y = 0
                
        # Remove if off screen
        if self.x < -10 or self.x > WIDTH + 10 or self.y > HEIGHT + 10:
            self.active = False
            
        # Update sprite
        self.sprite.x = int(self.x)
        self.sprite.y = int(self.y)
        
    def collides_with(self, player):
        # Check collision between barrel and player sprite
        barrel_left = self.x - BARREL_SIZE//2
        barrel_right = self.x + BARREL_SIZE//2
        barrel_top = self.y - BARREL_SIZE//2
        barrel_bottom = self.y + BARREL_SIZE//2
        
        player_left = player.x
        player_right = player.x + MARIO_WIDTH
        player_top = player.y
        player_bottom = player.y + MARIO_HEIGHT
        
        return (barrel_right > player_left and
                barrel_left < player_right and
                barrel_bottom > player_top and
                barrel_top < player_bottom)

class DonkeyKong:
    def __init__(self, x, y, bitmap, palette):
        self.x = x
        self.y = y
        self.barrel_timer = 0
        
        # Create sprite or fallback to rectangle
        if bitmap is not None:
            try:
                # Check if bitmap dimensions match expected tile size
                if bitmap.width == DK_WIDTH and bitmap.height == DK_HEIGHT:
                    # Single sprite - no tiling needed
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette
                    )
                else:
                    # Try to create tiled sprite
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette,
                        width=1,
                        height=1,
                        tile_width=DK_WIDTH,
                        tile_height=DK_HEIGHT
                    )
            except ValueError as e:
                print(f"DK sprite error: {e}, using fallback")
                self.sprite = Rect(x, y, DK_WIDTH, DK_HEIGHT, fill=COLOR_BROWN)
        else:
            self.sprite = Rect(x, y, DK_WIDTH, DK_HEIGHT, fill=COLOR_BROWN)
        
        self.sprite.x = int(x)
        self.sprite.y = int(y)
        
    def update(self):
        self.barrel_timer += 1

class Princess:
    def __init__(self, x, y, bitmap, palette):
        self.x = x
        self.y = y
        
        # Create sprite or fallback to circle
        if bitmap is not None:
            try:
                # Check if bitmap dimensions match expected tile size
                if bitmap.width == PRINCESS_WIDTH and bitmap.height == PRINCESS_HEIGHT:
                    # Single sprite - no tiling needed
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette
                    )
                else:
                    # Try to create tiled sprite
                    self.sprite = displayio.TileGrid(
                        bitmap,
                        pixel_shader=palette,
                        width=1,
                        height=1,
                        tile_width=PRINCESS_WIDTH,
                        tile_height=PRINCESS_HEIGHT
                    )
            except ValueError as e:
                print(f"Princess sprite error: {e}, using fallback")
                self.sprite = Circle(x, y, PRINCESS_WIDTH//2, fill=COLOR_PINK)
        else:
            self.sprite = Circle(x, y, PRINCESS_WIDTH//2, fill=COLOR_PINK)
        
        self.sprite.x = int(x)
        self.sprite.y = int(y)

# Create main game group
game_group = displayio.Group()

# Create platforms (from bottom to top)
platforms = [
    {'x': 0, 'y': HEIGHT - 10, 'width': WIDTH, 'rect': None},
    {'x': 20, 'y': HEIGHT - 40, 'width': 180, 'rect': None},
    {'x': 40, 'y': HEIGHT - 70, 'width': 180, 'rect': None},
    {'x': 20, 'y': HEIGHT - 100, 'width': 180, 'rect': None},
    {'x': 40, 'y': 20, 'width': 160, 'rect': None},
]

# Create platform rectangles
for platform in platforms:
    platform['rect'] = Rect(
        platform['x'], 
        platform['y'], 
        platform['width'], 
        PLATFORM_HEIGHT, 
        fill=COLOR_BLUE
    )
    game_group.append(platform['rect'])

# Create game objects with bitmap sprites
player = Player(30, HEIGHT - MARIO_HEIGHT - 20, mario_bitmap, mario_palette if mario_bitmap else None)
donkey_kong = DonkeyKong(10, 10, dk_bitmap, dk_palette if dk_bitmap else None)
princess = Princess(WIDTH - PRINCESS_WIDTH - 20, 5, princess_bitmap, princess_palette if princess_bitmap else None)

# Add sprites to group
game_group.append(donkey_kong.sprite)
game_group.append(princess.sprite)
game_group.append(player.sprite)

# Barrel list
barrels = []

# Game state
score = 0
lives = 3
game_over = False
game_started = False  # Track if game has started

# Create and show splash screen
splash_group = displayio.Group()

if splash_bitmap is not None:
    try:
        # Create splash sprite centered on screen
        splash_sprite = displayio.TileGrid(
            splash_bitmap,
            pixel_shader=splash_palette
        )
        # Center the splash screen
        splash_sprite.x = (WIDTH - splash_bitmap.width) // 2
        splash_sprite.y = (HEIGHT - splash_bitmap.height) // 2
        splash_group.append(splash_sprite)
    except Exception as e:
        print(f"Error creating splash screen: {e}")

# Show splash screen
display.root_group = splash_group

print("=" * 40)
print("Donkey Kong - IMU Control Edition")
print("=" * 40)
print("Press D3 button to start!")
print("=" * 40)

# Animate NeoPixels while waiting
pixel_animation = 0
last_button_state = True

# Wait for button press to start game
while not game_started:
    current_button = button_jump.value
    
    # Check for button press (edge detection)
    if (last_button_state is True) and (current_button is False):
        game_started = True
        print("Game Starting!")
        # Flash pixels on start
        for i in range(2):
            pixels.fill(COLOR_GREEN)
            pixels.show()
            time.sleep(0.1)
            pixels.fill(COLOR_BLACK)
            pixels.show()
            time.sleep(0.1)
    
    last_button_state = current_button
    
    # Animate NeoPixels in a sweep pattern (skip pixel 0, use 1-4)
    pixel_animation = (pixel_animation + 1) % 40
    pixels[0] = COLOR_BLACK  # Always keep first pixel off
    if pixel_animation < 10:
        pixels[1] = COLOR_RED
        pixels[2] = COLOR_BLACK
        pixels[3] = COLOR_BLACK
        pixels[4] = COLOR_BLACK
    elif pixel_animation < 20:
        pixels[1] = COLOR_BLACK
        pixels[2] = COLOR_RED
        pixels[3] = COLOR_BLACK
        pixels[4] = COLOR_BLACK
    elif pixel_animation < 30:
        pixels[1] = COLOR_BLACK
        pixels[2] = COLOR_BLACK
        pixels[3] = COLOR_RED
        pixels[4] = COLOR_BLACK
    else:
        pixels[1] = COLOR_BLACK
        pixels[2] = COLOR_BLACK
        pixels[3] = COLOR_BLACK
        pixels[4] = COLOR_RED
    pixels.show()
    
    time.sleep(0.05)

# Game has started - switch to game screen
display.root_group = game_group

print("Controls:")
print("  Tilt board LEFT/RIGHT to move")
print("  D3 button to JUMP")
print("=" * 40)
print(f"Lives: {lives}")
print("=" * 40)

# Button state tracking for jump
last_jump = True

# Main game loop
frame_count = 0
while True:
    frame_count += 1
    
    if not game_over:
        # Read IMU acceleration
        try:
            accel_x, accel_y, accel_z = icm.acceleration
            
            if Debug:
                print(f"IMU X: {accel_x:.2f}, Y: {accel_y:.2f}, Z: {accel_z:.2f}")
            
            # Move player based on IMU tilt
            player.move_imu(accel_x)
            
            # Visual feedback on NeoPixels based on tilt (skip pixel 0, use 1-4)
            if accel_x < -IMU_DEADZONE:
                # Tilting left - show blue on left side
                pixels[0] = COLOR_BLACK  # Skip first pixel
                pixels[1] = COLOR_BLUE
                pixels[2] = COLOR_BLUE
                pixels[3] = COLOR_BLACK
                pixels[4] = COLOR_BLACK
            elif accel_x > IMU_DEADZONE:
                # Tilting right - show blue on right side
                pixels[0] = COLOR_BLACK  # Skip first pixel
                pixels[1] = COLOR_BLACK
                pixels[2] = COLOR_BLACK
                pixels[3] = COLOR_BLUE
                pixels[4] = COLOR_BLUE
            else:
                # Center - show green
                pixels[0] = COLOR_BLACK  # Skip first pixel
                pixels[1] = COLOR_BLACK
                pixels[2] = COLOR_GREEN
                pixels[3] = COLOR_BLACK
                pixels[4] = COLOR_BLACK
            pixels.show()
            
        except Exception as e:
            if Debug:
                print(f"IMU read error: {e}")
        
        # Handle jump button (D3)
        current_jump = button_jump.value
        if (last_jump is True) and (current_jump is False):
            player.jump()
            if Debug:
                print("Jump!")
        last_jump = current_jump
        
        # Update player
        player.update(platforms)
        
        # Spawn barrels from Donkey Kong
        donkey_kong.update()
        if donkey_kong.barrel_timer > 60:  # Every ~3 seconds
            new_barrel = Barrel(donkey_kong.x + DK_WIDTH//2, donkey_kong.y + DK_HEIGHT)
            barrels.append(new_barrel)
            game_group.append(new_barrel.sprite)
            donkey_kong.barrel_timer = 0
        
        # Update barrels
        for barrel in barrels[:]:
            barrel.update(platforms)
            
            # Check collision with player
            if barrel.collides_with(player):
                lives -= 1
                print(f"Hit! Lives remaining: {lives}")
                barrel.active = False
                # Flash red on hit
                pixels.fill(COLOR_RED)
                pixels.show()
                time.sleep(0.2)
                
                if lives <= 0:
                    game_over = True
                    print("=" * 40)
                    print("GAME OVER!")
                    print(f"Final Score: {score}")
                    print("=" * 40)
            
            # Remove inactive barrels
            if not barrel.active:
                try:
                    game_group.remove(barrel.sprite)
                except ValueError:
                    pass
                barrels.remove(barrel)
        
        # Check if player reached princess
        player_center_x = player.x + MARIO_WIDTH // 2
        player_center_y = player.y + MARIO_HEIGHT // 2
        princess_center_x = princess.x + PRINCESS_WIDTH // 2
        princess_center_y = princess.y + PRINCESS_HEIGHT // 2
        
        dist_to_princess = ((player_center_x - princess_center_x)**2 + 
                           (player_center_y - princess_center_y)**2)**0.5
        if dist_to_princess < 20:
            score += 100
            print("=" * 40)
            print(f"Level Complete! Score: {score}")
            print("=" * 40)
            
            # Victory flash
            for i in range(3):
                pixels.fill(COLOR_YELLOW)
                pixels.show()
                time.sleep(0.1)
                pixels.fill(COLOR_GREEN)
                pixels.show()
                time.sleep(0.1)
            
            # Reset player position
            player.x = 30
            player.y = HEIGHT - MARIO_HEIGHT - 20
            player.vel_y = 0
            
            # Clear barrels
            for barrel in barrels[:]:
                try:
                    game_group.remove(barrel.sprite)
                except ValueError:
                    pass
            barrels.clear()
            
    else:
        # Game over - flash pixels
        if (frame_count // 10) % 2 == 0:
            pixels.fill(COLOR_RED)
        else:
            pixels.fill(COLOR_YELLOW)
        pixels.show()
    
    time.sleep(0.02)  # ~50 FPS