import board
import digitalio

# configure User Button as digital input
# NOTE: button is Active LOW
user_button = digitalio.DigitalInOut(board.D3)
user_button.direction = digitalio.Direction.INPUT

# configure onboard LED as output
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# set initial states for the button  
current_button_state = False
last_button_state = False

# set initial state for LED - start with LED off
led_state = False   

while True:
    # read the button and save to current state
    current_button_state = user_button.value

    # if the button has been pressed, the current state will be different to the last state
    if (not current_button_state and last_button_state):    
        print ("Button pressed!")       # write to serial monitor as a sanity check
        led_state = not led_state       # set the LED state to be the opposite of what it was
        led.value = led_state           # write the state to the LED

    last_button_state = current_button_state    # save the button state for the next time through the loop 
