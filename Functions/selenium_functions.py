import os
import time
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from Functions import logging as log
from Functions import db_functions as dbf
from Functions import bot_functions as bf


countries = {
			 'SERIE A': 'italia/seriea.html',
			 'PREMIER LEAGUE': 'inghilterra/premierleague.html',
			 'PRIMERA DIVISION': 'spagna/primeradivision.html',
			 'BUNDESLIGA': 'germania/bundesliga.html',
			 'LIGUE 1': 'francia/ligue1.html',
			 'EREDIVISIE': 'olanda/eredivisie1.html',
			 'CHAMPIONS LEAGUE': 'europa/championsleague.html',
			 }

conn_err_message = ('An error occurred. This might be due to some problems ' +
					'with the internet connection. Please try again.')

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.binary_location = ('/Applications/Google Chrome.app/' +
								  'Contents/MacOS/Google Chrome')

absolute_path = os.getcwd()
chrome_path = absolute_path + '/chromedriver'
logger = log.get_flogger()

WAIT = 10
recurs_lim = 3


def add_bet_to_basket(browser, details, count, dynamic_message):  # DONE

	"""
	Click the bet button and add it to the basket.
	Used inside the command /play.

	:param browser: selenium browser instance

	:param details: tuple, contain field and bet names

	:param count: int

	:param dynamic_message: str, the message to update in the chat


	:return: str, dynamic message updated

	"""

	field, bet = details

	click_bet(browser, field, bet)
	time.sleep(10)

	return dynamic_message.format(count + 1)


def all_matches_missing(browser, all_matches, league):  # DONE

	"""
	Check if the container with all the matches is present. Sometimes it is
	missing because the league is not playing.
	Used inside fill_db_with_quotes().

	:param browser: selenium browser instance

	:param all_matches: str, box xpath

	:param league: str, name of the league. Ex. SERIE A



	:return: bool, True if missing otherwise False

	"""

	for j in range(recurs_lim):
		try:
			wait_clickable(browser, WAIT, all_matches)
			return False
		except TimeoutException:
			logger.info('FILL DB WITH QUOTES - MATCHES for ' +
			            '{} not found: trial {}.'.format(league, j + 1))
			browser.refresh()

	return True


def analyze_details_table(browser, ref_id, new_status, LIMIT_4):

	"""
	Used in analyze_main_table function. It first checks if all the matches
	inside the bet are concluded. If yes, update the column bet_result in
	the table 'bet' and the columns 'pred_result' and pred_label in the
	table 'predictions' of the database.
	"""

	try:

		prize_table = ('//div[@class="col-md-5 col-lg-5 col-xs-5 ' +
					   'pull-right pull-down"]')
		prize_element = browser.find_elements_by_xpath(prize_table +
													   '//tr/td')[7]
		prize_value = float(prize_element.text[:-1].replace('.', '').
		                    replace(',', '.'))

		dbf.db_update(
				table='bets',
				columns=['bet_prize'],
				values=[prize_value],
				where='bet_id = {}'.format(ref_id))

		new_table_path = './/table[@class="bet-detail"]'
		wait_visible(browser, 20, new_table_path)
		new_bets_list = browser.find_elements_by_xpath(
				new_table_path + '//tr[@class="ng-scope"]')

		# Count the matches inside the bet which are already concluded
		matches_completed = 0
		for new_bet in new_bets_list:
			label_element = new_bet.find_element_by_xpath(
				'.//div[contains(@class,"ng-scope")]')
			label = label_element.get_attribute('ng-switch-when')
			if label == 'WINNING' or label == 'LOSING':
				matches_completed += 1

		# If not all of them are concluded code stops here
		if matches_completed != len(new_bets_list):
			logger.info('Bet with id {} is still incomplete'.format(ref_id))
			return 0

		logger.info('Updating bet with id: {}'.format(ref_id))
		for new_bet in new_bets_list:
			match = new_bet.find_element_by_xpath('.//td[6]').text
			team1 = dbf.select_team(match.split(' - ')[0])
			team2 = dbf.select_team(match.split(' - ')[1])
			label_element = new_bet.find_element_by_xpath(
					'.//div[contains(@class,"ng-scope")]')
			label = label_element.get_attribute('ng-switch-when')
			quote = float(new_bet.find_element_by_xpath('.//td[10]').text)
			result = new_bet.find_element_by_xpath('.//td[11]').text

			match_id = dbf.db_select(
					table='bets INNER JOIN predictions on pred_bet = bet_id',
					columns_in=['pred_id'],
					where=('bet_id = {} AND pred_team1 = "{}" AND ' +
					       'pred_team2 = "{}"').
					format(ref_id, team1, team2))[0]

			dbf.db_update(
					table='bets',
					columns=['bet_result'],
					values=[new_status],
					where='bet_id = {}'.format(ref_id))

			dbf.db_update(
					table='predictions',
					columns=['pred_quote', 'pred_result', 'pred_label'],
					values=[quote, result, label],
					where='pred_id = {}'.format(match_id))

		return 1

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_4 < 3:
			logger.info('Recursive analyze_details_table')
			browser.refresh()
			time.sleep(3)
			return analyze_details_table(browser, ref_id,
			                             new_status, LIMIT_4 + 1)
		else:
			raise ConnectionError('Unable to find past bets. ' +
								  'Please try again.')


