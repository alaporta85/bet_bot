import time
from datetime import datetime
from itertools import count
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

import config
from Functions import db_functions as dbf
import config as cfg
import utils as utl


def add_bet_to_basket(brow: webdriver, panel_name: str,
                      field_name: str, bet_name: str) -> webdriver:

	"""
	Click the bet button and add it to the basket.
	"""

	_, panel = open_panels(brow=brow, specific_panel=panel_name)[0]

	field_bets = all_fields_and_bets(panel=panel)

	bets_container = [b for f, b in field_bets if f == field_name][0]

	bets_group = extract_all_bets_from_container(bets_container=bets_container)
	for bet in bets_group:
		if extract_bet_name(bet_element=bet) == bet_name:
			scroll_to_element(brow, bet)
			time.sleep(2)
			bet.click()
			time.sleep(5)

	return brow


def get_bet_status(bet: webdriver) -> str:

	text = bet.find_elements_by_xpath('.//td')[2].text
	if text == 'Vincente':
		return 'WINNING'
	elif text == 'Non Vincente':
		return 'LOSING'
	else:
		return ''


def open_details(brow: webdriver, bet: webdriver) -> tuple:

	details = bet.find_element_by_xpath('.//a')
	scroll_to_element(brow, details)
	details.click()
	time.sleep(3)

	new_window = brow.window_handles[-1]
	brow.switch_to_window(new_window)
	time.sleep(1)

	return new_window, brow


def cross_check_teams(table: webdriver, bets_db: list) -> (int, tuple):

	preds_list = table.find_elements_by_xpath('.//tr[@class="ng-scope"]')
	teams_web = []
	preds_details = []
	for pred in preds_list:
		match = pred.find_element_by_xpath('.//td[6]').text
		team1, team2 = match.strip().split(' - ')
		quote = float(pred.find_element_by_xpath('.//td[10]').text)
		result = pred.find_element_by_xpath('.//td[11]').text
		label_element = pred.find_element_by_xpath(
				'.//div[contains(@class,"ng-scope")]')
		label = label_element.get_attribute('ng-switch-when')

		teams_web.append(team1)
		teams_web.append(team2)
		preds_details.append((team1, team2, quote, result, label))
	teams_web.sort()

	for bet_db_id, _ in bets_db:
		teams_db = dbf.db_select(table='predictions',
								 columns=['team1', 'team2'],
								 where=f'bet_id = {bet_db_id}')
		teams_db = [t for i in teams_db for t in i]
		teams_db.sort()
		if teams_web == teams_db:
			return bet_db_id, preds_details
		else:
			continue
	return 0, []


def get_prize(brow: webdriver) -> float:

	prize_table = ('//div[@class="col-md-5 col-lg-5 col-xs-5 ' +
				   'pull-right pull-down"]')

	prize_el = brow.find_elements_by_xpath(prize_table + '//tr/td')[7]
	prize_value = prize_el.text[:-1].replace('.', '').replace(',', '.')
	return float(prize_value)


def update_database(brow: webdriver, bets_to_update: list):

	bets_list = filter_by_color(brow)

	bets_list = filter_by_date(web_bets=bets_list, db_bets=bets_to_update)

	for bet in bets_list:

		status = get_bet_status(bet=bet)
		if not status:
			continue

		main_window = brow.current_window_handle
		new_window, brow = open_details(brow=brow, bet=bet)

		path = './/table[@class="bet-detail"]'
		wait_visible(brow, path)
		details = brow.find_element_by_xpath(path)

		bet_id, preds = cross_check_teams(table=details, bets_db=bets_to_update)
		if not bet_id:
			brow.close()
			brow.switch_to_window(main_window)
			continue

		for tm1, tm2, quote, result, label in preds:
			dbf.db_update(table='predictions',
						  columns=['quote', 'result', 'label'],
						  values=[quote, result, label],
						  where=(f'bet_id = {bet_id} AND ' +
						         f'team1 = "{tm1}" AND team2 = "{tm2}"'))

		prize = get_prize(brow=brow)
		dbf.db_update(table='bets',
					  columns=['prize', 'result'],
					  values=[prize, status],
					  where=f'id = {bet_id}')

		brow.close()
		brow.switch_to_window(main_window)


def extract_all_bets_from_container(bets_container: webdriver) -> [webdriver]:

	bets_ngclass = "{'active':selection.selected}"
	all_bets = bets_container.find_elements_by_xpath(
			f'.//div[@ng-class="{bets_ngclass}"]')

	return all_bets


def extract_bet_name(bet_element: webdriver) -> str:

	name_element = bet_element.find_element_by_xpath(
			'.//div[@class="selection-name ng-binding"]')
	name = name_element.get_attribute('innerText').upper()
	if '(' in name:
		name = name.split('(')[0]
	return name.strip()


def extract_bet_quote(bet_element: webdriver) -> float:

	quote_element = bet_element.find_element_by_xpath(
					'.//div[@class="selection-price"]')
	quote = quote_element.get_attribute('innerText').upper()

	return float(quote)


