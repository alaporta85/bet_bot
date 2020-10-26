import time
from datetime import datetime
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from Functions import db_functions as dbf
import config as cfg
import utils as utl


def add_bet_to_basket(browser, details, count, dynamic_message):

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


def analyze_details_table(browser, ref_id, new_status):

	"""
	Used in analyze_main_table function. It first checks if all the matches
	inside the bet are concluded. If yes, update the column bet_result in
	the table 'bet' and the columns 'pred_result' and pred_label in the
	table 'predictions' of the database.

	"""

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
	wait_visible(browser, new_table_path)
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
		cfg.logger.info('Bet with id {} is still incomplete'.format(ref_id))
		return 0

	cfg.logger.info('Updating bet with id: {}'.format(ref_id))
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


def analyze_main_table(browser, ref_list):

	"""
	Used in update_results() function to drive the browser to the personal
	area in the 'MOVIMENTI E GIOCATE' section and call the function
	analyze_details_table for each bet not updated yet.
	"""

	bets_updated = 0

	table_path = './/table[@id="tabellaRisultatiTransazioni"]'
	wait_visible(browser, table_path)
	bets_list = browser.find_elements_by_xpath(table_path +
											   '//tr[@class="ng-scope"]')

	updated = []
	for ref_bet in ref_list:
		ref_id = ref_bet[0]
		details_db = dbf.db_select(
				table='predictions',
				columns_in=['pred_team1', 'pred_team2'],
				where='pred_bet = {}'.format(ref_id))
		ref_date = '/'.join(list(reversed(ref_bet[1][:10].split('-'))))

		for bet in bets_list:

			color = bet.find_element_by_xpath(
					'.//td[contains(@class,"state state")]')\
				.get_attribute('class')

			if 'blue' not in color:

				date = bet.find_element_by_xpath(
						'.//td[@class="ng-binding"]').text[:10]

				if date == ref_date and date in updated:
					updated.remove(date)
					continue

				elif date == ref_date and date not in updated:
					updated.append(date)

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
					wait_visible(browser, new_table_path)
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
														  new_status)

					browser.close()

					browser.switch_to_window(main_window)
					break


	return bets_updated


def click_bet(browser, field, bet):

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

	for panel in all_panels:

		# Open the panel if closed
		click_panel(browser, panel)

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


def extract_bet_name(bet_element: webdriver) -> str:

	name_element = bet_element.find_element_by_xpath(
			'.//div[@class="selection-name ng-binding"]')
	name = name_element.get_attribute('innerText').upper().split('(')[0]
	return name


def extract_bet_quote(bet_element: webdriver) -> float:

	quote_element = bet_element.find_element_by_xpath(
					'.//div[@class="selection-price"]')
	quote = quote_element.get_attribute('innerText').upper()

	return float(quote)


def extract_bet_info(bets_container: webdriver) -> [(str, float)]:

	bets_ngclass = "{'active':selection.selected}"
	all_bets = bets_container.find_elements_by_xpath(
			f'.//div[@ng-class="{bets_ngclass}"]')
	info = []
	for bet in all_bets:
		name = extract_bet_name(bet)
		quote = extract_bet_quote(bet)
		info.append((name, quote))

	return info


def extract_match_datetime(brow: webdriver,
                           match_obj: webdriver) -> datetime:

	scroll_to_element(brow, match_obj)

	data = match_obj.find_element_by_xpath(
			'.//div[@class="event-date ng-binding"]').text
	ddmmyy, hhmm = data.split(' - ')
	day, month, year = ddmmyy.split('/')
	hour, minute = hhmm.split(':')

	match_datetime = f'{year}-{month}-{day} {hour}:{minute}:00'

	return datetime.strptime(match_datetime, '%Y-%m-%d %H:%M:%S')


