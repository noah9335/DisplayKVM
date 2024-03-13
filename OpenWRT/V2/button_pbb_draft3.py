import gpio as GPIO
from time import sleep, time

##IN
btn = 59
GPIO.GPIOPin(btn, GPIO.IN)
print (GPIO.mode(btn))

##IN NEW
while True:
    if(GPIO.input(btn) == 0): #check button pressed
        start = time() #start timer
        sleep(0.02)
        while(GPIO.input(btn) == 0): #always loop if button pressed
            sleep(0.01)
        length = time() - start #get long time button pressed
        long_press_length = 1 # seconds
        if (length > long_press_length): #if button greater x seconds statement active
            # long press function
            print ("Long press")
        else:
            # short press function
            print ("Short press")
        print("press duration: "+str(length))
    else:
        print("await")
    sleep(0.2)

##IN OLD
#while True:
#	print (GPIO.input(btn))
#	time.sleep(0.2)

##OUT
##GPIO.setup(btn, GPIO.OUT)
#GPIO.GPIOPin(btn, GPIO.OUT)
#print (GPIO.mode(btn))
#GPIO.output(btn, GPIO.HIGH)
##GPIO.output(btn, GPIO.LOW)
#print (GPIO.input(btn))