def analyze_main_table(browser, ref_list, LIMIT_3):

	"""
	Used in update_results() function to drive the browser to the personal
	area in the 'MOVIMENTI E GIOCATE' section and call the function
	analyze_details_table for each bet not updated yet.
	"""

	bets_updated = 0

	try:
		table_path = './/table[@id="tabellaRisultatiTransazioni"]'
		wait_visible(browser, 20, table_path)
		bets_list = browser.find_elements_by_xpath(table_path +
												   '//tr[@class="ng-scope"]')

		# updated = []
		for ref_bet in ref_list:
			ref_id = ref_bet[0]
			details_db = dbf.db_select(
					table='predictions',
					columns_in=['pred_team1', 'pred_team2'],
					where='pred_bet = {}'.format(ref_id))
			# ref_date = '/'.join(list(reversed(ref_bet[1][:10].split('-'))))

			for bet in bets_list:

				color = bet.find_element_by_xpath(
						'.//td[contains(@class,"state state")]')\
					.get_attribute('class')

				if 'blue' not in color:

					# date = bet.find_element_by_xpath(
					# 		'.//td[@class="ng-binding"]').text[:10]
					#
					# if date == ref_date and date in updated:
					# 	updated.remove(date)
					# 	continue
					#
					# elif date == ref_date and date not in updated:
					# 	updated.append(date)

						new_status = bet.find_element_by_xpath(
								'.//translate-label[@key-default=' +
								'"statement.state"]').text

						if new_status == 'Vincente':
							new_status = 'WINNING'
						elif new_status == 'Non Vincente':
							new_status = 'LOSING'

						main_window = browser.current_window_handle
						details = bet.find_element_by_xpath('.//a')
						scroll_to_element(browser, details)
						details.click()
						time.sleep(3)

						new_window = browser.window_handles[-1]
						browser.switch_to_window(new_window)
						time.sleep(1)

						new_table_path = './/table[@class="bet-detail"]'
						wait_visible(browser, 20, new_table_path)
						new_bets_list = browser.find_elements_by_xpath(
								new_table_path + '//tr[@class="ng-scope"]')

						details_web = []
						for new_bet in new_bets_list:
							match = new_bet.find_element_by_xpath(
								'.//td[6]').text
							team1 = dbf.select_team(match.split(' - ')[0])
							team2 = dbf.select_team(match.split(' - ')[1])
							details_web.append((team1, team2))
						if set(details_db) - set(details_web):
							browser.close()
							browser.switch_to_window(main_window)
							continue

						bets_updated += analyze_details_table(browser, ref_id,
															  new_status, 0)

						browser.close()

						browser.switch_to_window(main_window)
						break


		return bets_updated

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_3 < 3:
			logger.info('Recursive analyze_main_table')
			browser.refresh()
			time.sleep(3)
			return analyze_main_table(browser, ref_list, LIMIT_3 + 1)
		else:
			raise ConnectionError('Unable to find past bets. ' +
								  'Please try again.')


