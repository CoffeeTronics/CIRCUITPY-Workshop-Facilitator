"""
This demo will read the IMU data and print it to the Serial Monitor.
"""
import time
import board
import adafruit_icm20x

# Change this to False to hide debug print statements
Debug = True

i2c = board.I2C()  # use board.SCL and board.SDA pins for the IMU

try:
    icm = adafruit_icm20x.ICM20948(i2c, 0x69)
except:
    print("No ICM20948 found at default address 0x69. Trying alternate address 0x68.")
    try:
        icm = adafruit_icm20x.ICM20948(i2c, 0x68)
    except:
        print("No ICM20948 device found! Make sure the dev board and ruler are connected properly!")


while True:
    X, Y, Z = icm.acceleration

    if Debug:
        print("X: {:.2f}".format(X))
        print("Y: {:.2f}".format(Y))
        print("Z: {:.2f}".format(Z))
        print("")

    time.sleep(0.1)
