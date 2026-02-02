import time
import board
# random added to send randomized colors to NeoPixel 0
import random   
# asyncio added for asynchronous multitasking 
# Make sure it is in D:\CIRCUITPY\lib folder!
import asyncio  

try:
    import neopixel
    # Make sure it is in D:\CIRCUITPY\lib folder!
except ImportError:
    raise ImportError("Please copy neopixel.mpy into /lib")

pixel_pin = board.NEOPIXEL
num_pixels = 5
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.05, auto_write=True)

NEOPIXEL_RED = (255, 0, 0)
NEOPIXEL_YELLOW = (255, 150, 0)
NEOPIXEL_GREEN = (0, 255, 0)
NEOPIXEL_BLUE = (0, 0, 255)
NEOPIXEL_OFF = (0, 0, 0)
NEOPIXEL_RANDOM = (random.randrange(255), random.randrange(255), random.randrange(255))

# pixel is neopixel number, count is for-loop counter, interval is blink rate, color_value is one of the colors previously defined
async def blinks(pixel, interval, count, color_value):
	for _ in range(count):
		pixels[pixel] = color_value
		await asyncio.sleep(interval)   
		pixels[pixel] = NEOPIXEL_OFF
		await asyncio.sleep(interval)   
print("Start") # So we know that it actually started!

async def main():
    pixel_task1 = asyncio.create_task(blinks(0, 0.30, 15, NEOPIXEL_RANDOM ))
    pixel_task2 = asyncio.create_task(blinks(1, 0.75, 10, NEOPIXEL_GREEN))
    pixel_task3 = asyncio.create_task(blinks(2, 1.0,  10, NEOPIXEL_RED))
    pixel_task4 = asyncio.create_task(blinks(3, 0.50, 10, NEOPIXEL_YELLOW))
    pixel_task5 = asyncio.create_task(blinks(4, 0.25, 15, NEOPIXEL_BLUE))

# gather statement initiates the task loop and passes control to the first in the list - await is mandatory
    await asyncio.gather(pixel_task1, pixel_task2, pixel_task3, pixel_task4, pixel_task5)
    print("Finished") # So we know that it actually finished!

asyncio.run(main())