def click_bet(browser, field, bet):   # DONE

	"""
	Find the button relative to the bet to play and click it.
	Used inside the function add_bet_to_basket().

	:param browser: selenium browser instance

	:param field: str, Ex. GOAL/NOGOAL + U/O 2,5

	:param bet: str, Ex. GOAL + OVER


	:return: nothing

	"""

	CLICK_CHECK = False

	# All panels. Ex. Più giocate, Combo, Casa...
	all_panels = find_all_panels(browser)

	for i, panel in enumerate(all_panels):

		# Open the panel if closed
		click_panel(browser, i, panel)

		# Select fields and bets containers inside the panel. Each field has
		# a bets container which contains multiple bets
		fields_path = ('./div[contains(@class, "group-market")]//' +
		               'div[@class="market-info"]/div')
		bets_path = ('./div[contains(@class, "group-market")]//' +
		             'div[@class="market-selections"]')

		fields = panel.find_elements_by_xpath(fields_path)
		bets = panel.find_elements_by_xpath(bets_path)

		# Associate each field with its bets and loop through all of them
		for field_, bets_ in zip(fields, bets):
			scroll_to_element(browser, field_)
			field_name = field_.text.upper()

			# When the correct field is found
			if field_name == field:

				# Select all the bets associated
				all_bets = bets_.find_elements_by_xpath(
						'.//div[@ng-repeat="selection in prematchSingle' +
						'EventMarketSimple.market.sel"]')

				# In case the field is ESITO FINALE 1X2 HANDICAP the bets have
				# a different path
				if not all_bets:
					all_bets = bets_.find_elements_by_xpath(
							'.//div[@ng-repeat="selection in market.sel"]')

				# Loop through all the bets until we find the correct one
				for new_bet in all_bets:
					scroll_to_element(browser, new_bet)

					if field_name == 'ESITO FINALE 1X2 HANDICAP':
						bet_name = new_bet.find_element_by_xpath(
								'.//div[@class="selection-name ' +
								'ng-binding"]').text.upper().split()[0]
					else:
						bet_name = new_bet.find_element_by_xpath(
								'.//div[@class="selection-name ' +
								'ng-binding"]').text.upper()

					# When found, we click it and break
					if bet_name == bet:
						new_bet.click()
						CLICK_CHECK = True
						break
				break

			else:
				continue

		if CLICK_CHECK:
			break


def click_panel(browser, index, panel):   # DONE

	"""
	Click the panel to open it, if closed.
	Used inside click_bet() and find_all_fields_and_bets() functions.

	:param browser: selenium browser instance

	:param index: int, index of the panel to click

	:param panel: selenium element


	:return: nothing

	"""

	# button = panel.find_elements_by_xpath(
	# 		'//div[contains(@class, "group-name")]')[index]
	button = panel.find_element_by_xpath(
			'.//div[contains(@class, "group-name")]')
	scroll_to_element(browser, button)
	name = button.text

	WebDriverWait(
			browser, WAIT).until(EC.element_to_be_clickable(
				(By.LINK_TEXT, name)))

	if 'active' not in button.get_attribute('class'):
		scroll_to_element(browser, button)
		button.find_element_by_xpath('.//a').click()
		time.sleep(1)


