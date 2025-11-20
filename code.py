"""
CircuitPython Super Mario Bros - Enhanced IMU Edition with Sprites
Complete game with IMU controls, calibration, scrolling levels, and real sprites!

Features:
- Auto-calibration for IMU
- Scrolling camera
- Multiple enemies and platforms
- Coin collection
- NeoPixel feedback
- Better tilt sensitivity tuning
- Real sprite graphics!
- MEMORY LEAK FIXES: Proper audio cleanup and aggressive garbage collection
"""

import time
import board
import adafruit_icm20x
import displayio
import adafruit_imageload
import digitalio
import microcontroller
import neopixel
import touchio
import gc
import terminalio
from fourwire import FourWire
from adafruit_st7789 import ST7789
from adafruit_display_text import label

# Audio imports
try:
    import audiocore
    import audioio
    AUDIO_AVAILABLE = True
except ImportError:
    print("⚠ Audio libraries not available")
    AUDIO_AVAILABLE = False

# Display configuration
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 135

# Game constants
GRAVITY = 0.6
JUMP_STRENGTH = -10
MOVE_SPEED = 2.5
RUN_SPEED = 4.5
GROUND_Y = 105

# IMU configuration
TILT_DEADZONE = 0.8   # Minimum tilt to register (reduces drift)
TILT_MAX = 6.0        # Maximum tilt for max speed
CALIBRATION_SAMPLES = 30  # Number of samples for calibration

# Sprite sizes
MARIO_WIDTH = 16
MARIO_HEIGHT = 16
ENEMY_WIDTH = 16
ENEMY_HEIGHT = 16
BLOCK_SIZE = 16

Debug = True

class AudioManager:
    """Manage audio playback for sound effects and music - MEMORY OPTIMIZED"""
    def __init__(self):
        self.audio_enabled = False
        self.audio = None
        self.sounds = {}
        self.current_file = None
        self.current_wave = None  # Track wave object for cleanup
        self.last_play_time = 0  # Rate limiting
        self.play_count = 0  # Track number of sounds played
        
        if not AUDIO_AVAILABLE:
            print("✗ Audio not available (missing libraries)")
            return
            
        try:
            # Initialize DAC audio output
            self.audio = audioio.AudioOut(board.DAC)
            print("✓ Audio initialized on DAC pin")
            self.audio_enabled = True
            
            # Load sound files
            self.load_sounds()
            
        except Exception as e:
            print(f"✗ Audio initialization failed: {e}")
            self.audio_enabled = False
    
    def load_sounds(self):
        """Load WAV files from /AudioFiles/ directory"""
        sound_files = {
            'jump': '/AudioFiles/smb_jump.wav',
            'coin': '/AudioFiles/smb_coin.wav',
            'gameover': '/AudioFiles/smb_gameover.wav',
            'world_clear': '/AudioFiles/smb_world_clear.wav',
            #'stomp': '/AudioFiles/smb_stomp.wav',
            #'death': '/AudioFiles/smb_death.wav',
        }
        
        print("Loading sound effects...")
        for sound_name, filepath in sound_files.items():
            try:
                # Verify file exists
                with open(filepath, "rb") as f:
                    pass
                self.sounds[sound_name] = filepath
                print(f"  ✓ {sound_name}: {filepath}")
            except Exception as e:
                print(f"  ✗ {sound_name}: {e}")
        
        if self.sounds:
            print(f"✓ {len(self.sounds)} sound effects ready")
        else:
            print("✗ No sound files found")
            self.audio_enabled = False
    
    def cleanup_audio_resources(self):
        """CRITICAL: Properly cleanup audio resources - FAST VERSION"""
        try:
            # Stop audio playback
            if self.audio and self.audio.playing:
                self.audio.stop()
            
            # Close file handle FIRST
            if self.current_file is not None:
                try:
                    self.current_file.close()
                except:
                    pass
                self.current_file = None
            
            # Delete wave object
            if self.current_wave is not None:
                del self.current_wave
                self.current_wave = None
            
            # NO GC HERE - let main loop handle it!
            
        except Exception as e:
            if Debug:
                print(f"Cleanup error: {e}")
            # Even on error, force cleanup
            self.current_file = None
            self.current_wave = None
    
    def play(self, sound_name):
        """Play a sound effect - FAST VERSION, NO BLOCKING"""
        if not self.audio_enabled:
            return
            
        if sound_name not in self.sounds:
            if Debug:
                print(f"Sound '{sound_name}' not available")
            return
        
        # Rate limiting - 100ms minimum between sounds
        current_time = time.monotonic()
        if current_time - self.last_play_time < 0.1:
            return
        
        try:
            # Clean up previous resources (fast, no GC)
            self.cleanup_audio_resources()
            
            # Recreate audio device every 50 sounds
            self.play_count += 1
            if self.play_count % 50 == 0:
                try:
                    self.audio.deinit()
                    self.audio = audioio.AudioOut(board.DAC)
                except Exception as e:
                    print(f"Audio reinit error: {e}")
            
            # Open and play immediately
            filepath = self.sounds[sound_name]
            self.current_file = open(filepath, "rb")
            self.current_wave = audiocore.WaveFile(self.current_file)
            self.audio.play(self.current_wave)
            self.last_play_time = current_time
            
            if Debug:
                print(f"♪ {sound_name}")
                
        except Exception as e:
            print(f"Audio error ({sound_name}): {e}")
            self.cleanup_audio_resources()
    
    def stop(self):
        """Stop current audio playback"""
        if self.audio_enabled and self.audio:
            self.cleanup_audio_resources()
            # NO GC - let main loop handle it
    
    def is_playing(self):
        """Check if audio is currently playing"""
        if self.audio_enabled and self.audio:
            try:
                return self.audio.playing
            except:
                return False
        return False

