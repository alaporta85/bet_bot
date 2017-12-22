import os
import time
import signal

wdir = os.getcwd()
fileName = wdir + '/logs/bet_bot.log'
os.system("open " + fileName)

time.sleep(2)

plot = os.system("screencapture -R0,22,747,705 Images/log.png")