def extract_teams_names(brow: webdriver, league_name: str) -> (str, str):

	# Extract the text with the two teams
	teams_cont = './/div[@class="event-name ng-binding"]'
	teams = None
	while not teams:
		teams = brow.find_element_by_xpath(teams_cont).text.upper()

	# Split them and add an '*' to their name if it is a Champions League match
	team1, team2 = teams.split(' - ')
	if league_name == 'CHAMPIONS LEAGUE':
		team1 = '*' + team1
		team2 = '*' + team2

	return team1, team2


def open_browser() -> webdriver:

	brow = webdriver.Chrome(cfg.chrome_path)
	brow.set_window_size(1200, 850)
	time.sleep(3)
	return brow


def scrape_all_quotes() -> None:

	"""
	Download all the quotes from the website and save them in the database.
	"""

	browser = None
	leagues = dbf.db_select(table='leagues', columns=['name'], where='')
	for league in leagues:
		start = time.time()
		browser = scrape_league_quotes(brow=browser, league_name=league)
		time_needed(start, league)

	browser.quit()


# TODO try decorator
def scrape_league_quotes(brow: webdriver, league_name: str) -> webdriver:

	if not brow:
		brow = open_browser()
	brow.get(utl.get_league_url(league_name))

	for i in range(cfg.MATCHES_TO_SCRAPE):
		matches = find_all_matches(brow=brow, league_name=league_name)

		# Select the match or continue to the next league if done
		try:
			match = matches[i]
		except IndexError:
			break

		match_dt = extract_match_datetime(brow, match)
		if match_is_out_of_range(match_dt):
			break
		else:
			match.click()

		# Fill "matches" table in the db
		last_id = insert_match(brow=brow,
		                       league_name=league_name,
		                       match_dt=match_dt)

		# Fill "quotes" table in the db
		insert_quotes(brow, last_id)

		return_to_league_page(brow=brow)

	return brow


def insert_match(brow: webdriver, league_name: str,
                 match_dt: datetime) -> int:

	"""
	Insert all details relative to a single match into the 'matches' table of
	the db.
	"""

	team1, team2 = extract_teams_names(brow, league_name=league_name)

	remove_existing_match_quotes(team_one=team1, team_two=team2)

	# We need the id of the match to update the quotes later
	last_id = dbf.db_insert(
			table='matches',
			columns=['league', 'team1', 'team2', 'date', 'url'],
			values=[league_name, team1, team2, match_dt, brow.current_url],
			last_index=True)

	return last_id


def insert_quotes(brow: webdriver, last_index: int) -> None:

	"""
	Insert the quotes in the database.
	"""

	# Select all fields we want to scrape
	fields_in_db = dbf.db_select(table='fields',
	                             columns=['id', 'name'],
	                             where='')

	open_panels(brow)

	# Associate each field with its corresponding bets
	fields_bets = all_fields_and_bets(brow, fields_in_db)
	for field_name, bets in fields_bets:

		all_bets = extract_bet_info(bets_container=bets)

		for bet_name, quote in all_bets:

			dbf.db_insert(
					table='quotes',
					columns=['match', 'bet', 'quote'],
					values=[last_index, f'{field_name}_{bet_name}', quote])


def all_fields_and_bets(brow: webdriver,
                        fields_to_scrape: list) -> [(str, webdriver)]:

	fields_names = [f for i in fields_to_scrape for f, _ in (i[1].split('_'),)]
	fields_names = set(fields_names)

	all_fields_path = '//div[@class="market-info"]/div'
	all_bets_path = '//div[@class="market-selections"]'
	fields = brow.find_elements_by_xpath(all_fields_path)
	bets = brow.find_elements_by_xpath(all_bets_path)

	field_bets = []
	for field, bet_group in zip(fields, bets):
		field_name = field.get_attribute('innerText').upper()
		if field_name in fields_names:
			field_bets.append((field_name, bet_group))

	return field_bets


def find_all_matches(brow: webdriver, league_name: str) -> [webdriver]:

	matches_path = './/div[@class="block-event event-description"]'
	try:
		wait_clickable(brow, matches_path)
	except TimeoutException:
		cfg.logger.info('ALL MATCHES MISSING - MATCHES ' +
		                f'for {league_name} missing.')
		return []

	return brow.find_elements_by_xpath(matches_path)