def connect_to(some_url, browser=None):   # DONE

	"""
	Connect to website address.
	Used inside command /play.

	:param some_url: str

	:param browser: selenium browser instance


	:return: selenium browser instance

	"""

	if not browser:
		# browser = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
		browser = webdriver.Chrome(chrome_path)
		time.sleep(3)

	browser.get(some_url)

	return browser


def extract_bet_name(field, bet_element):

	# Bet name has a different path for the field 'ESITO FINALE 1X2
	# HANDICAP', don't know why
	if field == 'ESITO FINALE 1X2 HANDICAP':
		return bet_element.text.upper().split()[0]
	else:
		return bet_element.text.upper()


def fill_db_with_quotes(leagues):   # DONE

	"""
	Download all the quotes from the website and save them in the database.

	:param leagues: list, leagues to download


	:return: nothing

	"""

	head = 'https://www.lottomatica.it/scommesse/avvenimenti/calcio/'

	browser = None
	for j, league in enumerate(leagues):
		start = time.time()
		browser = connect_to(head + countries[league], browser)

		# To close the popup. Only the first time after connection
		if not j:
			browser.refresh()

		league_id = dbf.db_select(
				table='leagues',
				columns_in=['league_id'],
		        where='league_name = "{}"'.format(league))[0]

		# We repeat this for loop for every match of the league. Value is set
		# to 100 to be sure to download all the matches. When no match is found
		# for the corresponding index, IndexError is handled
		for i in range(100):

			# If list of matches is not found, league is skipped
			matches_path = './/div[@class="block-event event-description"]'
			skip_league = all_matches_missing(browser, matches_path, league)
			if skip_league:
				break

			# We load the matches until we are sure we have all of them with no
			# repetitions. Sometimes we found in the db repeated matches
			while True:
				all_matches = browser.find_elements_by_xpath(matches_path)
				if len(all_matches) == len(set(all_matches)):
					break
				else:
					logger.info('FILL DB WITH QUOTES - Repeated matches found')

			# Select the match or continue to the next league if done
			try:
				match = all_matches[i]
			except IndexError:
				end = time.time() - start
				minutes = int(end // 60)
				seconds = round(end % 60)
				logger.info('FILL DB WITH QUOTES - Updating {} took {}:{}'.
				            format(league, minutes, seconds))
				break

			scroll_to_element(browser, match)

			# Extract date and time of the match and then click it
			ddmmyy, hhmm = match.find_element_by_xpath(
					'.//div[@class="event-date ng-binding"]').text.split(' - ')
			match.click()

			# Fill "matches" table in the db
			last_id, back = fill_matches_table(browser, league_id, ddmmyy, hhmm)

			# Fill "quotes" table in the db
			fill_quotes_table(browser, last_id)

			# Go back at the main page of the league
			scroll_to_element(browser, back)
			back.click()

	browser.quit()


def fill_matches_table(browser, league_id, d_m_y, h_m):   # DONE

	"""
	Insert all details relative to a single match into the 'matches' table of
	the db.
	Used inside fill_db_with_quotes().

	:param browser: selenium browser instance

	:param league_id: int

	:param d_m_y: str, date of the match. Ex 20/20/2018

	:param h_m: str, time of the match. Ex 15:00


	:return last_id: int, id of the match the will be used for the quotes
	:return back: button

	"""

	# Look for the back button
	back_path = './/a[@class="back-competition ng-scope"]'
	back = browser.find_element_by_xpath(back_path)
	scroll_to_element(browser, back)
	wait_clickable(browser, WAIT, back_path)

	# Extract the text with the two teams
	teams_cont = './/div[@class="event-name ng-binding"]'
	teams = None
	while not teams:
		teams = browser.find_element_by_xpath(teams_cont).text.upper()

	# Split them and add an '*' to their name if it is a Champions League match
	team1, team2 = teams.split(' - ')
	if league_id == 8:
		team1 = '*' + team1
		team2 = '*' + team2

	# Format datetime object
	dd, mm, yy = d_m_y.split('/')
	h, m = h_m.split(':')
	match_dt = bf.from_str_to_dt(
			'{}-{}-{} {}:{}:{}'.format(yy, mm, dd, h, m, 00))

	# Fix url to save
	# url = fix_url(browser.current_url)
	url = browser.current_url

	# We need the id of the match to update the quotes later
	last_id = dbf.db_insert(
			table='matches',
			columns=['match_league', 'match_team1', 'match_team2',
			         'match_date', 'match_url'],
			values=[league_id, team1, team2, match_dt, url],
			last_row=True)

	return last_id, back


# def fill_quotes_table(browser, last_id):   # DONE
#
# 	"""
# 	Insert the quotes in the database.
# 	Used inside fill_db_with_quotes().
#
# 	:param browser: selenium browser instance
#
# 	:param last_id: int, id of the match
#
#
# 	:return: nothing
#
# 	"""
#
# 	# Select all fields we want scrape
# 	all_fields = dbf.db_select(
# 			table='fields',
# 			columns_in=['field_name'])
#
# 	# Associate each field with its corresponding bets
# 	fields_bets = find_all_fields_and_bets(browser)
# 	for field, bets in fields_bets:
# 		scroll_to_element(browser, field)
#
# 		# If it is a field we have in the db we extract all the quotes
# 		field_name = field.text.upper()
# 		if field_name in all_fields:
# 			all_bets = bets.find_elements_by_xpath(
# 				'.//div[@class="selection-name ng-binding"]')
#
# 			for i, new_bet in enumerate(all_bets):
# 				scroll_to_element(browser, new_bet)
#
# 				# Bet name has a different path for the field 'ESITO FINALE 1X2
# 				# HANDICAP', don't know why
# 				if field_name == 'ESITO FINALE 1X2 HANDICAP':
# 					bet_name = new_bet.text.upper().split()[0]
# 				else:
# 					bet_name = new_bet.text.upper()
#
# 				# Extract quote value
# 				bet_quote = bets.find_elements_by_xpath(
# 								 './/div[@class="selection-price"]')[i]
# 				scroll_to_element(browser, bet_quote)
# 				bet_quote = bet_quote.text
#
# 				# Take corresponding field id from db
# 				field_id = dbf.db_select(
# 						table='fields',
# 						columns_in=['field_id'],
# 						where='field_name = "{}" AND field_value = "{}"'.
# 						format(field_name, bet_name))[0]
#
# 				# If quote is not available insert '-' in the db
# 				if len(bet_quote) == 1:
# 					bet_quote = '-'
# 				else:
# 					bet_quote = float(bet_quote)
#
# 				dbf.db_insert(
# 						table='quotes',
# 						columns=['quote_match', 'quote_field', 'quote_value'],
# 						values=[last_id, field_id, bet_quote])


def fill_quotes_table(browser, last_id):   # DONE

	"""
	Insert the quotes in the database.
	Used inside fill_db_with_quotes().

	:param browser: selenium browser instance

	:param last_id: int, id of the match


	:return: nothing

	"""

	# Select all fields we want scrape
	all_fields = dbf.db_select(
			table='fields',
			columns_in=['field_name'])

	# Associate each field with its corresponding bets
	fields_bets = find_all_fields_and_bets(browser)
	for field, bets in fields_bets:
		field_name = field.text.upper()

		while not field_name:
			scroll_to_element(browser, field)
			# time.sleep(3)
			field_name = field.text.upper()
			print('a')

		# If it is a field we have in the db we extract all the quotes
		if field_name in all_fields:
			all_bets = bets.find_elements_by_xpath(
				'.//div[@class="selection-name ng-binding"]')

			for i, new_bet in enumerate(all_bets):

				bet_name = extract_bet_name(field_name, new_bet)
				while not bet_name:
					scroll_to_element(browser, new_bet)
					# time.sleep(3)
					bet_name = extract_bet_name(field_name, new_bet)
					print('b')

				# Extract quote value
				bet_quote_el = bets.find_elements_by_xpath(
						'.//div[@class="selection-price"]')[i]
				bet_quote = bet_quote_el.text

				while not bet_quote:
					scroll_to_element(browser, bet_quote_el)
					# time.sleep(3)
					bet_quote = bet_quote_el.text
					print('c')
				# print(f'{field}___{bet_name}___{bet_quote}')

				# Take corresponding field id from db
				field_id = dbf.db_select(
						table='fields',
						columns_in=['field_id'],
						where='field_name = "{}" AND field_value = "{}"'.
						format(field_name, bet_name))[0]

				# If quote is not available insert '-' in the db
				if len(bet_quote) == 1:
					bet_quote = '-'
				else:
					bet_quote = float(bet_quote)

				dbf.db_insert(
						table='quotes',
						columns=['quote_match', 'quote_field', 'quote_value'],
						values=[last_id, field_id, bet_quote])


def fill_teams_table():

	# Delete old data from "teams"
	dbf.empty_table('teams')

	# Start the browser
	browser = webdriver.Chrome(chrome_path)
	head = 'https://www.lottomatica.it/scommesse/avvenimenti/calcio/'

	for league in countries:
		browser.get(head + countries[league])

		# To close the popup. Only the first time after connection
		if league == 'SERIE A':
			browser.refresh()

		league_id = dbf.db_select(
				table='leagues',
				columns_in=['league_id'],
				where='league_name = "{}"'.format(league))[0]

		matches_path = './/div[@class="event-name ng-binding"]'
		wait_clickable(browser, WAIT, matches_path)
		all_matches = browser.find_elements_by_xpath(matches_path)
		for match in all_matches:
			scroll_to_element(browser, match)
			teams = match.text.upper().split(' - ')
			for team in teams:
				dbf.db_insert(
						table='teams',
						columns=['team_league', 'team_name'],
						values=[league_id, team])

	browser.quit()

	dbf.empty_table('teams_short')

	teams = dbf.db_select(table='teams', columns_in=['team_name'])
	for team in teams:
		dbf.db_insert(
				table='teams_short',
				columns=['team_short_name', 'team_short_value'],
				values=[team, team[:3]])


def find_all_fields_and_bets(browser):

	"""
	Return the HTML container of the fields (ESITO FINALE 1X2, DOPPIA
	CHANCE, GOAL/NOGOAL, ...).
	"""

	all_panels = find_all_panels(browser)

	for i, panel in enumerate(all_panels):
		try:
			click_panel(browser, i, panel)
		except ConnectionError:
			continue

	all_fields_path = '//div[@class="market-info"]/div'
	all_bets_path = '//div[@class="market-selections"]'

	fields = browser.find_elements_by_xpath(all_fields_path)
	bets = browser.find_elements_by_xpath(all_bets_path)

	return zip(fields, bets)


def find_all_panels(browser):

	"""
	Return the HTML container of the panels (Più giocate, Combo, Casa, ...).
	Used inside click_bet() and find_all_fields_and_bets() functions.

	:param browser: selenium browser instance

	:return: selenium element

	"""

	all_panels_path = '//div[@class="item-group ng-scope"]'

	for i in range(recurs_lim):
		try:
			wait_visible(browser, WAIT, all_panels_path)
			all_panels = browser.find_elements_by_xpath(all_panels_path)
			return all_panels

		except TimeoutException:
			logger.info('FIND ALL PANELS - PANELS container not found: ' +
			            'trial {}.'.format(i + 1))
			if i < 2:
				browser.refresh()
				return find_all_panels(browser)
			else:
				browser.quit()


def click_scommetti(browser):   # DONE

	"""
	Click the button SCOMMETTI once logged in.
	Used inside command /play.

	:param browser: selenium browser instance


	:return: nothing

	"""

	button_location = './/div[@class="buttons-betslip"]'
	button = browser.find_element_by_xpath(button_location)
	scroll_to_element(browser, button)
	button.click()


# def fix_url(match_url):   # DONE
#
# 	"""
# 	Fix the url to make it work later in the /play command.
#
# 	:param match_url: str, url to fix
#
#
# 	:return: str, url fixed
#
# 	"""
#
# 	codes = {'seriea': 'seriea',
# 	         'premierleague': 'premierleague1',
# 	         'primeradivision': 'primeradivision1',
# 	         'bundesliga': 'bundesliga1',
# 	         'ligue1': 'ligue11',
# 	         'eredivisie': 'eredivisie1',
# 	         'championsleague': 'championsleague1'}
#
# 	for code in codes:
# 		if code in match_url:
# 			return match_url.replace(code, codes[code])


def go_to_lottomatica():

	"""Connect to Lottomatica webpage and click "CALCIO" button."""

	url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
		   'scommesse-sportive.html')

	# browser = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
	browser = webdriver.Chrome(chrome_path)
	time.sleep(3)

	browser.get(url)
	browser.refresh()  # To close the popup

	return browser


