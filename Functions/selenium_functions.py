import os
import time
import datetime
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
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


countries = {
			 # 'SERIE A': 'ITALIA',
			 # 'PREMIER LEAGUE': 'INGHILTERRA',
			 # 'PRIMERA DIVISION': 'SPAGNA',
			 # 'BUNDESLIGA': 'GERMANIA',
			 # 'LIGUE 1': 'FRANCIA',
			 # 'EREDIVISIE': 'OLANDA',
			 # 'CHAMPIONS LEAGUE': 'EUROPA',
			 'MONDIALI': 'MONDO'
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

WAIT = 60


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


def scroll_to_element(browser, true_false, element):

	"""
	If the argument of 'scrollIntoView' is 'true' the command scrolls
	the webpage positioning the element at the top of the window, if it
	is 'false' the element will be positioned at the bottom.
	"""

	browser.execute_script('return arguments[0].scrollIntoView({});'
						   .format(true_false), element)


def simulate_hover_and_click(browser, element):

	"""Handles the cases when hover is needed before clicking."""

	try:
		webdriver.ActionChains(
				browser).move_to_element(element).click(element).perform()
	except MoveTargetOutOfBoundsException:
		raise ConnectionError(conn_err_message)


def click_calcio_button(browser):  # UPDATED

	calcio = './/div/div[@class="item-sport ng-scope"]//a'
	wait_clickable(browser, WAIT, calcio)
	calcio_button = browser.find_element_by_xpath(calcio)

	scroll_to_element(browser, 'true', calcio_button)
	scroll_to_element(browser, 'false', calcio_button)

	calcio_button.click()


def go_to_lottomatica(LIMIT_1):  # UPDATED

	"""Connect to Lottomatica webpage and click "CALCIO" button."""

	url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
		   'scommesse-sportive.html')

	# browser = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
	browser = webdriver.Chrome(chrome_path)
	time.sleep(3)
	browser.set_window_size(1400, 800)

	try:
		browser.get(url)
		click_calcio_button(browser)

		return browser

	except TimeoutException:

		if LIMIT_1 < 3:
			logger.info('Recursive go_to_lottomatica')
			browser.quit()
			return go_to_lottomatica(LIMIT_1 + 1)
		else:
			raise ConnectionError('Unable to reach Lottomatica webpage. ' +
								  'Please try again.')


def click_country_button(browser, league, LIMIT_COUNTRY_BUTTON):  # UPDATED

	"""
	Find the button relative to the country we are interested in and click it.
	"""

	current_url = browser.current_url

	countries_container = './/div[@class="country-name"]'
	try:
		wait_clickable(browser, WAIT, countries_container)
		all_countries = browser.find_elements_by_xpath(countries_container)

	except TimeoutException:
		if LIMIT_COUNTRY_BUTTON < 3:
			logger.info('Recursive click_country_button')
			browser.get(current_url)
			time.sleep(3)
			click_calcio_button(browser)
			return click_country_button(browser, league,
										LIMIT_COUNTRY_BUTTON + 1)
		else:
			browser.quit()
			raise ConnectionError(conn_err_message)

	for country in all_countries:
		panel = country.find_element_by_xpath('.//a')
		scroll_to_element(browser, 'false', panel)
		if panel.text.upper() == countries[league]:
			panel.click()
			time.sleep(2)
			break


def click_league_button(browser, league):  # UPDATED

	"""
	Find the button relative to the league we are interested in and click it.
	"""

	nat_leagues_container = ('.//div[@class="item-competition competition ' +
							 'slide-menu ng-scope"]')
	all_nat_leagues = browser.find_elements_by_xpath(nat_leagues_container)
	for nat_league in all_nat_leagues:
		panel = nat_league.find_element_by_xpath('.//a')
		scroll_to_element(browser, 'false', panel)
		if panel.text.upper() == league:
			panel.click()
			break


