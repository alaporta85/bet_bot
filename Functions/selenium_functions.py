import os
import time
import datetime
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


countries = {
			 'SERIE A': 'italia/idivisionev3.html',
			 'PREMIER LEAGUE': 'inghilterra/premierleague1.html',
			 'PRIMERA DIVISION': 'spagna/primeradivision1.html',
			 'BUNDESLIGA': 'germania/bundesliga1.html',
			 'LIGUE 1': 'francia/ligue11.html',
			 'EREDIVISIE': 'olanda/eredivisie1.html',
			 'CHAMPIONS LEAGUE': 'europa/championsleague1.html',
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
recurs_lim = 3


def add_bet_to_basket(browser, match, count, dynamic_message):

	team1 = match[0]
	team2 = match[1]
	field = match[2]
	bet = match[3]
	url = match[4]

	try:
		browser.get(url)
		click_bet(browser, field, bet)
		time.sleep(5)
		check_single_bet(browser, count, team1, team2)
		return dynamic_message.format(count + 1)

	except ConnectionError as e:
		raise ConnectionError(str(e))


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
		prize_value = float(prize_element.text[1:-1].replace('.', '').
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
			team1 = match.split(' - ')[0]
			team2 = match.split(' - ')[1]
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

		for ref_bet in ref_list:
			ref_id = ref_bet[0]
			ref_date = '/'.join(list(reversed(ref_bet[1][:10].split('-'))))

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


def check_single_bet(browser, anumber, team1, team2):

	"""Check whether the bet is inserted correctly."""

	message = 'Problems with {} - {}. Try again.'.format(team1, team2)

	singola = browser.find_elements_by_xpath('.//div[@class="item-ticket"]')
	multipla = browser.find_elements_by_xpath(
									   './/div[@class="item-ticket ng-scope"]')

	if not singola and len(multipla) != anumber + 1:
		logger.info('CHECK SINGLE BET - ' + message)
		browser.quit()
		raise ConnectionError(message)


def click_bet(browser, field, bet):

	"""
	Find the button relative to the bet we are interested in and click
	it.
	"""

	CLICK_CHECK = False

	all_panels = find_all_panels(browser)

	for i, panel in enumerate(all_panels):

		click_panel(browser, i, panel)

		fields_path = ('./div[contains(@class, "group-market")]//' +
		               'div[@class="market-info"]/div')
		bets_path = ('./div[contains(@class, "group-market")]//' +
		             'div[@class="market-selections"]')

		fields = panel.find_elements_by_xpath(fields_path)
		bets = panel.find_elements_by_xpath(bets_path)

		fields_bets = (fields, bets)

		for field_, bets in zip(fields_bets[0], fields_bets[1]):
			scroll_to_element(browser, 'false', field_)
			field_name = field_.text.upper()

			if field_name == field:

				all_bets = bets.find_elements_by_xpath(
						'.//div[@ng-repeat="selection in prematchSingle' +
						'EventMarketSimple.market.sel"]')
				if not all_bets:
					all_bets = bets.find_elements_by_xpath(
							'.//div[@ng-repeat="selection in market.sel"]')

				for new_bet in all_bets:
					scroll_to_element(browser, 'false', new_bet)
					if field_name == 'ESITO FINALE 1X2 HANDICAP':
						bet_name = new_bet.find_element_by_xpath(
								'.//div[@class="selection-name ' +
								'ng-binding"]').text.upper().split()[0]
					else:
						bet_name = new_bet.find_element_by_xpath(
								'.//div[@class="selection-name ' +
								'ng-binding"]').text.upper()

					if bet_name == bet:

						new_bet.click()
						CLICK_CHECK = True
						break

			if CLICK_CHECK:
				break

		if CLICK_CHECK:
			break


def click_calcio_button(browser):

	calcio = './/div/div[@class="item-sport ng-scope"]//a'

	for i in range(recurs_lim):
		try:
			wait_clickable(browser, WAIT, calcio)

		except TimeoutException:
			logger.info('CLICK CALCIO BUTTON - CALCIO button not found: ' +
			            'trial {}'.format(i + 1))
			if i < 2:
				browser.refresh()
				continue
			else:
				browser.quit()

	calcio_button = browser.find_element_by_xpath(calcio)
	scroll_to_element(browser, 'true', calcio_button)
	scroll_to_element(browser, 'false', calcio_button)
	calcio_button.click()


def click_country_button(browser, league):

	"""
	Find the button relative to the country we are interested in and click it.
	"""

	countries_container = './/div[@class="country-name"]'

	for i in range(recurs_lim):
		try:
			wait_clickable(browser, WAIT, countries_container)
			break

		except TimeoutException:
			logger.info('CLICK COUNTRY BUTTON - ALL COUNTRIES container not ' +
			            'found: trial {}'.format(i + 1))
			if i < 2:
				browser.refresh()
				click_calcio_button(browser)
				continue
			else:
				browser.quit()

	all_countries = browser.find_elements_by_xpath(countries_container)
	first_container = all_countries[0]
	for country in all_countries:
		panel = country.find_element_by_xpath('.//a')
		scroll_to_element(browser, 'false', panel)
		if panel.text.upper() == countries[league]:
			scroll_to_element(browser, 'true', panel)
			panel.click()

			return panel, first_container


def click_league_button(browser, league):

	"""
	Find the button relative to the league we are interested in and click it.
	"""

	nat_leagues_container = ('.//div[@class="item-competition competition ' +
							 'slide-menu ng-scope"]')
	for i in range(recurs_lim):
		try:
			wait_visible(browser, WAIT, nat_leagues_container)
			break
		except TimeoutException:
			logger.info('CLICK LEAGUE BUTTON - ALL LEAGUES container not ' +
			            'found: trial {}'.format(i + 1))
			if i < 2:
				browser.refresh()
				click_calcio_button(browser)
				click_country_button(browser, league)
				continue
			else:
				browser.quit()

	all_nat_leagues = browser.find_elements_by_xpath(nat_leagues_container)
	for nat_league in all_nat_leagues:
		panel = nat_league.find_element_by_xpath('.//a')
		scroll_to_element(browser, 'false', panel)
		if panel.text.upper() == league:
			scroll_to_element(browser, 'true', panel)
			panel.click()
			break


def click_panel(browser, index, panel):

	button = panel.find_elements_by_xpath(
			'//div[contains(@class, "group-name")]')[index]
	scroll_to_element(browser, 'false', button)
	txt = button.text

	try:
		WebDriverWait(
				browser, WAIT).until(EC.element_to_be_clickable(
					(By.LINK_TEXT, txt)))
	except TimeoutException:
		logger.info('CLICK PANEL - Not possible to click on ' +
		            '{} panel'.format(txt))
		raise ConnectionError

	if 'active' not in button.get_attribute('class'):
		button.click()
		time.sleep(.5)


def fill_db_with_quotes():

	"""
	Call the function 'scan_league()' for all the leagues present in the
	dict "countries" to fully update the db.
	"""

	head = 'https://www.lottomatica.it/scommesse/avvenimenti/calcio/'

	browser = webdriver.Chrome(chrome_path)
	dbf.empty_table('quotes')
	dbf.empty_table('matches')

	all_fields = dbf.db_select(
			table='fields',
			columns_in=['field_name'])

	filters = './/div[@class="markets-favourites"]'

	for league in countries:
		url = head + countries[league]
		start = time.time()
		browser.get(url)
		if league == 'SERIE A':
			browser.refresh()  # To close the popup
		skip_league = False

		for i in range(recurs_lim):
			try:
				wait_visible(browser, WAIT, filters)
				break
			except TimeoutException:
				logger.info('FILL DB WITH QUOTES - FILTERS for ' +
				            '{} not found: trial {}.'.format(league, i + 1))
				if i < 2:
					browser.refresh()
					continue
				else:
					skip_league = True

		if skip_league:
			continue

		league_id = dbf.db_select(
				table='leagues',
				columns_in=['league_id'],
		        where='league_name = "{}"'.format(league))[0]

		for i in range(10):
			try:
				buttons = './/div[@class="block-event event-description"]'
				for j in range(recurs_lim):
					try:
						wait_clickable(browser, WAIT, buttons)
						break
					except TimeoutException:
						logger.info('FILL DB WITH QUOTES - MATCHES for ' +
						            '{} not found: trial {}.'.format(league,
						                                             j + 1))
						if j < 2:
							browser.refresh()
							continue
						else:
							skip_league = True

				if skip_league:
					break

				match = browser.find_elements_by_xpath(buttons)[i]
				scroll_to_element(browser, 'true', match)
				scroll_to_element(browser, 'false', match)
				ddmmyy, hhmm = match.find_element_by_xpath(
						'.//div[@class="event-date ng-binding"]').\
					text.split(' - ')
				match.click()
				last_id, back = update_matches_table(browser, league_id,
											         ddmmyy, hhmm)
				update_quotes_table(browser, all_fields, last_id)
				scroll_to_element(browser, 'false', back)
				back.click()
			except IndexError:
				end = time.time() - start
				minutes = int(end // 60)
				seconds = round(end % 60)
				logger.info('FILL DB WITH QUOTES - Updating {} took {}:{}'.
				            format(league, minutes, seconds))
				break

		if skip_league:
			continue

	browser.quit()


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

	return fields, bets


def find_all_panels(browser):

	"""
	Return the HTML container of the panels (PIU' GIOCATE, CHANCE MIX,
	TRICOMBO, ...).
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


def find_scommetti_box(browser):

	button_location = './/div[@class="buttons-betslip"]'
	button = browser.find_element_by_xpath(button_location)
	scroll_to_element(browser, 'false', button)
	button.click()


def fix_url(match_url):

	"""
	Fix the url to make it work later in the /play command.

	:param match_url: str, url to fix

	:return: str, url fixed
	"""

	codes = {'seriea': 'idivisionev3',
	         'premierleague': 'premierleague1',
	         'primeradivision': 'primeradivision1',
	         'bundesliga': 'bundesliga1',
	         'ligue1': 'ligue11',
	         'eredivisie': 'eredivisie1',
	         'championsleague': 'championsleague1'}

	for code in codes:
		if code in match_url:
			return match_url.replace(code, codes[code])


def go_to_lottomatica():

	"""Connect to Lottomatica webpage and click "CALCIO" button."""

	url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
		   'scommesse-sportive.html')

	# browser = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
	browser = webdriver.Chrome(chrome_path)
	time.sleep(3)

	browser.get(url)
	browser.refresh()  # To close the popup
	click_calcio_button(browser)

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
			logger.info('GO TO PLACED BETS - Unable to go to '
						'section: MOVIMENTI E GIOCATE.')
			browser.refresh()
			time.sleep(3)
			return go_to_placed_bets(browser, LIMIT_2 + 1)
		else:
			raise ConnectionError('GO TO PLACED BETS - Unable to go to '
								  'section: MOVIMENTI E GIOCATE.')


def insert_euros(browser, euros):

	input_euros = ('.//div[@class="price-container-input"]/' +
	               'input[@ng-model="amountSelect.amount"]')
	euros_box = browser.find_element_by_xpath(input_euros)
	scroll_to_element(browser, 'false', euros_box)
	euros_box.send_keys(Keys.COMMAND, "a")
	euros_box.send_keys(Keys.LEFT)
	euros_box.send_keys(euros)
	euros_box.send_keys(Keys.DELETE)


def login(browser):

	f = open('login.txt', 'r')
	credentials = f.readlines()
	f.close()

	username = credentials[0][10:-1]
	password = credentials[1][10:]

	try:
		button = './/button[@class="btn btn-default btn-accedi"]'
		wait_clickable(browser, WAIT, button)
		button = browser.find_element_by_xpath(button)
		scroll_to_element(browser, 'false', button)
		button.click()

		user_path = './/input[@autocomplete="username"]'
		pass_path = './/input[@autocomplete="current-password"]'
		accedi_path = './/button[@id="signin-button"]'
		wait_visible(browser, WAIT, user_path)
		wait_visible(browser, WAIT, pass_path)
		user = browser.find_element_by_xpath(user_path)
		passw = browser.find_element_by_xpath(pass_path)

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
	scroll_to_element(browser, 'false', refresh)
	refresh.click()


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


def update_matches_table(browser, league_id, d_m_y, h_m):

	back = './/a[@class="back-competition ng-scope"]'
	wait_clickable(browser, WAIT, back)
	back = browser.find_element_by_xpath(back)

	teams_cont = './/div[@class="event-name ng-binding"]'
	teams = ''
	while not teams:
		teams = browser.find_element_by_xpath(teams_cont).text.upper()

	team1, team2 = teams.split(' - ')
	team1 = dbf.jaccard_result(team1,
	                           dbf.db_select(
			                           table='teams',
			                           columns_in=['team_name']), 3)
	team2 = dbf.jaccard_result(team2,
	                           dbf.db_select(
			                           table='teams',
			                           columns_in=['team_name']), 3)
	if league_id == 8:
		team1 = '*' + team1
		team2 = '*' + team2

	dd, mm, yy = d_m_y.split('/')
	match_date = datetime.datetime.strptime(yy + mm + dd, '%Y%m%d')
	match_date = match_date.replace(hour=int(h_m.split(':')[0]),
									minute=int(h_m.split(':')[1]))
	url = fix_url(browser.current_url)

	last_id = dbf.db_insert(
			table='matches',
			columns=['match_league', 'match_team1', 'match_team2',
			         'match_date', 'match_url'],
			values=[league_id, team1, team2, match_date, url],
			last_row=True)

	return last_id, back


def update_quotes_table(browser, all_fields, last_id):

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

				field_id = dbf.db_select(
						table='fields',
						columns_in=['field_id'],
						where='field_name = "{}" AND field_value = "{}"'.
						format(field_name, bet_name))[0]

				if len(bet_quote) == 1:
					bet_quote = 'NOT AVAILABLE'
				else:
					bet_quote = float(bet_quote)

				dbf.db_insert(
						table='quotes',
						columns=['quote_match', 'quote_field', 'quote_value'],
						values=[last_id, field_id, bet_quote])


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
