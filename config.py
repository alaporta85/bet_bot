import os
import db_functions as dbf
from telegram.ext import Updater
from Functions import logging_file as log


# TELEGRAM BOT
with open('token.txt', 'r') as f:
    UPDATER = Updater(token=f.readline(), use_context=True)
DISPATCHER = UPDATER.dispatcher
JOB_QUEUE = UPDATER.job_queue

DEBUG = False
TESTAZZA_ID = 67507055
GROUP_ID = -235014519 if not DEBUG else TESTAZZA_ID

# SELENIUM SCRAPING
MAIN_PAGE = 'https://www.lottomatica.it/scommesse/avvenimenti'
ABSOLUTE_PATH = os.getcwd()
CHROME_PATH = ABSOLUTE_PATH + '/chromedriver'
MATCHES_TO_SCRAPE = 100
WAIT = 30
HOURS_RANGE = 240
PANELS_TO_USE = ['PRINCIPALI', 'U/O', 'PRIMO TEMPO', 'SECONDO TEMPO',
                 '1°TEMPO/FINALE', 'COMBO']

# LOGGING
LOGGER = log.set_logging()

# PLAY
LIM_LOW = 1.4
LIM_HIGH = 3.2
N_BETS = 6
DEFAULT_EUROS = 5
WEEKDAYS = {'lun': 1, 'mar': 2, 'mer': 3, 'gio': 4,
            'ven': 5, 'sab': 6, 'dom': 7}

# UPDATING
BETS_FILTER = 'Ultimi 3 Mesi'

# SCORE
YEARS = ['general', '2017-2018', '2018-2019', '2019-2020', '2020-2021',
         '2021-2022', '2022-2023']

# SCRAPING
URL = 'https://www.diretta.it'
LEAGUES = dbf.db_select(
        table='leagues',
        columns=['name'],
        where='is_active=1'
)