def go_to_personal_area(browser, LIMIT_1):

	"""
	Used in update_results() function to navigate until the personal area
	after the login.
	"""

	try:
		area_pers_path1 = './/a[@title="Profilo"]'
		wait_clickable(browser, 20, area_pers_path1)
		area_pers_button1 = browser.find_element_by_xpath(area_pers_path1)
		area_pers_button1.click()

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_1 < 3:
			logger.info('GO TO PERSONAL AREA - Unable to go to '
						'section: AREA PERSONALE.')
			browser.refresh()
			time.sleep(3)
			return go_to_personal_area(browser, LIMIT_1 + 1)
		else:
			raise ConnectionError('GO TO PERSONAL AREA - Unable to go to '
								  'section: AREA PERSONALE.')


def go_to_placed_bets(browser, LIMIT_2):

	"""
	Used in update_results() function to navigate until the page containing
	all the past bets.
	"""

	FILTER = 'Ultimi 5 Mesi'

	try:
		placed_bets_path = './/a[@title="Movimenti e giocate"]'
		wait_clickable(browser, 20, placed_bets_path)
		placed_bets_button = browser.find_element_by_xpath(placed_bets_path)
		placed_bets_button.click()
		time.sleep(5)

		date_filters_path = ('.//div[@id="movement-filters"]/' +
							 'div[@id="games-filter"]//' +
							 'label[@class="radio-inline"]')
		wait_visible(browser, 20, date_filters_path)
		date_filters_list = browser.find_elements_by_xpath(date_filters_path)
		for afilter in date_filters_list:
			new_filter = afilter.text
			if new_filter == FILTER:
				scroll_to_element(browser, afilter)
				afilter.click()
				break

		mostra_path = ('.//div[@class="btn-group btn-group-justified"]' +
					   '/a[@class="btn button-submit"]')
		wait_clickable(browser, 20, mostra_path)
		mostra_button = browser.find_element_by_xpath(mostra_path)
		scroll_to_element(browser, mostra_button)
		mostra_button.click()

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_2 < 3:
			logger.info('GO TO PLACED BETS - Unable to go to '
						'section: MOVIMENTI E GIOCATE.')
			browser.refresh()
			time.sleep(3)
			return go_to_placed_bets(browser, LIMIT_2 + 1)
		else:
			raise ConnectionError('GO TO PLACED BETS - Unable to go to '
								  'section: MOVIMENTI E GIOCATE.')