def extract_bet_info(bets_container: webdriver) -> [(str, float)]:

	all_bets = extract_all_bets_from_container(bets_container)

	# info = []
	# for bet in all_bets:
	# 	name = extract_bet_name(bet)
	# 	quote = extract_bet_quote(bet)
	# 	info.append((name, quote))
	# return info

	names = [extract_bet_name(i) for i in all_bets]
	quotes = [extract_bet_quote(i) for i in all_bets]
	return list(zip(names, quotes))


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

	return team1.strip(), team2.strip()


def filter_by_color(brow: webdriver) -> list:

	table_path = './/table[@id="tabellaRisultatiTransazioni"]'
	wait_visible(brow, table_path)
	bets_list = brow.find_elements_by_xpath(table_path +
	                                        '//tr[@class="ng-scope"]')

	color_path = './/td[contains(@class,"state state")]'
	filtered = []
	for bet in bets_list:
		c = bet.find_element_by_xpath(color_path).get_attribute('class')
		if 'blue' not in c:
			filtered.append(bet)

	return filtered


def filter_by_date(web_bets: [webdriver], db_bets: [tuple]) -> [webdriver]:

	db_dates = [utl.str_to_dt(d).date() for _, d in db_bets]

	filtered = []
	path = './/td[@class="ng-binding"]'
	for bet in web_bets:
		dt = bet.find_element_by_xpath(path).text[:10]
		dt = utl.str_to_dt(dt, '%d/%m/%Y').date()
		if dt in db_dates:
			filtered.append(bet)

	return filtered


def open_browser() -> webdriver:

	brow = webdriver.Chrome(cfg.CHROME_PATH)
	brow.set_window_size(1200, 850)
	time.sleep(3)
	return brow


def scrape_all_quotes() -> None:

	"""
	Download all the quotes from the website and save them in the database.
	"""

	browser = None
	# leagues = dbf.db_select(table='leagues', columns=['name'], where='')
	for league in cfg.LEAGUES:
		start = time.time()
		browser = scrape_league_quotes(brow=browser, league_name=league)
		m, s = utl.time_needed(start)
		cfg.LOGGER.info(f'FILL DB WITH QUOTES - {league} aggiornata: {m}:{s}')

	browser.quit()
	utl.remove_matches_without_quotes()


# TODO try decorator
def scrape_league_quotes(brow: webdriver, league_name: str) -> webdriver:

	if not brow:
		brow = open_browser()
	brow.get(utl.get_league_url(league_name))
	brow.refresh()
	time.sleep(5)

	for i in range(cfg.MATCHES_TO_SCRAPE):
		matches = find_all_matches(brow=brow, league_name=league_name)

		# Select the match or continue to the next league if done
		try:
			match = matches[i]
		except IndexError:
			break

		match_dt = extract_match_datetime(brow, match)
		if utl.match_is_out_of_range(match_dt):
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

	utl.remove_existing_match_quotes(team_one=team1, team_two=team2)

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

	panels = open_panels(brow=brow, specific_panel='')

	# Associate each field with its corresponding bets
	already_added = []
	for p_name, p in panels:
		fields_bets = all_fields_and_bets(p)
		for field_name, bets in fields_bets:
			all_bets = extract_bet_info(bets_container=bets)
			for bet_name, quote in all_bets:
				full_name = f'{field_name}_{bet_name}'
				if full_name in already_added:
					continue

				dbf.db_insert(
						table='quotes',
						columns=['match', 'panel', 'bet', 'quote'],
						values=[last_index, p_name, full_name, quote])
				already_added.append(full_name)


def all_fields_and_bets(panel: webdriver) -> [(str, webdriver)]:

	# Select all fields we want to scrape
	fields_in_db = dbf.db_select(table='fields',
	                             columns=['name'],
	                             where='')

	fields_names = [f for i in fields_in_db for f, _ in (i.split('_'),)]
	fields_names = set(fields_names)

	all_fields_path = './/div[@class="market-info"]/div'
	all_bets_path = './/div[@class="market-selections"]'
	fields = panel.find_elements_by_xpath(all_fields_path)
	bets = panel.find_elements_by_xpath(all_bets_path)

	field_bets = []
	for field, bet_group in zip(fields, bets):
		field_name = field.get_attribute('innerText').upper().strip()
		if field_name in fields_names:
			field_bets.append((field_name, bet_group))

	return field_bets


def find_all_matches(brow: webdriver, league_name: str) -> [webdriver]:

	matches_path = './/div[@class="block-event event-description"]'
	try:
		wait_clickable(brow, matches_path)
	except TimeoutException:
		cfg.LOGGER.info(f'Nessun match trovato per {league_name}.')
		return []

	return brow.find_elements_by_xpath(matches_path)


def get_money_after(brow: webdriver, before: float) -> float:

	after = get_budget(brow)

	# Verify money has the new value. If not, refresh the value and check again
	# up to N times
	c = count(1)
	while next(c) < 100 and after == before:
		refresh_money(brow)
		time.sleep(2)
		after = get_budget(brow)

	return after