class SpriteLoader:
    """Load and manage sprite sheets"""
    def __init__(self):
        self.sprites_loaded = False
        self.mario_sheet = None
        self.mario_palette = None
        self.goomba_sheet = None
        self.goomba_palette = None
        self.block_sheet = None
        self.block_palette = None
        self.coin_sheet = None
        self.coin_palette = None
        
        self.load_sprites()
        
    def load_sprites(self):
        """Load all sprite sheets from /Sprites/ directory"""
        try:
            print("Loading sprite sheets...")
            
            # Load Mario sprites (48x16, 3 frames of 16x16)
            self.mario_sheet, self.mario_palette = adafruit_imageload.load(
                "/Sprites/mario_sprites.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            print("✓ Mario sprites loaded")
            
            # Load Goomba sprites (32x16, 2 frames of 16x16)
            self.goomba_sheet, self.goomba_palette = adafruit_imageload.load(
                "/Sprites/goomba_sprites.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            print("✓ Goomba sprites loaded")
            
            # Load block sprites (48x16, 3 types of 16x16)
            self.block_sheet, self.block_palette = adafruit_imageload.load(
                "/Sprites/block_sprites.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            print("✓ Block sprites loaded")
            
            # Load coin sprite (8x14)
            self.coin_sheet, self.coin_palette = adafruit_imageload.load(
                "/Sprites/coin_sprite.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            print("✓ Coin sprite loaded")
            
            self.sprites_loaded = True
            print("✓ All sprites loaded successfully!\n")
            
        except Exception as e:
            print(f"✗ Could not load sprites: {e}")
            print("Will use colored rectangles instead.\n")
            self.sprites_loaded = False

class Camera:
    """Camera system for side-scrolling"""
    def __init__(self):
        self.x = 0
        self.target_x = 0
        self.smoothing = 0.2
        
    def update(self, mario_x):
        """Follow Mario smoothly"""
        self.target_x = mario_x - DISPLAY_WIDTH // 3
        self.target_x = max(0, min(self.target_x, 2200 - DISPLAY_WIDTH))
        self.x += (self.target_x - self.x) * self.smoothing

class Platform:
    """Static platform"""
    def __init__(self, x, y, width, height, block_type="brick"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.block_type = block_type

class Coin:
    """Collectible coin"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False

class Enemy:
    """Goomba enemy"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = ENEMY_WIDTH
        self.height = ENEMY_HEIGHT
        self.vel_x = -1.0
        self.vel_y = 0
        self.alive = True
        self.on_ground = False
        self.sprite_frame = 0
        self.frame_counter = 0
        
    def update(self, platforms):
        """Update enemy movement - OPTIMIZED for performance"""
        if not self.alive:
            return False
            
        self.x += self.vel_x
        self.vel_y += GRAVITY
        self.y += self.vel_y
        
        # OPTIMIZATION: Only check platforms within reasonable range
        # Enemies move slowly so we only need to check nearby platforms
        nearby_range = 100  # Check platforms within 100 pixels
        
        self.on_ground = False
        for platform in platforms:
            # CRITICAL: Skip platforms that are far away
            if abs(platform.x - self.x) > nearby_range:
                continue
                
            if (self.x + self.width > platform.x and 
                self.x < platform.x + platform.width and
                self.vel_y >= 0 and
                self.y + self.height >= platform.y and
                self.y + self.height <= platform.y + platform.height + 5):
                self.y = platform.y - self.height
                self.vel_y = 0
                self.on_ground = True
                break  # Found ground, no need to check more
                
        # Check for wall collisions (only nearby platforms)
        for platform in platforms:
            if abs(platform.x - self.x) > nearby_range:
                continue
                
            if (self.x + self.width > platform.x and 
                self.x < platform.x + platform.width):
                if self.y + self.height > platform.y + platform.height:
                    if self.vel_x > 0:
                        self.x = platform.x - self.width
                    else:
                        self.x = platform.x + platform.width
                    self.vel_x *= -1
                    break  # Hit wall, no need to check more
        
        self.frame_counter += 1
        if self.frame_counter >= 15:
            self.sprite_frame = 1 - self.sprite_frame
            self.frame_counter = 0
        
        if self.y > DISPLAY_HEIGHT + 50:
            return True
            
        return False
        
    def stomp(self):
        """Enemy stomped"""
        self.alive = False

def check_collision(x1, y1, w1, h1, x2, y2, w2, h2):
    """AABB collision detection"""
    return (x1 < x2 + w2 and x1 + w1 > x2 and
            y1 < y2 + h2 and y1 + h1 > y2)

class Level:
    """Game level with platforms, enemies, and coins"""
    def __init__(self):
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.create_level()
        
    def create_level(self):
        """Create a simple but fun level"""
        for i in range(0, 2200, BLOCK_SIZE):
            self.platforms.append(Platform(i, GROUND_Y + 15, BLOCK_SIZE, BLOCK_SIZE))
        
        for x in [200, 250, 300]:
            self.platforms.append(Platform(x, 70, BLOCK_SIZE, BLOCK_SIZE, "question"))
            
        for x in range(400, 550, BLOCK_SIZE):
            self.platforms.append(Platform(x, 80, BLOCK_SIZE, BLOCK_SIZE, "brick"))
            
        for x in range(700, 800, BLOCK_SIZE):
            self.platforms.append(Platform(x, 60, BLOCK_SIZE, BLOCK_SIZE))
            
        self.platforms.append(Platform(900, 90, BLOCK_SIZE, BLOCK_SIZE*3, "pipe"))
        
        for x in range(1100, 1250, BLOCK_SIZE):
            self.platforms.append(Platform(x, 70, BLOCK_SIZE, BLOCK_SIZE))
            
        for x in range(1400, 1550, BLOCK_SIZE):
            y_offset = ((x - 1400) // BLOCK_SIZE) * BLOCK_SIZE
            self.platforms.append(Platform(x, GROUND_Y - y_offset, BLOCK_SIZE, BLOCK_SIZE))
            
        for x in range(1700, 1900, BLOCK_SIZE):
            self.platforms.append(Platform(x, 50, BLOCK_SIZE, BLOCK_SIZE, "brick"))
            
        self.platforms.append(Platform(2050, 70, BLOCK_SIZE, BLOCK_SIZE*2, "pipe"))
        
        for x in [150, 350, 600, 950, 1200, 1500, 1800]:
            self.enemies.append(Enemy(x, GROUND_Y))
            
        # Coins - positioned to be accessible (not embedded in platforms)
        for x in [225, 275, 475, 525]:
            self.coins.append(Coin(x, 50))
        # These coins were embedded in platforms, moved up to be accessible
        self.coins.append(Coin(750, 30))   # Was y=50, overlapped with platform at y=60
        self.coins.append(Coin(1175, 50))  # This one was fine
        self.coins.append(Coin(1450, 30))  # Was y=50, overlapped with staircase at y=57
        self.coins.append(Coin(1750, 30))  # Was y=50, overlapped with brick at y=50

class Mario:
    """Mario with enhanced IMU physics and sprite animation - ORIGINAL CODE"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.width = MARIO_WIDTH
        self.height = MARIO_HEIGHT
        self.is_running = False
        self.invincible = 0  # Invincibility frames
        self.sprite_frame = 0  # 0=stand, 1=walk, 2=jump
        self.anim_counter = 0  # Animation timing
        self.jump_triggered = False  # Track when jump starts (for NeoPixel)
        
    def update(self, imu_control, platforms):
        """Update with IMU control and platform collision - OPTIMIZED"""
        prev_y = self.y
        
        # Decrement invincibility
        if self.invincible > 0:
            self.invincible -= 1
        
        # Movement with variable speed based on tilt amount
        if imu_control.tilt_value != 0:
            move_speed = RUN_SPEED if imu_control.run else MOVE_SPEED
            # Use tilt value to control speed smoothly
            self.vel_x = imu_control.tilt_value * move_speed
            self.facing_right = imu_control.tilt_value > 0
            
            # Walking animation
            if self.on_ground:
                self.anim_counter += 1
                if self.anim_counter > 5:
                    self.sprite_frame = 1 if self.sprite_frame == 0 else 0
                    self.anim_counter = 0
        else:
            # Deceleration
            self.vel_x *= 0.8
            if abs(self.vel_x) < 0.1:
                self.vel_x = 0
            self.sprite_frame = 0  # Standing
                
        # Jumping
        if imu_control.jump and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.jump_triggered = True  # NeoPixel indicator
            self.on_ground = False
            
        # Set jump sprite when in air
        if not self.on_ground:
            self.sprite_frame = 2
            
        # Gravity
        if not self.on_ground:
            self.vel_y += GRAVITY
            if self.vel_y > 10:
                self.vel_y = 10
                
        # Update position
        self.x += self.vel_x
        self.y += self.vel_y
        
        # OPTIMIZED: Platform collision - only check nearby platforms
        self.on_ground = False
        nearby_range = 150  # Check platforms within 150 pixels (Mario moves faster than enemies)
        
        for platform in platforms:
            # CRITICAL: Skip platforms that are too far away
            if abs(platform.x - self.x) > nearby_range and abs(platform.y - self.y) > nearby_range:
                continue
                
            if self.check_platform_collision(platform, prev_y):
                break
                
        # Ground collision
        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            self.jump_triggered = False  # Turn off NeoPixel when landing
            
    def check_platform_collision(self, platform, prev_y):
        """Check collision with platform"""
        if (self.x + self.width > platform.x and
            self.x < platform.x + platform.width and
            self.y + self.height > platform.y and
            self.y < platform.y + platform.height):
            
            # Landing on top
            if prev_y + self.height <= platform.y and self.vel_y > 0:
                self.y = platform.y - self.height
                self.vel_y = 0
                self.on_ground = True
                self.jump_triggered = False  # Turn off NeoPixel when landing on platform
                return True
                
            # Hitting from below
            elif prev_y >= platform.y + platform.height and self.vel_y < 0:
                self.y = platform.y + platform.height
                self.vel_y = 0
                return True
                
        return False

class IMUController:
    """Enhanced IMU controller with calibration - ORIGINAL CODE"""
    def __init__(self):
        print("Initializing IMU...")
        
        # Setup I2C and IMU
        i2c = board.I2C()
        
        try:
            self.icm = adafruit_icm20x.ICM20948(i2c, 0x69)
            print("✓ ICM20948 found at 0x69")
        except:
            try:
                self.icm = adafruit_icm20x.ICM20948(i2c, 0x68)
                print("✓ ICM20948 found at 0x68")
            except Exception as e:
                print(f"✗ IMU initialization failed: {e}")
                raise
        
        # Calibration offsets (will be set during calibration)
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_z = 0.0
        
        # Setup jump button (D3, active LOW)
        self.btn_jump = digitalio.DigitalInOut(board.D3)
        self.btn_jump.direction = digitalio.Direction.INPUT
        self.btn_jump.pull = digitalio.Pull.UP
        self.prev_jump = True
        self.jump_buffer = False  # NEW: Buffer to catch quick presses
        self.jump_buffer_frames = 0  # NEW: How long to keep buffered jump
        
        # Setup capacitive touch for run
        try:
            self.touch_run = touchio.TouchIn(board.CAP1)
            self.touch_available = True
            print("✓ Capacitive touch initialized")
        except Exception as e:
            print(f"✗ Touch not available: {e}")
            self.touch_available = False
            
        # Control state
        self.left = False
        self.right = False
        self.jump = False
        self.run = False
        self.tilt_value = 0.0
        
        # Calibrate on startup
        self.calibrate()
        
    def calibrate(self):
        """Calibrate IMU by averaging readings when level"""
        print("\nCalibrating IMU...")
        print("Place board on level surface...")
        time.sleep(1)
        
        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0
        
        for i in range(CALIBRATION_SAMPLES):
            x, y, z = self.icm.acceleration
            sum_x += x
            sum_y += y
            sum_z += z
            time.sleep(0.05)
            
        self.offset_x = sum_x / CALIBRATION_SAMPLES
        self.offset_y = sum_y / CALIBRATION_SAMPLES
        self.offset_z = sum_z / CALIBRATION_SAMPLES
        
        print(f"✓ Calibration complete!")
        print(f"  Offsets: X={self.offset_x:.2f}, Y={self.offset_y:.2f}, Z={self.offset_z:.2f}")
        
    def update(self):
        """Read IMU and button states - WITH BUTTON BUFFERING"""
        # Read accelerometer with calibration
        accel_x, accel_y, accel_z = self.icm.acceleration
        
        # Apply calibration
        adjusted_x = accel_x - self.offset_x
        
        # Apply deadzone
        if abs(adjusted_x) < TILT_DEADZONE:
            self.tilt_value = 0.0
            self.left = False
            self.right = False
        else:
            # Remove deadzone offset and normalize
            if adjusted_x > 0:
                self.tilt_value = min(1.0, (adjusted_x - TILT_DEADZONE) / TILT_MAX)
                self.right = True
                self.left = False
            else:
                self.tilt_value = max(-1.0, (adjusted_x + TILT_DEADZONE) / TILT_MAX)
                self.left = True
                self.right = False
        
        # IMPROVED: Read jump button with buffering to catch quick presses
        current_jump = not self.btn_jump.value
        
        # Detect button press (rising edge)
        if current_jump and not self.prev_jump:
            self.jump_buffer = True
            self.jump_buffer_frames = 3  # Keep buffered for 3 frames (~100ms)
        
        self.prev_jump = current_jump
        
        # Set jump flag if buffer is active
        if self.jump_buffer:
            self.jump = True
            self.jump_buffer_frames -= 1
            # Clear buffer after it expires
            if self.jump_buffer_frames <= 0:
                self.jump_buffer = False
                self.jump = False
        else:
            self.jump = False
        
        # Read capacitive touch
        if self.touch_available:
            self.run = self.touch_run.value
        else:
            self.run = False
    
    def poll_button_only(self):
        """Quick poll of just the button - call this frequently to catch fast presses"""
        current_jump = not self.btn_jump.value
        
        # Detect button press and buffer it
        if current_jump and not self.prev_jump:
            self.jump_buffer = True
            self.jump_buffer_frames = 3
        
        self.prev_jump = current_jump

class NeoPixelFeedback:
    """NeoPixel game feedback - ORIGINAL CODE"""
    def __init__(self):
        try:
            self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 5, brightness=0.15, auto_write=False)
            self.pixels.fill(0x000000)
            self.pixels.show()
            self.available = True
        except:
            self.available = False
            
    def update(self, mario, score, lives, level_complete=False):
        """Update based on game state"""
        if not self.available:
            return
        
        # Victory pattern - all gold!
        if level_complete:
            self.pixels.fill(0xFFD700)  # Gold color for victory!
            self.pixels.show()
            return
            
        # Pixel 0-2: Lives (green to red)
        for i in range(min(lives, 3)):
            self.pixels[i] = 0x00FF00
        for i in range(lives, 3):
            self.pixels[i] = 0x000000
            
        # Pixel 3: Jump indicator
        self.pixels[3] = 0x0000FF if mario.jump_triggered else 0x000000
        
        # Pixel 4: Run indicator
        self.pixels[4] = 0xFFFF00 if mario.is_running else 0x000000
        
        self.pixels.show()

class HUD:
    """Heads-Up Display for score, coins, and lives - ORIGINAL CODE"""
    def __init__(self, parent_group):
        self.hud_group = displayio.Group()
        parent_group.append(self.hud_group)
        
        # Score label (top left)
        self.score_label = label.Label(
            terminalio.FONT,
            text="SCORE: 0",
            color=0xFFFFFF,
            x=5,
            y=8
        )
        self.hud_group.append(self.score_label)
        
        # Lives label (top center)
        self.lives_label = label.Label(
            terminalio.FONT,
            text="LIVES: 3",
            color=0xFFFFFF,
            x=95,
            y=8
        )
        self.hud_group.append(self.lives_label)
        
        # Coins label (top right)
        self.coins_label = label.Label(
            terminalio.FONT,
            text="COINS: 0",
            color=0xFFFFFF,
            x=175,
            y=8
        )
        self.hud_group.append(self.coins_label)
        
        # MEMORY: Track last values to avoid unnecessary string creation
        self.last_score = 0
        self.last_coins = 0
        self.last_lives = 3
        
        print("✓ HUD created")
    
    def update(self, score, coins, lives):
        """Update HUD text - ONLY when values change (MEMORY OPTIMIZED)"""
        # Only update if values actually changed - prevents creating new strings every frame!
        if score != self.last_score:
            self.score_label.text = f"SCORE:{score}"
            self.last_score = score
        
        if coins != self.last_coins:
            self.coins_label.text = f"COINS:{coins}"
            self.last_coins = coins
        
        if lives != self.last_lives:
            self.lives_label.text = f"LIVES:{lives}"
            self.last_lives = lives
    
    def hide(self):
        """Hide HUD during victory screen"""
        self.hud_group.hidden = True
    
    def show(self):
        """Show HUD during gameplay"""
        self.hud_group.hidden = False

class VictoryScreen:
    """Victory screen showing final score - ORIGINAL CODE"""
    def __init__(self, parent_group):
        self.victory_group = displayio.Group()
        parent_group.append(self.victory_group)
        
        # Semi-transparent background (using a colored bitmap)
        bg = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
        bg_palette = displayio.Palette(1)
        bg_palette[0] = 0x000000  # Black background
        bg_tile = displayio.TileGrid(bg, pixel_shader=bg_palette)
        self.victory_group.append(bg_tile)
        
        # "LEVEL COMPLETE!" text
        self.title_label = label.Label(
            terminalio.FONT,
            text="LEVEL COMPLETE!",
            color=0xFFD700,  # Gold
            scale=2,
            x=30,
            y=40
        )
        self.victory_group.append(self.title_label)
        
        # Score text
        self.score_label = label.Label(
            terminalio.FONT,
            text="SCORE: 0",
            color=0xFFFFFF,
            scale=2,
            x=50,
            y=70
        )
        self.victory_group.append(self.score_label)
        
        # Coins text
        self.coins_label = label.Label(
            terminalio.FONT,
            text="COINS: 0",
            color=0xFFFFFF,
            scale=2,
            x=50,
            y=95
        )
        self.victory_group.append(self.coins_label)
        
        # Hide by default
        self.victory_group.hidden = True
        
        print("✓ Victory screen created")
    
    def show(self, score, coins):
        """Show victory screen with final stats"""
        self.score_label.text = f"SCORE: {score}"
        self.coins_label.text = f"COINS: {coins}"
        self.victory_group.hidden = False
    
    def hide(self):
        """Hide victory screen"""
        self.victory_group.hidden = True


class GameOverScreen:
    """Game Over screen with Game_Over.BMP image"""
    def __init__(self, parent_group):
        self.gameover_group = displayio.Group()
        parent_group.append(self.gameover_group)
        
        # Try to load Game_Over.BMP
        self.image_loaded = False
        try:
            gameover_bitmap, gameover_palette = adafruit_imageload.load(
                "/Sprites/Game_Over.BMP",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            
            # Create TileGrid to display the image
            gameover_tilegrid = displayio.TileGrid(
                gameover_bitmap,
                pixel_shader=gameover_palette,
                x=0,
                y=0
            )
            self.gameover_group.append(gameover_tilegrid)
            self.image_loaded = True
            print("✓ Game Over screen image loaded")
            
        except Exception as e:
            print(f"✗ Could not load Game_Over.BMP: {e}")
            print("Creating text-based game over screen instead")
            
            # Fallback: Create text-based game over screen
            bg = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = 0x000000  # Black background
            bg_tile = displayio.TileGrid(bg, pixel_shader=bg_palette)
            self.gameover_group.append(bg_tile)
            
            # "GAME OVER" text
            title_label = label.Label(
                terminalio.FONT,
                text="GAME OVER",
                color=0xFF0000,  # Red
                scale=3,
                x=40,
                y=DISPLAY_HEIGHT // 2
            )
            self.gameover_group.append(title_label)
        
        # Hide by default
        self.gameover_group.hidden = True
    
    def show(self):
        """Show game over screen"""
        self.gameover_group.hidden = False
    
    def hide(self):
        """Hide game over screen"""
        self.gameover_group.hidden = True

class MarioGame:
    """Main game class"""
    
    # Class-level constants to avoid recreation
    TILE_MAP = {"brick": 0, "question": 1, "pipe": 2}
    
    def __init__(self):
        # MEMORY: Force garbage collection at start
        gc.collect()
        print(f"Initial free memory: {gc.mem_free()} bytes")
        
        # Initialize display (ORIGINAL DISPLAY SETUP CODE)
        self.setup_display()
        
        # Load sprites
        self.sprite_loader = SpriteLoader()
        
        # Initialize audio (with memory leak fixes)
        self.audio_manager = AudioManager()
        
        # Create sprite pools
        self.setup_sprite_pools()
        
        # Initialize game state
        self.level = Level()
        self.mario = Mario(40, GROUND_Y)
        self.camera = Camera()
        self.imu_control = IMUController()
        self.neopixels = NeoPixelFeedback()
        
        # Game variables
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.game_over = False
        self.level_complete = False
        self.victory_timer = 0
        
    def setup_display(self):
        """Setup display - ORIGINAL CODE"""
        print("Setting up display...")
        
        backlight = digitalio.DigitalInOut(microcontroller.pin.PA06)
        backlight.direction = digitalio.Direction.OUTPUT
        backlight.value = False
        
        displayio.release_displays()
        
        spi = board.LCD_SPI()
        display_bus = FourWire(spi, command=board.D4, chip_select=board.LCD_CS)
        self.display = ST7789(
            display_bus, rotation=90, width=DISPLAY_WIDTH, 
            height=DISPLAY_HEIGHT, rowstart=40, colstart=53
        )
        
        self.main_group = displayio.Group()
        self.display.root_group = self.main_group
        self.create_background()
        print("✓ Display ready")
        
    def create_background(self):
        """Create static background (never redrawn - prevents stuttering)"""
        # Sky - STATIC LAYER
        sky = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
        pal = displayio.Palette(1)
        pal[0] = 0x5C94FC
        self.main_group.append(displayio.TileGrid(sky, pixel_shader=pal, x=0, y=0))
        
        # Ground - STATIC LAYER
        ground = displayio.Bitmap(DISPLAY_WIDTH, 30, 1)
        gpal = displayio.Palette(1)
        gpal[0] = 0x00AA00
        self.main_group.append(displayio.TileGrid(ground, pixel_shader=gpal, x=0, y=GROUND_Y))
        print("✓ Static background created")
        
    def create_sprite(self, w, h, color):
        """Create sprite for fallback when sprite files aren't loaded"""
        bmp = displayio.Bitmap(w, h, 1)
        pal = displayio.Palette(1)
        pal[0] = color
        return displayio.TileGrid(bmp, pixel_shader=pal)
        
    def setup_sprite_pools(self):
        """Create reusable sprite pools - UPDATED from original"""
        self.sprite_group = displayio.Group()
        self.main_group.append(self.sprite_group)
        
        # Create sprite pools
        self.platform_sprites = []
        self.enemy_sprites = []
        self.coin_sprites = []
        
        # Platform pool (increased to 75 to handle densest sections)
        for i in range(75):
            if self.sprite_loader.sprites_loaded:
                sprite = displayio.TileGrid(
                    self.sprite_loader.block_sheet,
                    pixel_shader=self.sprite_loader.block_palette,
                    width=1, height=1,
                    tile_width=BLOCK_SIZE, tile_height=BLOCK_SIZE,
                    x=0, y=0
                )
            else:
                sprite = self.create_sprite(BLOCK_SIZE, BLOCK_SIZE, 0xD87850)
            sprite.hidden = True
            self.platform_sprites.append(sprite)
            self.sprite_group.append(sprite)
        
        # Enemy pool (10 enemies)
        for i in range(10):
            if self.sprite_loader.sprites_loaded:
                sprite = displayio.TileGrid(
                    self.sprite_loader.goomba_sheet,
                    pixel_shader=self.sprite_loader.goomba_palette,
                    width=1, height=1,
                    tile_width=ENEMY_WIDTH, tile_height=ENEMY_HEIGHT,
                    x=0, y=0
                )
            else:
                sprite = self.create_sprite(ENEMY_WIDTH, ENEMY_HEIGHT, 0x8B4513)
            sprite.hidden = True
            self.enemy_sprites.append(sprite)
            self.sprite_group.append(sprite)
            
        # Coin pool (20 coins)
        for i in range(20):
            if self.sprite_loader.sprites_loaded:
                sprite = displayio.TileGrid(
                    self.sprite_loader.coin_sheet,
                    pixel_shader=self.sprite_loader.coin_palette,
                    width=1, height=1,
                    tile_width=8, tile_height=14,
                    x=0, y=0
                )
            else:
                sprite = self.create_sprite(8, 14, 0xFCBC00)
            sprite.hidden = True
            self.coin_sprites.append(sprite)
            self.sprite_group.append(sprite)
            
        # Mario sprite (always visible)
        if self.sprite_loader.sprites_loaded:
            self.mario_sprite = displayio.TileGrid(
                self.sprite_loader.mario_sheet,
                pixel_shader=self.sprite_loader.mario_palette,
                width=1, height=1,
                tile_width=MARIO_WIDTH, tile_height=MARIO_HEIGHT,
                x=40, y=GROUND_Y
            )
        else:
            self.mario_sprite = self.create_sprite(MARIO_WIDTH, MARIO_HEIGHT, 0xFF0000)
        self.sprite_group.append(self.mario_sprite)
        
        # OPTIMIZATION: Track last sprite state to avoid unnecessary updates
        self.last_mario_frame = -1
        self.last_mario_flip = None
        
        print(f"✓ Sprite pools created: {len(self.platform_sprites)} platforms, {len(self.enemy_sprites)} enemies, {len(self.coin_sprites)} coins")
        
        # Create HUD and Victory Screen (on top of everything)
        self.hud = HUD(self.main_group)
        self.victory_screen = VictoryScreen(self.main_group)
        self.game_over_screen = GameOverScreen(self.main_group)
            
    def update(self):
        """Update game state"""
        if self.game_over:
            return
        
        # Victory timer countdown (allow this even during victory screen)
        if self.level_complete and self.victory_timer > 0:
            self.victory_timer -= 1
            if self.victory_timer == 0:
                # Reset level after victory screen
                self.reset_level()
            return  # Don't update game during victory screen
            
        # CRITICAL: Poll button at START of frame to catch quick presses
        self.imu_control.poll_button_only()
        
        # Controls - UPDATE IMU (includes another button poll)
        self.imu_control.update()
        self.mario.is_running = self.imu_control.run
        
        # Check for jump (before updating Mario)
        mario_was_on_ground = self.mario.on_ground
        
        # Mario
        self.mario.update(self.imu_control, self.level.platforms)
        
        # Play jump sound if Mario just jumped
        if mario_was_on_ground and not self.mario.on_ground and self.mario.vel_y < 0:
            self.audio_manager.play('jump')
        
        # Camera
        self.camera.update(self.mario.x)
        
        # Enemies
        for enemy in self.level.enemies[:]:
            if enemy.update(self.level.platforms):
                self.level.enemies.remove(enemy)
                continue
                
            if enemy.alive and self.mario.invincible == 0:
                if check_collision(
                    self.mario.x, self.mario.y, self.mario.width, self.mario.height,
                    enemy.x, enemy.y, enemy.width, enemy.height
                ):
                    if self.mario.vel_y > 0 and self.mario.y < enemy.y:
                        enemy.stomp()
                        self.score += 100
                        self.mario.vel_y = -6
                        # self.audio_manager.play('stomp')  # Add smb_stomp.wav to enable
                    else:
                        self.lives -= 1
                        self.mario.invincible = 120
                        # self.audio_manager.play('death')  # Add smb_death.wav to enable
                        if self.lives <= 0:
                            self.game_over = True
                            self.audio_manager.play('gameover')  # Game over sound!
                            self.game_over_screen.show()
                            self.hud.hide()
                            
        # Coins
        for coin in self.level.coins:
            if not coin.collected:
                if check_collision(
                    self.mario.x, self.mario.y, self.mario.width, self.mario.height,
                    coin.x, coin.y, 8, 14
                ):
                    coin.collected = True
                    self.coins += 1
                    self.score += 200
                    self.audio_manager.play('coin')  # Coin sound!
                    
        # Level completion check - must reach the actual end (past flag pole at x=2050)
        if not self.level_complete and self.mario.x >= 2075:
            self.level_complete = True
            self.victory_timer = 180  # Display victory screen for 180 frames (6 seconds at 30 FPS)
            self.audio_manager.play('world_clear')  # Victory sound!
            
            # Show victory screen, hide HUD
            self.victory_screen.show(self.score, self.coins)
            self.hud.hide()
            
            print(f"\n🎉 LEVEL COMPLETE! 🎉")
            print(f"Final Score: {self.score}")
            print(f"Coins Collected: {self.coins}")
                    
        # Fall death
        if self.mario.y > DISPLAY_HEIGHT:
            self.lives -= 1
            # self.audio_manager.play('death')  # Add smb_death.wav to enable
            if self.lives <= 0:
                self.game_over = True
                self.audio_manager.play('gameover')  # Game over sound!
                self.game_over_screen.show()
                self.hud.hide()
            else:
                self.mario.x = 40
                self.mario.y = GROUND_Y
                self.mario.invincible = 120
                
        # Update NeoPixels
        self.neopixels.update(self.mario, self.score, self.lives, self.level_complete)
        
    def draw(self):
        """Draw game by updating sprite positions - NO FLICKER VERSION"""
        # Larger buffer zones to prevent edge flickering
        # Was 32, now 64 pixels on each side = 128 pixel total buffer
        visible_left = self.camera.x - 64
        visible_right = self.camera.x + DISPLAY_WIDTH + 64
        
        # Track which sprites we use this frame
        used_platform_sprites = 0
        used_enemy_sprites = 0
        used_coin_sprites = 0
        
        # Update platform sprites (DON'T hide first, just update positions)
        platform_index = 0
        for platform in self.level.platforms:
            # CRITICAL FIX: Check if ANY part of platform is visible (not just left edge)
            # A platform is visible if its right edge is past the left boundary
            # AND its left edge is before the right boundary
            platform_right = platform.x + platform.width
            if platform_right > visible_left and platform.x < visible_right:
                if platform_index < len(self.platform_sprites):
                    sprite = self.platform_sprites[platform_index]
                    
                    # Update position
                    new_x = int(platform.x - self.camera.x)
                    new_y = int(platform.y)
                    
                    # Only update if position changed (reduces display updates)
                    if sprite.x != new_x or sprite.y != new_y:
                        sprite.x = new_x
                        sprite.y = new_y
                    
                    # Ensure visible
                    if sprite.hidden:
                        sprite.hidden = False
                    
                    # OPTIMIZED: Use class-level TILE_MAP instead of creating dict every frame
                    if self.sprite_loader.sprites_loaded:
                        tile = self.TILE_MAP.get(platform.block_type, 0)
                        sprite[0] = tile
                    
                    platform_index += 1
                    used_platform_sprites = platform_index
        
        used_platform_sprites = platform_index
        
        # Hide only the unused platform sprites
        for i in range(used_platform_sprites, len(self.platform_sprites)):
            if not self.platform_sprites[i].hidden:
                self.platform_sprites[i].hidden = True
                    
        # Update coin sprites (same pattern)
        coin_index = 0
        for coin in self.level.coins:
            # Coins are 8 pixels wide - check if any part is visible
            coin_right = coin.x + 8
            if not coin.collected and coin_right > visible_left and coin.x < visible_right:
                if coin_index < len(self.coin_sprites):
                    sprite = self.coin_sprites[coin_index]
                    
                    new_x = int(coin.x - self.camera.x)
                    new_y = int(coin.y)
                    
                    if sprite.x != new_x or sprite.y != new_y:
                        sprite.x = new_x
                        sprite.y = new_y
                    
                    if sprite.hidden:
                        sprite.hidden = False
                    
                    coin_index += 1
        
        used_coin_sprites = coin_index
        
        # Hide unused coin sprites
        for i in range(used_coin_sprites, len(self.coin_sprites)):
            if not self.coin_sprites[i].hidden:
                self.coin_sprites[i].hidden = True
                    
        # Update enemy sprites (same pattern)
        enemy_index = 0
        for enemy in self.level.enemies:
            # Enemies are 16 pixels wide - check if any part is visible
            enemy_right = enemy.x + enemy.width
            if enemy.alive and enemy_right > visible_left and enemy.x < visible_right:
                if enemy_index < len(self.enemy_sprites):
                    sprite = self.enemy_sprites[enemy_index]
                    
                    new_x = int(enemy.x - self.camera.x)
                    new_y = int(enemy.y)
                    
                    if sprite.x != new_x or sprite.y != new_y:
                        sprite.x = new_x
                        sprite.y = new_y
                    
                    if sprite.hidden:
                        sprite.hidden = False
                    
                    if self.sprite_loader.sprites_loaded:
                        sprite[0] = enemy.sprite_frame
                    
                    enemy_index += 1
        
        used_enemy_sprites = enemy_index
        
        # Hide unused enemy sprites
        for i in range(used_enemy_sprites, len(self.enemy_sprites)):
            if not self.enemy_sprites[i].hidden:
                self.enemy_sprites[i].hidden = True
                    
        if self.mario.invincible == 0 or self.mario.invincible % 10 < 5:
            screen_x = int(self.mario.x - self.camera.x)
            self.mario_sprite.x = screen_x
            self.mario_sprite.y = int(self.mario.y)
            self.mario_sprite.hidden = False
            
            # OPTIMIZED: Only update sprite properties if they changed
            if self.sprite_loader.sprites_loaded:
                if self.mario.sprite_frame != self.last_mario_frame:
                    self.mario_sprite[0] = self.mario.sprite_frame
                    self.last_mario_frame = self.mario.sprite_frame
                
                facing = not self.mario.facing_right
                if facing != self.last_mario_flip:
                    self.mario_sprite.flip_x = facing
                    self.last_mario_flip = facing
        else:
            self.mario_sprite.hidden = True
        
        self.hud.update(self.score, self.coins, self.lives)
    
    def reset_level(self):
        """Reset the level to start over"""
        print("\n" + "="*50)
        print("RESTARTING LEVEL...")
        print("="*50 + "\n")
        
        # Clean up audio before reset
        self.audio_manager.stop()
        
        self.level = Level()
        self.mario = Mario(40, GROUND_Y)
        self.camera = Camera()
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.game_over = False
        self.level_complete = False
        self.victory_timer = 0
        
        self.victory_screen.hide()
        self.game_over_screen.hide()
        self.hud.show()
        
        self.neopixels.update(self.mario, self.score, self.lives, False)
        
        # MEMORY: Force garbage collection after reset
        gc.collect()
            
    def run(self):
        """Main loop - MEMORY OPTIMIZED"""
        print("\n" + "="*50)
        print("SUPER MARIO BROS - IMU EDITION")
        print("="*50)
        print("Tilt to move, D3 to jump, CAP1 to run!")
        if self.sprite_loader.sprites_loaded:
            print("Graphics: Real sprite graphics! 🎨")
        else:
            print("Graphics: Colored rectangles (sprites not found)")
        if self.audio_manager.audio_enabled:
            print(f"Audio: {len(self.audio_manager.sounds)} sound effects! 🔊")
        else:
            print("Audio: Disabled (no audio files or hardware)")
        print("Sprite reuse enabled - smooth rendering!")
        print("MEMORY LEAK FIXES ACTIVE - AGGRESSIVE GC")
        print("="*50 + "\n")
        
        frame = 0
        
        while not self.game_over:
            # CRITICAL: Poll button IMMEDIATELY at start of frame
            # This catches presses that happened during draw() or sleep()
            self.imu_control.poll_button_only()
            
            self.update()
            self.draw()
            
            frame += 1
            
            # MEMORY: Balanced garbage collection - every 90 frames (3 seconds at 30 FPS)
            # MOVED HERE: GC only in main loop, NOT during audio playback!
            if frame % 90 == 0:
                gc.collect()
                if Debug or frame % 180 == 0:
                    print(f"Score: {self.score} | Coins: {self.coins} | Lives: {self.lives} | Free RAM: {gc.mem_free()}")
                
            time.sleep(0.033)
            
        # Game over - hold screen and let audio play
        print(f"\n{'='*50}")
        print(f"GAME OVER! Score: {self.score}")
        print(f"Final free memory: {gc.mem_free()} bytes")
        print("="*50)
        
        if self.neopixels.available:
            self.neopixels.pixels.fill(0xFF0000)
            self.neopixels.pixels.show()
        
        # Hold the game over screen for 5 seconds and let audio finish playing
        print("Displaying game over screen...")
        hold_frames = 150  # 5 seconds at 30 FPS
        for i in range(hold_frames):
            # Keep display active but don't update game state
            time.sleep(0.033)
            # Check if audio is still playing, if finished we can wait quietly
            if i % 30 == 0:  # Every second
                if self.audio_manager.is_playing():
                    print(f"  Game over audio playing... ({i//30 + 1}s)")
                else:
                    print(f"  Holding screen... ({i//30 + 1}s)")
        
        print("Game over sequence complete.")
            
        # CRITICAL: Clean up audio on exit
        self.audio_manager.stop()

if __name__ == "__main__":
    game = MarioGame()
    game.run()