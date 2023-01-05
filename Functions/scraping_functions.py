import time
from datetime import datetime
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver

import db_functions as dbf
import config as cfg
import utils as utl


def deny_cookies(brow: webdriver) -> None:
	try:
		deny_path = './/button[@class="onetrust-close-btn-handler ' \
		            'banner-close-button ot-close-link"]'
		wait_clickable(brow=brow, element_path=deny_path)
		brow.find_element_by_xpath(deny_path).click()
	except TimeoutException:
		pass


def extract_all_bets_from_container(bets_container: webdriver) -> [webdriver]:
	return bets_container.find_elements_by_xpath('.//td')


def extract_bet_name(bet_element: webdriver) -> str:
	name = bet_element.find_elements_by_xpath('.//span')[0].text
	return name.strip()


def extract_bet_quote(bet_element: webdriver) -> float:
	quote = bet_element.find_elements_by_xpath('.//span')[1].text
	return float(quote.strip())


def extract_bet_info(bets_container: webdriver) -> [(str, float)]:

	all_bets = extract_all_bets_from_container(bets_container)

	names = [extract_bet_name(i) for i in all_bets]
	quotes = [extract_bet_quote(i) for i in all_bets]
	return list(zip(names, quotes))


def extract_match_datetime(match_obj: webdriver) -> datetime:

	data = match_obj.get_attribute('data-evndate')
	ddmmyy, hhmm = data.split()
	day, month, year = ddmmyy.split('-')
	hour, minute = hhmm.split(':')

	match_datetime = f'{year}-{month}-{day} {hour}:{minute}:00'

	return datetime.strptime(match_datetime, '%Y-%m-%d %H:%M:%S')


def extract_teams_names(brow: webdriver, league_name: str) -> (str, str):

	# Extract the text with the two teams
	teams_cont_path = './/span[@class="sport-title-dtl"]'
	wait_visible(brow=brow, element_path=teams_cont_path)
	teams_cont = brow.find_element_by_xpath(teams_cont_path)
	teams = teams_cont.text.upper()

	# Split them and add an '*' to their name if it is a Champions League match
	team1, team2 = teams.split(' - ')
	if league_name == 'CHAMPIONS LEAGUE':
		team1 = '*' + team1
		team2 = '*' + team2

	return team1.strip(), team2.strip()


def get_panels(brow: webdriver, specific_name: str) -> [webdriver]:
	# Filter panels
	panels = brow.find_elements_by_xpath(
			'.//ul[@class="sport nav nav-tabs"]//a')

	if not specific_name:
		return [p for p in panels if
		        p.get_attribute('innerText') in cfg.PANELS_TO_USE]
	return [p for p in panels if p.get_attribute('innerText') == specific_name]


def open_browser(url: str) -> webdriver:

	brow = webdriver.Chrome(cfg.CHROME_PATH)
	brow.set_window_size(1200, 850)
	time.sleep(3)

	brow.get(url)
	time.sleep(5)

	# Deny cookies
	deny_cookies(brow=brow)
	time.sleep(5)

	return brow


def scrape_all_quotes() -> None:

	"""
	Download all the quotes from the website and save them in the database.
	"""

	browser = None
	for league in cfg.LEAGUES:
		start = time.time()
		browser = scrape_league_quotes(brow=browser, league_name=league)
		m, s = utl.time_needed(start)
		cfg.LOGGER.info('FILL DB WITH QUOTES - '
		                f'{league} aggiornata: {m}:{s} mins')

	browser.quit()


