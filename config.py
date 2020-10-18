import os
import datetime
from selenium.webdriver.chrome.options import Options
from Functions import logging_file as log

countries = {
			 'SERIE A': 'italia/seriea.html',
			 'PREMIER LEAGUE': 'inghilterra/premierleague.html',
			 'PRIMERA DIVISION': 'spagna/primeradivision.html',
			 # 'BUNDESLIGA': 'germania/bundesliga.html',
			 # 'LIGUE 1': 'francia/ligue1.html',
			 # 'EREDIVISIE': 'olanda/eredivisie1.html',
			 # 'CHAMPIONS LEAGUE': 'europa/championsleague.html',
			 }

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.binary_location = ('/Applications/Google Chrome.app/' +
								  'Contents/MacOS/Google Chrome')

absolute_path = os.getcwd()
chrome_path = absolute_path + '/chromedriver'
logger = log.get_flogger()

WAIT = 10
RECURSIONS = 3
PANELS_TO_USE = ["piu' giocate", 'under/over', 'goal', 'combo',
                 'combo parziale/finale', 'combo doppia chance',
                 'tempo 1', 'tempo 2', 'parziale e finale']

TODAY = datetime.date.today()
DAYS_RANGE = 3