def insert_euros(browser, euros):   # DONE

	"""
	Fill the euros box in the website when playing the bet.
	Used inside /play.

	:param browser: selenium browser instance

	:param euros: int, amount to bet


	:return: nothing

	"""

	input_euros = ('.//div[@class="price-container-input"]/' +
	               'input[@ng-model="amountSelect.amount"]')
	euros_box = browser.find_element_by_xpath(input_euros)
	scroll_to_element(browser, euros_box)
	euros_box.send_keys(Keys.COMMAND, "a")
	euros_box.send_keys(Keys.LEFT)
	euros_box.send_keys(euros)
	euros_box.send_keys(Keys.DELETE)


def login(browser):   # DONE

	"""
	Make login by inserting username and password.
	Used inside /play.

	:param browser: selenium browser instance


	:return: nothing

	"""

	f = open('login.txt', 'r')
	credentials = f.readlines()
	f.close()

	username = credentials[0][10:-1]
	password = credentials[1][10:]

	try:
		# Click the login button
		button_path = './/button[@class="btn btn-default btn-accedi"]'
		button = browser.find_element_by_xpath(button_path)
		scroll_to_element(browser, button)
		wait_clickable(browser, WAIT, button_path)
		button.click()

		# Find the boxes to insert username and password
		user_path = './/input[@autocomplete="username"]'
		pass_path = './/input[@autocomplete="current-password"]'
		accedi_path = './/button[@id="signin-button"]'
		wait_visible(browser, WAIT, user_path)
		wait_visible(browser, WAIT, pass_path)
		user = browser.find_element_by_xpath(user_path)
		passw = browser.find_element_by_xpath(pass_path)

		# Insert username and password and login
		user.send_keys(username)
		passw.send_keys(password)
		wait_clickable(browser, WAIT, accedi_path)
		accedi = browser.find_element_by_xpath(accedi_path)
		accedi.click()
	except TimeoutException:
		browser.refresh()
		return login(browser)