def find_all_panels(browser, LIMIT_ALL_PANELS):  # UPDATED

	"""
	Return the HTML container of the panels (PIU' GIOCATE, CHANCE MIX,
	TRICOMBO, ...).
	"""

	all_panels_path = ('//div[@class="item-group ng-scope"]/' +
					   'div[contains(@class, "group-name")]')
	current_url = browser.current_url

	try:
		wait_visible(browser, WAIT, all_panels_path)
		all_panels = browser.find_elements_by_xpath(all_panels_path)

	except TimeoutException:
		if LIMIT_ALL_PANELS < 3:
			logger.info('Recursive find_all_panels')
			browser.get(current_url)
			time.sleep(3)
			return find_all_panels(browser, LIMIT_ALL_PANELS + 1)
		else:
			browser.quit()
			raise ConnectionError(conn_err_message)

	return all_panels


def find_all_fields_and_bets(browser):  # UPDATED

	"""
	Return the HTML container of the fields (ESITO FINALE 1X2, DOPPIA
	CHANCE, GOAL/NOGOAL, ...).
	"""

	all_fields_path = '//div[@class="market-info"]/div'
	all_bets_path = '//div[@class="market-selections"]'

	fields = browser.find_elements_by_xpath(all_fields_path)
	bets = browser.find_elements_by_xpath(all_bets_path)

	return fields, bets


def click_bet(browser, field, bet, LIMIT_GET_QUOTE):

	"""
	Find the button relative to the bet we are interested in and click
	it.
	"""

	current_url = browser.current_url
	CLICK_CHECK = False

	try:
		all_panels = find_all_panels(browser, 0)

		for panel in all_panels:
			panel.click()
			all_fields = find_all_fields(browser)

			for new_field in all_fields:
				field_name = new_field.find_element_by_xpath(
						'.//div[@class="text-left col ng-binding"]').text

				if field_name == field:
					all_bets = find_all_bets(field, new_field)

					for new_bet in all_bets:
						bet_name = new_bet.find_element_by_xpath(
								'.//div[@class="sel-ls"]/a').text

						if bet_name == bet:

							bet_element_path = ('.//a[@ng-click="remCrt.' +
												'selectionClick(selection)"]')

							wait_clickable(browser, 20, bet_element_path)
							bet_element = new_bet.find_element_by_xpath(
									bet_element_path)

							CLICK_CHECK = True
							scroll_to_element(browser, 'true', bet_element)
							scroll_to_element(browser, 'false',
											  bet_element)
							simulate_hover_and_click(browser, bet_element)
							break

					if CLICK_CHECK:
						break

			if CLICK_CHECK:
				break

	except TimeoutException:

		if LIMIT_GET_QUOTE < 3:
			logger.info('Recursive click_bet')
			browser.get(current_url)
			time.sleep(3)
			click_bet(browser, field, bet, LIMIT_GET_QUOTE + 1)
		else:
			browser.quit()
			raise ConnectionError(conn_err_message)


def login(browser):

	f = open('login.txt', 'r')
	credentials = f.readlines()
	f.close()

	username = credentials[0][10:-1]
	password = credentials[1][10:]

	user_path = './/input[@placeholder="Username"]'
	pass_path = './/input[@placeholder="Password"]'
	button_path = './/button[@class="button-submit"]'

	user_list = browser.find_elements_by_xpath(user_path)
	pass_list = browser.find_elements_by_xpath(pass_path)
	button_list = browser.find_elements_by_xpath(button_path)

	for element in user_list:
		if element.is_displayed():
			element.send_keys(username)
			break

	for element in pass_list:
		if element.is_displayed():
			element.send_keys(password)
			break

	for element in button_list:
		if element.is_displayed():
			scroll_to_element(browser, 'false', element)
			element.click()
			break


def add_bet(browser, current_url, field, bet):

	"""
	Add the quote to the basket by taking directly the url of the bet.
	It is used inside the play_bet function.
	"""

	browser.get(current_url)
	time.sleep(3)

	try:
		click_bet(browser, field, bet, 0)
	except ConnectionError as e:
		raise ConnectionError(str(e))


def check_single_bet(browser, anumber, team1, team2):

	"""Check whether the bet is inserted correctly."""

	message = ('Problems with the match {} - {}. '.format(team1, team2) +
			   'Possible reason: bad internet connection. Please try again.')

	avv = './/div[@class="col-lg-4 col-md-4 col-sm-4 col-xs-4 text-right"]'

	try:
		current_number = int(browser.find_element_by_xpath(avv).text)

		if current_number != anumber + 1:
			browser.quit()
			raise ConnectionError(message)

	except NoSuchElementException:
		browser.quit()
		raise ConnectionError(message)


