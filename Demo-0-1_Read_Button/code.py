import board
import digitalio

# create user button object 
user_button = digitalio.DigitalInOut(board.D3)
# set up user button as an input
user_button.direction = digitalio.Direction.INPUT

# create led object 
led = digitalio.DigitalInOut(board.LED)
# set up led as an output
led.direction = digitalio.Direction.OUTPUT


while True:     # loop forever
    # get the value of the button - returns True or False
    button = user_button.value

    # if button is False turn on led
    if (not button):
        led.value = True
    # otherwise turn off led
    else:
        led.value = False