def open_panels(brow: webdriver) -> None:

	all_panels_path = '//div[@class="item-group ng-scope"]'
	wait_visible(brow, all_panels_path)
	all_panels = brow.find_elements_by_xpath(all_panels_path)

	panel_name_path = './/div[contains(@class, "group-name")]'
	for panel in all_panels:
		button = panel.find_element_by_xpath(panel_name_path)
		scroll_to_element(brow, button)
		panel_name = button.text

		if panel_name.strip().lower() not in cfg.PANELS_TO_USE:
			continue

		WebDriverWait(
				brow, cfg.WAIT).until(
				EC.element_to_be_clickable((By.LINK_TEXT, panel_name)))
		if 'active' not in button.get_attribute('class'):
			button.find_element_by_xpath('.//a').click()
			time.sleep(1)


def return_to_league_page(brow: webdriver) -> None:

	back_path = './/a[@class="back-competition ng-scope"]'
	back = brow.find_element_by_xpath(back_path)
	scroll_to_element(brow, back)
	wait_clickable(brow, back_path)
	back.click()


def click_scommetti(browser):

	"""
	Click the button SCOMMETTI once logged in.
	Used inside command /play.

	:param browser: selenium browser instance


	:return: nothing

	"""

	button_location = './/div[@class="buttons-betslip"]'
	button = browser.find_element_by_xpath(button_location)
	scroll_to_element(browser, button)
	time.sleep(10)
	button.click()
	time.sleep(20)


def go_to_personal_area(browser):

	"""
	Used in update_results() function to navigate until the personal area
	after the login.
	"""

	try:
		area_pers_path1 = './/a[@title="Profilo"]'
		wait_clickable(browser, area_pers_path1)
		area_pers_button1 = browser.find_element_by_xpath(area_pers_path1)
		area_pers_button1.click()

	except (TimeoutException, ElementNotInteractableException):

		cfg.logger.info('GO TO PERSONAL AREA - Unable to go to '
		                'section: AREA PERSONALE.')
		browser.refresh()
		time.sleep(3)
		return go_to_personal_area(browser)


def go_to_placed_bets(browser, LIMIT_2):

	"""
	Used in update_results() function to navigate until the page containing
	all the past bets.
	"""

	FILTER = 'Ultimi 3 Mesi'

	try:
		placed_bets_path = './/a[@title="Movimenti e giocate"]'
		wait_clickable(browser, placed_bets_path)
		placed_bets_button = browser.find_element_by_xpath(placed_bets_path)
		placed_bets_button.click()
		time.sleep(5)

		date_filters_path = ('.//div[@id="movement-filters"]/' +
							 'div[@id="games-filter"]//' +
							 'label[@class="radio-inline"]')
		wait_visible(browser, date_filters_path)
		date_filters_list = browser.find_elements_by_xpath(date_filters_path)
		for afilter in date_filters_list:
			new_filter = afilter.text
			if new_filter == FILTER:
				scroll_to_element(browser, afilter)
				afilter.click()
				break

		mostra_path = ('.//div[@class="btn-group btn-group-justified"]' +
					   '/a[@class="btn button-submit"]')
		wait_clickable(browser, mostra_path)
		mostra_button = browser.find_element_by_xpath(mostra_path)
		scroll_to_element(browser, mostra_button)
		mostra_button.click()

	except (TimeoutException, ElementNotInteractableException):

		if LIMIT_2 < 3:
			cfg.logger.info('GO TO PLACED BETS - Unable to go to '
			                'section: MOVIMENTI E GIOCATE.')
			browser.refresh()
			time.sleep(3)
			return go_to_placed_bets(browser, LIMIT_2 + 1)
		else:
			raise ConnectionError('GO TO PLACED BETS - Unable to go to '
								  'section: MOVIMENTI E GIOCATE.')


