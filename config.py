import os
from telegram.ext import Updater
from selenium.webdriver.chrome.options import Options
from Functions import logging_file as log

with open('token.txt', 'r') as f:
	UPDATER = Updater(token=f.readline())
DISPATCHER = UPDATER.dispatcher

MAIN_PAGE = 'https://www.lottomatica.it/scommesse/avvenimenti'

DEBUG = True
GROUP_ID = -235014519 if not DEBUG else 67507055


LIM_LOW = 1
LIM_HIGH = 3.2
N_BETS = 6

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.binary_location = ('/Applications/Google Chrome.app/' +
								  'Contents/MacOS/Google Chrome')

absolute_path = os.getcwd()
chrome_path = absolute_path + '/chromedriver'
logger = log.get_flogger()

MATCHES_TO_SCRAPE = 100
WAIT = 10
RECURSIONS = 3
PANELS_TO_USE = ["piu' giocate", 'under/over', 'goal', 'combo',
                 'combo parziale/finale', 'combo doppia chance',
                 'tempo 1', 'tempo 2', 'parziale e finale']

DAYS_RANGE = 4