def insert_euros(browser, euros):

	input_euros = ('.//div[contains(@class,"text-right ' +
				   'amount-sign")]/input')
	euros_box = browser.find_element_by_xpath(input_euros)
	euros_box.send_keys(Keys.COMMAND, "a")
	euros_box.send_keys(Keys.LEFT)
	euros_box.send_keys(euros)
	euros_box.send_keys(Keys.DELETE)


	# win_path = ('.//div[@class="row ticket-bet-infos"]//' +
	# 			'p[@class="amount"]/strong')
	# win_container = browser.find_element_by_xpath(win_path)
	# sf.scroll_to_element(browser, 'false', win_container)
	#
	# possible_win_default = win_container.text[2:].replace(',', '.')
	#
	# # Manipulate the possible win's format to avoid errors
	# if len(possible_win_default.split('.')) == 2:
	# 	possible_win_default = float(possible_win_default)
	# else:
	# 	possible_win_default = float(''.join(
	# 			possible_win_default.split('.')[:-1]))
	# possible_win = round(possible_win_default * (euros/2), 2)
	#
	# return possible_win


def add_bet_to_basket(browser, match, count, dynamic_message):

	team1 = match[0]
	team2 = match[1]
	field = match[2]
	bet = match[3]
	url = match[4]

	try:
		add_bet(browser, url, field, bet)
		time.sleep(5)
		check_single_bet(browser, count, team1, team2)
		return dynamic_message.format(count + 1)

	except ConnectionError as e:
		raise ConnectionError(str(e))




def update_matches_table(browser, c, league_id, d_m_y, h_m):  # UPDATED

	back = './/a[@class="back-competition ng-scope"]'
	wait_clickable(browser, 30, back)
	back = browser.find_element_by_xpath(back)
	time.sleep(1)

	main = './/div[@class="event-name ng-binding"]'
	teams = browser.find_element_by_xpath(main).text.upper()

	team1, team2 = teams.split(' - ')
	if league_id == 8:
		team1 = '*' + team1
		team2 = '*' + team2

	dd, mm, yy = d_m_y.split('/')
	match_date = datetime.datetime.strptime(yy + mm + dd, '%Y%m%d')
	match_date = match_date.replace(hour=int(h_m.split(':')[0]),
									minute=int(h_m.split(':')[1]))
	time.sleep(4)
	c.execute('''INSERT INTO matches (match_league, match_team1, match_team2,
				 match_date, match_url) VALUES (?, ?, ?, ?, ?)
			  ''', (league_id, team1, team2, match_date, browser.current_url))

	last_id = c.lastrowid

	return last_id, back


def update_quotes_table(browser, db, c, all_fields, last_id):  # UPDATED

	all_panels = find_all_panels(browser, 0)

	for panel in all_panels:
		scroll_to_element(browser, 'false', panel)
		if 'active' not in panel.get_attribute('class'):
			panel.click()
			time.sleep(2)

	fields_bets = find_all_fields_and_bets(browser)

	for field, bets in zip(fields_bets[0], fields_bets[1]):
		scroll_to_element(browser, 'false', field)
		field_name = field.text.upper()

		if field_name in all_fields:
			all_bets = bets.find_elements_by_xpath(
				'.//div[@class="selection-name ng-binding"]')

			for i, new_bet in enumerate(all_bets):
				scroll_to_element(browser, 'false', new_bet)
				if field_name == 'ESITO FINALE 1X2 HANDICAP':
					bet_name = new_bet.text.upper().split()[0]
				else:
					bet_name = new_bet.text.upper()

				bet_quote = bets.find_elements_by_xpath(
								 './/div[@class="selection-price"]')[i]
				scroll_to_element(browser, 'false', bet_quote)
				bet_quote = bet_quote.text

				if len(bet_quote) == 1:
					bet_quote = '@LOCKED'
				else:
					bet_quote = float(bet_quote)

				field_id = list(c.execute(
						'''SELECT field_id from fields WHERE field_name = ? AND
						   field_value = ?''', (field_name, bet_name)))[0][0]

				c.execute(
						'''INSERT INTO quotes (quote_match, quote_field,
						   quote_value) VALUES (?, ?, ?)''',
						(last_id, field_id, bet_quote))
				db.commit()


