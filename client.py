#!/usr/bin/python

# https://docs.python.org/2/howto/logging.html#logging-basic-tutorial
# http://pyserial.readthedocs.org/en/latest/shortintro.html

import optparse
import ConfigParser
import os
import serial
import serial.tools.list_ports
import logging
import sys
import RPi.GPIO as GPIO
import time
import requests
import signal
import lcdModule as LCD

# hold all the options loaded from the config file
configOptions = {}
currentUser = False
currentUserID = False
currentUserTime = 0
globalDeviceName = False

parser = optparse.OptionParser()
parser.add_option("-f", "--config",
                  default="/opt/tinkeraccess/client.cfg",
                  help='config file to use', dest="configFileLocation", action="store")

(opts, args) = parser.parse_args()

def exitme():
  sys.exit()
signal.signal(signal.SIGINT, exitme)

# Begin Initalize ##

# Parse configuration
c = ConfigParser.SafeConfigParser()
if os.path.isfile(opts.configFileLocation):
  c.read(opts.configFileLocation)
  configOptions['logFile']         = c.get('config', 'logFile')
  configOptions['logLevel']        = c.getint('config', 'logLevel')
  configOptions['server']          = c.get('config', 'server')
  configOptions['deviceID']        = c.get('config', 'deviceID')
  configOptions['serialPortName']  = c.get('config', 'serialPortName')
  configOptions['serialPortSpeed'] = c.get('config', 'serialPortSpeed')
  configOptions['pin_logout']      = c.getint('config', 'pin_logout')
  configOptions['pin_relay']      = c.getint('config', 'pin_relay')
  configOptions['pin_led_r']      = c.getint('config', 'pin_led_r')
  configOptions['pin_led_g']      = c.getint('config', 'pin_led_g')
  configOptions['pin_led_b']      = c.getint('config', 'pin_led_b')

# setup logging
logging.basicConfig(filename=configOptions['logFile'] , level=configOptions['logLevel'] )
#logging.basicConfig(level=configOptions['logLevel'] )

# configure GPIO
GPIO.setmode( GPIO.BCM )
GPIO.cleanup()
GPIO.setwarnings(False)

GPIO.setup( configOptions['pin_logout'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup( configOptions['pin_relay'], GPIO.OUT)
GPIO.setup( configOptions['pin_led_r'], GPIO.OUT)
GPIO.setup( configOptions['pin_led_g'], GPIO.OUT)
GPIO.setup( configOptions['pin_led_b'], GPIO.OUT)
GPIO.output( configOptions['pin_relay'], GPIO.LOW )
GPIO.output(configOptions['pin_led_r'], False)
GPIO.output(configOptions['pin_led_g'], False)
GPIO.output(configOptions['pin_led_b'], False)

# configure the serial port
if not os.path.exists(configOptions['serialPortName']):
  logging.fatal("Unable to find serial port %s" % configOptions['serialPortName'] )
  sys.exit(1)

serialConnection = serial.Serial( configOptions['serialPortName'], configOptions['serialPortSpeed'] )
serialConnection.flushInput()
serialConnection.flushOutput()

LCD.lcd_init()
LCD.lcd_string("Scan Badge" ,LCD.LCD_LINE_1)
LCD.lcd_string("To Login" ,LCD.LCD_LINE_2)

# End Initialize ##

def led(r,g,b):
  global configOptions
  GPIO.output(configOptions['pin_led_r'], r)
  GPIO.output(configOptions['pin_led_g'], g)
  GPIO.output(configOptions['pin_led_b'], b)

def requestAccess(badgeCode):
  global configOptions
  url = "%s/device/%s/code/%s" % (configOptions['server'], configOptions['deviceID'], badgeCode)
  logging.debug("calling server:" + url)

  serverResponse = requests.get(url)
  data       = serverResponse.json()
  username   = data['username']
  devicename = data['devicename']
  userid     = data['userid']
  timelimit  = data['time']

  logging.debug("server response %s,%s,%s,%s" % (username, devicename, userid, timelimit))
  return (username, devicename, timelimit, userid)



# what to do when the logout button is pressed
def event_logout():
  global configOptions, currentUser,currentUserID

  if currentUser:

    # tell the server we have logged out
    url = "%s/device/%s/logout/%s" % (configOptions['server'], configOptions['deviceID'], currentUserID)
    logging.debug("calling server:" + url)
    re = requests.get(url)
    logging.debug("server response:" + re.text)

    logging.info("%s logged out" % currentUser )
    GPIO.output( configOptions['pin_relay'], GPIO.LOW )
    currentUser = False
    currentUserTime = 0
    currentUserID = False
  else:
    currentUserTime = 0

  LCD.lcd_string("Scan Badge" ,LCD.LCD_LINE_1)
  LCD.lcd_string("To Login" ,LCD.LCD_LINE_2)
  led(False,False,False)

def event_login(badgeCode):
  global currentUser,currentUserID, currentUserTime,globalDeviceName,configOptions

  v = requestAccess(badgeCode)

  if v[2] > 0:
    logging.info("Access granted for %s granted with time %s" % (badgeCode, v) )
    GPIO.output( configOptions['pin_relay'], GPIO.HIGH)
    currentUser = v[0]
    currentUserID = v[3]
    currentUserTime = time.time() + ( v[2] * 60 )
    globalDeviceName = v[1]
    led(True,True,False)
  else:
    if currentUser:
      logging.info("Access denied for %s but %s already logged in" % (badgeCode, currentUser))
      return
    logging.info("Access denied for %s " % badgeCode )
    led(True,False,False)
    time.sleep(1)
    led(False,False,False)
    GPIO.output( configOptions['pin_relay'], GPIO.LOW )


def loop():
  global currentUserTime, currentUser, configOptions

  while True:
    time.sleep(.01)

    if currentUser:
      LCD.lcd_string(currentUser,LCD.LCD_LINE_1)
      if currentUserTime - time.time() < 300:
        led(True,False,True)
        LCD.lcd_string( str( int(round( (currentUserTime - time.time())))) + " Seconds" ,LCD.LCD_LINE_2)
      else:
        LCD.lcd_string( str( int(round( (currentUserTime - time.time())/60 ))) + " Minutes" ,LCD.LCD_LINE_2)

    # if the user runs out of time, log them out
    if currentUser != False and currentUserTime < time.time():
      event_logout()
      continue

    # if the user logs out with the logout button log them out
    if GPIO.input( configOptions['pin_logout'] ) == GPIO.HIGH:
      event_logout()
      time.sleep(.2)
      continue

    # if the serial port has data read it.
    if serialConnection.inWaiting() > 1:
      badgeCode = serialConnection.readline().strip()[-11:-1]
      data = event_login(badgeCode)
      continue


loop()