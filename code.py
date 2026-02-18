Sudo commands 
To import adafruit_ dht 
sudo apt update
sudo apt upgrade
sudo apt install python3-pip build-essential python3-dev pigpio python3-pigpio
sudo pip3 install RPi.GPIO gpiozero hcsr04sensor Adafruit_DHT
sudo systemctl start pigpiod
sudo systemctl enable pigpiod
-----sudo commands
 Code  of the project

 import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import requests

# ==== Setup ====

# DHT setup
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4

# GPIO Pins
LED_PIN = 17
SERVO_PIN = 18
BUZZER_PIN = 22

# Ultrasonic sensor pins
TRIG = 23
ECHO = 24

# LCD Pins (BCM)
LCD_RS = 26
LCD_E = 19
LCD_D4 = 13
LCD_D5 = 6
LCD_D6 = 5
LCD_D7 = 11
LCD_WIDTH = 16

# ThingSpeak
THINGSPEAK_API_KEY = 'XU838M2N094QFJQI'
THINGSPEAK_URL = 'https://api.thingspeak.com/update'

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup([LCD_RS, LCD_E, LCD_D4, LCD_D5, LCD_D6, LCD_D7], GPIO.OUT)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Servo PWM
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

# ==== LCD Functions ====

def lcd_toggle_enable():
    time.sleep(0.0005)
    GPIO.output(LCD_E, True)
    time.sleep(0.0005)
    GPIO.output(LCD_E, False)
    time.sleep(0.0005)

def lcd_send_nibble(bits):
    GPIO.output(LCD_D4, bool(bits & 0x10))
    GPIO.output(LCD_D5, bool(bits & 0x20))
    GPIO.output(LCD_D6, bool(bits & 0x40))
    GPIO.output(LCD_D7, bool(bits & 0x80))
    lcd_toggle_enable()

def lcd_send_byte(bits, mode):
    GPIO.output(LCD_RS, mode)
    lcd_send_nibble(bits & 0xF0)
    lcd_send_nibble((bits << 4) & 0xF0)

def lcd_init():
    lcd_send_byte(0x33, 0)
    lcd_send_byte(0x32, 0)
    lcd_send_byte(0x28, 0)
    lcd_send_byte(0x0C, 0)
    lcd_send_byte(0x06, 0)
    lcd_send_byte(0x01, 0)
    time.sleep(0.005)

def lcd_message(message, line=1):
    if line == 1:
        lcd_send_byte(0x80, 0)
    elif line == 2:
        lcd_send_byte(0xC0, 0)
    message = message.ljust(LCD_WIDTH, " ")
    for char in message:
        lcd_send_byte(ord(char), 1)

# ==== Other Functions ====

def set_servo_angle(angle):
    duty = angle / 18 + 2
    servo.ChangeDutyCycle(duty)
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.05)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    d = round(pulse_duration * 17150, 2)
    return d

def send_to_thingspeak(t, h, angle, d):
    try:
        data = {
            'api_key': THINGSPEAK_API_KEY,
            'field1': t,
            'field2': h,
            'field3': angle,
            'field4': d
        }
        response = requests.post(THINGSPEAK_URL, data=data, timeout=5)
        print("Data sent to ThingSpeak, response: {}".format(response.text))
    except Exception as e:
        print("Failed to send data to ThingSpeak:", e)

# ==== MAIN PROGRAM ====

try:
    lcd_init()
    while True:
        print("=== New Loop Iteration ===")
        h, t = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        d = get_distance()

        if h is not None and t is not None:
            print("t={0:.1f}°C  h={1:.1f}%".format(t, h))
            print("d = {} cm".format(d))

            # LCD display
            lcd_message("t: {:.1f}C".format(t), line=1)
            lcd_message("h:{:.1f}% d:{:.0f}".format(h, d), line=2)

            # Temp-based logic
            if t > 30:
                print("Hot! Opening vent.")
                GPIO.output(LED_PIN, GPIO.HIGH)
                angle = 90
            elif t < 20:
                print("Cold. Closing vent.")
                GPIO.output(LED_PIN, GPIO.LOW)
                angle = 0
            else:
                print("Moderate temp. Half-open.")
                GPIO.output(LED_PIN, GPIO.HIGH)
                angle = 45

            set_servo_angle(angle)

            # Distance-based buzzer
            if d < 10:
                print("Object too close! Buzzing.")
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
            else:
                GPIO.output(BUZZER_PIN, GPIO.LOW)

            # Send to ThingSpeak
            send_to_thingspeak(t, h, angle, d)

        else:
            print("Sensor read error")
            lcd_message("Sensor error", line=1)

        print("Sleeping 15s...\n")
        time.sleep(15)

except KeyboardInterrupt:
    print("Keyboard Interrupt. Cleaning up...")
    lcd_send_byte(0x01, 0)
    servo.stop()
GPIO.cleanup()