def fill_db_with_quotes():  # UPDATED

	"""
	Call the function 'scan_league()' for all the leagues present in the
	dict "countries" to fully update the db.
	"""

	def three_buttons(browser, league):

		click_country_button(browser, league, 0)
		click_league_button(browser, league)
		# click_country_button(browser, league, 0)
		filters = './/div[@class="markets-favourites"]'

		return filters

	browser = go_to_lottomatica(0)
	dbf.empty_table('quotes')
	dbf.empty_table('matches')
	db, c = dbf.start_db()

	all_fields = list(c.execute('''SELECT field_name FROM fields'''))
	all_fields = [element[0] for element in all_fields]

	for league in countries:
		start = time.time()
		filters = three_buttons(browser, league)
		league_url = browser.current_url
		time.sleep(3)
		skip_league = False

		for i in range(3):
			try:
				wait_visible(browser, WAIT, filters)
				break
			except TimeoutException:
				if i < 2:
					logger.info('Recursive {}'.format(league))
					browser.get(league_url)
					time.sleep(3)
					continue
				else:
					logger.info('Failing to update quotes from {}'.format(
																	   league))
					skip_league = True

		if skip_league:
			continue

		c.execute('''SELECT league_id FROM leagues WHERE league_name = ? ''',
				  (league,))
		league_id = c.fetchone()[0]

		for i in range(500):
			try:
				buttons = './/div[@class="block-event event-description"]'

				WebDriverWait(
						browser, 30).until(EC.element_to_be_clickable(
												   (By.XPATH, buttons)))
				match = browser.find_elements_by_xpath(buttons)[i]
				scroll_to_element(browser, 'true', match)
				scroll_to_element(browser, 'false', match)
				ddmmyy, hhmm = match.find_element_by_xpath(
						'.//div[@class="event-date ng-binding"]').\
					text.split(' - ')
				match.click()
				last_id, back = update_matches_table(browser, c, league_id,
											   ddmmyy, hhmm)
				update_quotes_table(browser, db, c, all_fields, last_id)
				scroll_to_element(browser, 'false', back)
				back.click()
			except IndexError:
				end = time.time() - start
				minutes = int(end // 60)
				seconds = round(end % 60)
				logger.info('Updating {} took {}:{}'.format(league, minutes,
															seconds))
				break

	db.close()
	browser.quit()


def analyze_main_table(browser, ref_list, LIMIT_3):

	"""
	Used in update_results() function to drive the browser to the personal
	area in the 'MOVIMENTI E GIOCATE' section and call the function
	analyze_details_table for each bet not updated yet.
	"""

	current_url = browser.current_url
	bets_updated = 0

	try:
		table_path = './/table[@id="tabellaRisultatiTransazioni"]'
		wait_visible(browser, 20, table_path)
		bets_list = browser.find_elements_by_xpath(table_path +
												   '//tr[@class="ng-scope"]')

		db, c = dbf.start_db()

		for ref_bet in ref_list:
			ref_id = ref_bet[0]
			ref_date = ref_bet[1]
			year = str(ref_date)[:4]
			month = str(ref_date)[4:6]
			day = str(ref_date)[6:]
			ref_date = day + '/' + month + '/' + year

			for bet in bets_list:

				color = bet.find_element_by_xpath(
						'.//td[contains(@class,"state state")]')\
					.get_attribute('class')

				if 'blue' not in color:

					date = bet.find_element_by_xpath(
							'.//td[@class="ng-binding"]').text[:10]

					if date == ref_date:

						new_status = bet.find_element_by_xpath(
								'.//translate-label[@key-default=' +
								'"statement.state"]').text

						if new_status == 'Vincente':
							new_status = 'WINNING'
						elif new_status == 'Non Vincente':
							new_status = 'LOSING'

						main_window = browser.current_window_handle
						details = bet.find_element_by_xpath('.//a')
						scroll_to_element(browser, 'false', details)
						details.click()
						time.sleep(3)

						new_window = browser.window_handles[-1]
						browser.switch_to_window(new_window)

						bets_updated += analyze_details_table(browser, ref_id,
															  c, new_status, 0)

						browser.close()

						browser.switch_to_window(main_window)
						break
		db.commit()
		db.close()

		return bets_updated

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_3 < 3:
			logger.info('Recursive analyze_main_table')
			browser.get(current_url)
			time.sleep(3)
			return analyze_main_table(browser, ref_list, LIMIT_3 + 1)
		else:
			raise ConnectionError('Unable to find past bets. ' +
								  'Please try again.')


def analyze_details_table(browser, ref_id, c, new_status, LIMIT_4):

	"""
	Used in analyze_main_table function. It first checks if all the matches
	inside the bet are concluded. If yes, update the column bet_result in
	the table 'bet' and the columns 'pred_result' and pred_label in the
	table 'predictions' of the database.
	"""

	current_url = browser.current_url

	try:

		prize_table = ('//div[@class="col-md-5 col-lg-5 col-xs-5 ' +
					   'pull-right pull-down"]')
		prize_element = browser.find_elements_by_xpath(prize_table +
													   '//tr/td')[7]
		prize_value = float(prize_element.text[1:-1].replace(',', '.'))

		c.execute('''UPDATE bets SET bet_prize = ? WHERE bet_id = ?''',
				  (prize_value, ref_id))

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
			team1 = match.split(' - ')[0]
			team2 = match.split(' - ')[1]
			label_element = new_bet.find_element_by_xpath(
					'.//div[contains(@class,"ng-scope")]')
			label = label_element.get_attribute('ng-switch-when')
			quote = float(new_bet.find_element_by_xpath('.//td[10]').text)
			result = new_bet.find_element_by_xpath('.//td[11]').text

			c.execute('''SELECT pred_id FROM bets INNER JOIN predictions on
					  pred_bet = bet_id WHERE bet_id = ? AND
					  pred_team1 = ? AND pred_team2 = ?''', (ref_id, team1,
															 team2))

			match_id = c.fetchone()[0]

			c.execute('''UPDATE bets SET bet_result = ? WHERE
					  bet_id = ?''', (new_status, ref_id))

			c.execute('''UPDATE predictions SET pred_quote = ?,
					  pred_result = ?, pred_label = ? WHERE pred_id = ?''',
					  (quote, result, label, match_id))

		return 1

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_4 < 3:
			logger.info('Recursive analyze_details_table')
			browser.get(current_url)
			time.sleep(3)
			return analyze_details_table(browser, ref_id, c, LIMIT_4 + 1)
		else:
			raise ConnectionError('Unable to find past bets. ' +
								  'Please try again.')


def go_to_placed_bets(browser, LIMIT_2):

	"""
	Used in update_results() function to navigate until the page containing
	all the past bets.
	"""

	FILTER = 'Ultimi 5 Mesi'
	current_url = browser.current_url

	try:
		placed_bets_path = './/a[@id="pl-movimenti"]'
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
				scroll_to_element(browser, 'false', afilter)
				afilter.click()
				break

		mostra_path = ('.//div[@class="btn-group btn-group-justified"]' +
					   '/a[@class="btn button-submit"]')
		wait_clickable(browser, 20, mostra_path)
		mostra_button = browser.find_element_by_xpath(mostra_path)
		scroll_to_element(browser, 'false', mostra_button)
		mostra_button.click()

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_2 < 3:
			logger.info('Recursive go_to_placed_bets')
			browser.get(current_url)
			time.sleep(3)
			return go_to_placed_bets(browser, LIMIT_2 + 1)
		else:
			raise ConnectionError('Unable to go to the section: MOVIMENTI E' +
								  ' GIOCATE. Please try again.')


def go_to_personal_area(browser, LIMIT_1):

	"""
	Used in update_results() function to navigate until the personal area
	after the login.
	"""

	current_url = browser.current_url

	try:
		area_pers_path1 = './/a[@class="account-link theme-button"]'
		wait_clickable(browser, 20, area_pers_path1)
		area_pers_button1 = browser.find_element_by_xpath(area_pers_path1)
		area_pers_button1.click()

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_1 < 3:
			logger.info('Recursive go_to_personal_area')
			browser.get(current_url)
			time.sleep(3)
			return go_to_personal_area(browser, LIMIT_1 + 1)
		else:
			raise ConnectionError('Unable to go to the section: ' +
								  'AREA PERSONALE. Please try again.')