def insert_euros(brow: webdriver, euros: int) -> None:

	"""
	Fill the euros box in the website when playing the bet.
	"""

	input_euros = ('.//div[@class="price-container-input"]/' +
	               'input[@ng-model="amountSelect.amount"]')
	euros_box = brow.find_element_by_xpath(input_euros)
	scroll_to_element(brow, euros_box)
	euros_box.send_keys(Keys.COMMAND, "a")
	euros_box.send_keys(Keys.LEFT)
	euros_box.send_keys(euros)
	euros_box.send_keys(Keys.DELETE)


def login(brow: webdriver) -> webdriver:

	"""
	Make login by inserting username and password.
	"""

	f = open('login.txt', 'r')
	credentials = f.readlines()
	f.close()

	username = credentials[0][10:-1]
	password = credentials[1][10:]

	try:

		# Click the login button
		button_path = './/button[@class="btn btn-default btn-accedi"]'
		button = brow.find_element_by_xpath(button_path)
		scroll_to_element(brow, button)
		wait_clickable(brow, button_path)
		button.click()

		# Find the boxes to insert username and password
		user_path = './/input[@autocomplete="username"]'
		pass_path = './/input[@autocomplete="current-password"]'
		accedi_path = './/button[@id="signin-button"]'
		wait_visible(brow, user_path)
		wait_visible(brow, pass_path)
		user = brow.find_element_by_xpath(user_path)
		passw = brow.find_element_by_xpath(pass_path)

		# Insert username and password and login
		user.send_keys(username)
		passw.send_keys(password)
		wait_clickable(brow, accedi_path)
		accedi = brow.find_element_by_xpath(accedi_path)
		accedi.click()
		time.sleep(20)

		return brow
	except TimeoutException:
		brow.refresh()
		return login(brow)


def match_is_out_of_range(match_date: datetime) -> bool:

	today = datetime.now()
	days_diff = (match_date - today).days
	return True if days_diff > cfg.DAYS_RANGE else False


def money(browser):

	"""
	Extract the text from the HTML element and return it as a float.
	"""

	money_path = './/span[@class="user-balance ng-binding"]'
	money_el = browser.find_element_by_xpath(money_path)

	money = None
	while not money:
		money = money_el.get_attribute('innerText')

	return float(money.replace(',', '.'))


def remove_existing_match_quotes(team_one: str, team_two: str) -> None:

	match_ids = dbf.db_select(
			table='matches',
			columns=['id'],
			where=f'team1 = "{team_one}" OR team2 = "{team_two}"')
	if match_ids:
		for m_id in match_ids:
			dbf.db_delete(table='matches', where=f'id = {m_id}')
			dbf.db_delete(table='quotes', where=f'match = {m_id}')


def scroll_to_element(brow: webdriver, element: webdriver,
                      position='{block: "center"}') -> None:

	"""
	If the argument of 'scrollIntoView' is 'true' the command scrolls
	the webpage positioning the element at the top of the window, if it
	is 'false' the element will be positioned at the bottom.
	"""

	script = f'return arguments[0].scrollIntoView({position});'
	brow.execute_script(script, element)


def time_needed(start, league):

	end = time.time() - start
	m = int(end // 60)
	s = round(end % 60)
	cfg.logger.info(f'FILL DB WITH QUOTES - {league} updated: {m}:{s}')


def wait_clickable(brow: webdriver, element_path: str) -> None:

	"""
	Forces the script to wait for the element to be clickable before doing
	any other action.
	"""

	WebDriverWait(brow,
	              cfg.WAIT).until(EC.element_to_be_clickable(
					(By.XPATH, element_path)))


def wait_visible(brow: webdriver, element: webdriver) -> None:

	"""
	Forces the script to wait for the element to be visible before doing
	any other action.
	"""

	WebDriverWait(brow,
	              cfg.WAIT).until(EC.visibility_of_element_located(
					(By.XPATH, element)))