def money(browser):

	"""Extract the text from the HTML element and return it as a float."""

	money_path = './/span[@class="user-balance ng-binding"]'


	for i in range(recurs_lim):
		try:
			wait_visible(browser, WAIT, money_path)
		except TimeoutException:
			logger.info('MONEY - Money container not found')
			if i < 2:
				browser.refresh()
				continue
			else:
				browser.quit()

	money = browser.find_element_by_xpath(money_path).text
	money = float(money.replace(',', '.'))

	return money


def refresh_money(browser):

	time.sleep(2)
	refresh_path = './/user-balance-refresh-btn'

	for i in range(recurs_lim):
		try:
			wait_clickable(browser, WAIT, refresh_path)
			break
		except TimeoutException:
			logger.info('REFRESH MONEY - Refresh money button not found')
			if i < 2:
				browser.refresh()
				continue
			else:
				browser.quit()

	refresh = browser.find_element_by_xpath(refresh_path)
	scroll_to_element(browser, refresh)
	refresh.click()


def scroll_to_element(browser, element, position='{block: "center"}'):

	"""
	If the argument of 'scrollIntoView' is 'true' the command scrolls
	the webpage positioning the element at the top of the window, if it
	is 'false' the element will be positioned at the bottom.
	"""

	browser.execute_script(
			f'return arguments[0].scrollIntoView({position});',
			element)


def simulate_hover_and_click(browser, element):

	"""Handles the cases when hover is needed before clicking."""

	try:
		webdriver.ActionChains(
				browser).move_to_element(element).click(element).perform()
	except MoveTargetOutOfBoundsException:
		raise ConnectionError(conn_err_message)


def wait_clickable(browser, seconds, element):

	"""
	Forces the script to wait for the element to be clickable before doing
	any other action.
	"""

	WebDriverWait(
			browser, seconds).until(EC.element_to_be_clickable(
					(By.XPATH, element)))


def wait_visible(browser, seconds, element):

	"""
	Forces the script to wait for the element to be visible before doing
	any other action.
	"""

	WebDriverWait(
			browser, seconds).until(EC.visibility_of_element_located(
					(By.XPATH, element)))