def open_panels(brow: webdriver, specific_panel: str = '') -> list:

	all_panels_path = '//div[@class="item-group ng-scope"]'
	wait_visible(brow, all_panels_path)
	all_panels = brow.find_elements_by_xpath(all_panels_path)

	panel_name_path = './/div[contains(@class, "group-name")]'
	buttons = [p.find_element_by_xpath(panel_name_path) for p in all_panels]

	# When playing the bet only the right panel is opened
	if specific_panel:
		pairs = [(all_panels[x], buttons[x]) for x in range(len(buttons)) if
		         buttons[x].get_attribute('innerText').strip().lower() ==
		         specific_panel]

	# while when scraping quotes all the valid panels are opened
	else:
		pairs = [(all_panels[x], buttons[x]) for x in range(len(buttons)) if
		         buttons[x].get_attribute('innerText').strip().lower() in
		         cfg.PANELS_TO_USE]

	for _, b in pairs:
		scroll_to_element(brow, b)
		panel_name = b.text
		WebDriverWait(
				brow, cfg.WAIT).until(
				EC.element_to_be_clickable((By.LINK_TEXT, panel_name)))
		if 'active' not in b.get_attribute('class'):
			b.find_element_by_xpath('.//a').click()
			time.sleep(1)

	return [(b.get_attribute('innerText').strip().lower(), p) for p, b in pairs]


def refresh_money(brow: webdriver) -> None:

	refresh_path = './/user-balance-refresh-btn'

	wait_clickable(brow, refresh_path)
	refresh = brow.find_element_by_xpath(refresh_path)
	scroll_to_element(brow, refresh)
	refresh.click()


def return_to_league_page(brow: webdriver) -> None:

	back_path = './/a[@class="back-competition ng-scope"]'
	back = brow.find_element_by_xpath(back_path)
	scroll_to_element(brow, back)
	wait_clickable(brow, back_path)
	back.click()


def place_bet(brow: webdriver) -> None:

	button_location = './/div[@class="buttons-betslip"]'
	button = brow.find_element_by_xpath(button_location)
	scroll_to_element(brow, button)
	time.sleep(5)
	button.click()
	time.sleep(10)


def open_profile_history(brow: webdriver) -> None:

	path = './/a[@title="Movimenti e giocate"]'
	wait_clickable(brow, path)
	button = brow.find_element_by_xpath(path)
	button.click()
	time.sleep(5)


def open_profile_options(brow: webdriver) -> None:

	path = './/a[@title="Profilo"]'
	wait_clickable(brow, path)
	button = brow.find_element_by_xpath(path)
	button.click()
	time.sleep(5)


def set_time_filter(brow: webdriver) -> None:

	path = ('.//div[@id="movement-filters"]/div[@id="games-filter"]' +
	        '//label[@class="radio-inline"]')
	wait_visible(brow, path)

	all_filters = brow.find_elements_by_xpath(path)

	right_filter = [f for f in all_filters if
	                f.get_attribute('innerText').strip() == cfg.BETS_FILTER][0]
	scroll_to_element(brow, right_filter)
	right_filter.click()
	time.sleep(5)


def show_bets_history(brow: webdriver) -> None:

	path = ('.//div[@class="btn-group btn-group-justified"]' +
				   '/a[@class="btn button-submit"]')
	wait_clickable(brow, path)

	button = brow.find_element_by_xpath(path)
	scroll_to_element(brow, button)
	button.click()
	time.sleep(5)


def insert_euros(brow: webdriver, euros: int) -> None:

	"""
	Fill the euros box in the website when playing the bet.
	"""

	input_euros = ('.//div[@class="price-container-input"]/' +
	               'input[@ng-model="amountSelect.amount"]')
	time.sleep(3)
	euros_box = brow.find_element_by_xpath(input_euros)
	scroll_to_element(brow, euros_box)
	time.sleep(3)
	euros_box.send_keys(euros)
	time.sleep(1)
	euros_box.send_keys(Keys.ARROW_LEFT)
	time.sleep(1)
	euros_box.send_keys(Keys.BACKSPACE)
	time.sleep(1)


def login(brow: webdriver) -> webdriver:

	"""
	Make login by inserting username and password.
	"""

	with open('login.txt', 'r') as f:
		credentials = f.readlines()

	username = credentials[0][10:-1]
	password = credentials[1][10:]

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


def get_budget(brow: webdriver) -> float:

	"""
	Extract the text from the HTML element and return it as a float.
	"""

	money_path = './/span[@class="user-balance ng-binding"]'
	money_el = brow.find_element_by_xpath(money_path)

	money_value = None
	while not money_value:
		money_value = money_el.get_attribute('innerText')

	return float(money_value.replace(',', '.'))


def scroll_to_element(brow: webdriver, element: webdriver,
                      position='{block: "center"}') -> None:

	"""
	If the argument of 'scrollIntoView' is 'true' the command scrolls
	the webpage positioning the element at the top of the window, if it
	is 'false' the element will be positioned at the bottom.
	"""

	script = f'return arguments[0].scrollIntoView({position});'
	brow.execute_script(script, element)


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