def scrape_league_quotes(brow: webdriver, league_name: str) -> webdriver:

	# Open league url
	league_url = utl.get_league_url(league_name)
	if not brow:
		brow = open_browser(url=league_url)
	else:
		brow.get(league_url)
		time.sleep(5)

	path_to_click = './/li[@class="count-bet"]/a'
	for i in range(cfg.MATCHES_TO_SCRAPE):

		# Matches have to be retrieved at each iteration
		try:
			match = find_all_matches(brow=brow, league_name=league_name)[i]
		except IndexError:
			break

		# Double scroll_to_element, it doesn't work with just one
		scroll_to_element(brow, match)
		time.sleep(2)
		scroll_to_element(brow, match)
		time.sleep(2)
		wait_clickable(brow=brow, element_path=path_to_click)

		# Extract date and time info
		match_dt = extract_match_datetime(match)

		# If match is too far away go to next league. Since mathces are sorted
		# by time also following matches will be too far away
		if utl.match_is_out_of_range(match_dt):
			break

		# Go to match details
		match.find_element_by_xpath(path_to_click).click()
		time.sleep(5)

		# Fill "matches" table in the db
		last_id = insert_match(
				brow=brow,
				league_name=league_name,
				match_dt=match_dt
		)

		# Fill "quotes" table in the db
		insert_quotes(brow, last_id)
		brow.back()
		time.sleep(3)

	return brow


def insert_match(brow: webdriver, league_name: str, match_dt: datetime) -> int:

	"""
	Insert all details relative to a single match into the 'matches' table of
	the db.
	"""

	# Teams names
	team1, team2 = extract_teams_names(brow, league_name=league_name)

	# Remove old quotes of the same match
	utl.remove_existing_match_quotes(team_one=team1, team_two=team2)

	# Id of the match is used to associate quotes to the correct match
	last_id = dbf.db_insert(
			table='matches',
			columns=['league', 'team1', 'team2', 'date', 'url'],
			values=[league_name, team1, team2, match_dt, brow.current_url],
			last_index=True
	)

	return last_id


def insert_quotes(brow: webdriver, last_index: int) -> None:

	"""
	Insert the quotes in the database.
	"""

	# Panels
	panels = get_panels(brow=brow, specific_name='')

	# Associate each field with its corresponding bets
	values = []
	already_added = []
	for p in panels:

		p.click()
		time.sleep(3)

		p_name = p.get_attribute('innerText')
		fields_bets = all_fields_and_bets(brow=brow)
		for field_name, bets in fields_bets:
			all_bets = extract_bet_info(bets_container=bets)
			for bet_name, quote in all_bets:
				full_name = f'{field_name}_{bet_name}'
				if full_name in already_added:
					continue

				values.append((last_index, p_name, full_name, quote))
				already_added.append(full_name)

	dbf.db_insertmany(table='quotes',
	                  columns=['match', 'panel', 'bet', 'quote'],
	                  values=values)


def all_fields_and_bets(brow: webdriver) -> [(str, webdriver)]:

	# Select all fields we want to scrape
	fields_in_db = dbf.db_select(table='fields',
	                             columns=['name'],
	                             where='')

	fields_names = [f for i in fields_in_db for f, _ in (i.split('_'),)]
	fields_names = set(fields_names)

	all_fields_path = './/div[@class="accordion-title sport-heading"]'
	all_bets_path = './/div[@class="accordion-body"]'
	fields = brow.find_elements_by_xpath(all_fields_path)
	bets = brow.find_elements_by_xpath(all_bets_path)

	field_bets = []
	for field, bet_group in zip(fields, bets):
		field_name = field.get_attribute('innerText').upper().strip()
		if field_name in fields_names:
			field_bets.append((field_name, bet_group))

	return field_bets


def find_all_matches(brow: webdriver, league_name: str) -> [webdriver]:

	matches_path = './/tr[@data-evndate]'
	try:
		wait_clickable(brow, matches_path)
	except TimeoutException:
		cfg.LOGGER.info(f'Nessun match trovato per {league_name}.')
		return []

	return brow.find_elements_by_xpath(matches_path)


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


def wait_visible(brow: webdriver, element_path: str) -> None:

	"""
	Forces the script to wait for the element to be visible before doing
	any other action.
	"""

	WebDriverWait(brow,
	              cfg.WAIT).until(EC.visibility_of_element_located(
					(By.XPATH, element_path)))
