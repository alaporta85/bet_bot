import os
from telegram.ext import Updater
from Functions import logging_file as log


# TELEGRAM BOT
with open('token.txt', 'r') as f:
	UPDATER = Updater(token=f.readline())
DISPATCHER = UPDATER.dispatcher

DEBUG = False
GROUP_ID = -235014519 if not DEBUG else 67507055

# SELENIUM SCRAPING
MAIN_PAGE = 'https://www.lottomatica.it/scommesse/avvenimenti'
ABSOLUTE_PATH = os.getcwd()
CHROME_PATH = ABSOLUTE_PATH + '/chromedriver'
MATCHES_TO_SCRAPE = 100
WAIT = 10
RECURSIONS = 3
HOURS_RANGE = 96
PANELS_TO_USE = ["piu' giocate", 'under/over', 'goal', 'combo',
                 'combo parziale/finale', 'combo doppia chance',
                 'tempo 1', 'tempo 2', 'parziale e finale']

# LOGGING
LOGGER = log.set_logging()

# PLAY
LIM_LOW = 1.8
LIM_HIGH = 3.2
N_BETS = 5
DEFAULT_EUROS = 5

# UPDATING
BETS_FILTER = 'Ultimi 3 Mesi'

# SCORE
YEARS = ['general', '2017-2018', '2018-2019', '2019-2020', '2020-2021']
