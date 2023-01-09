import time
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

import db_functions as dbf
import config as cfg
from scraping_functions import (
	scroll_to_element, wait_visible, wait_clickable, all_fields_and_bets,
	extract_all_bets_from_container, extract_bet_name, get_panels
)


def add_bet_to_basket(brow: webdriver, panel_name: str,
                      field_name: str, bet_name: str) -> webdriver:

	# Go to the specific panel
	panel = get_panels(brow=brow, specific_name=panel_name)[0]
	panel.click()
	time.sleep(3)

	# Locate the right html element
	field_bets = all_fields_and_bets(brow=brow)
	bets_container = [b for f, b in field_bets if f == field_name][0]

	# Click the right bet
	bets_group = extract_all_bets_from_container(bets_container=bets_container)
	for bet in bets_group:
		if extract_bet_name(bet_element=bet) == bet_name:
			scroll_to_element(brow, bet)
			time.sleep(2)
			scroll_to_element(brow, bet)
			time.sleep(2)
			bet.click()
			time.sleep(5)
			break

	return brow


def cross_check_teams(all_matches: [webdriver], bet_id: int) -> list:
	"""
	Check whether the bet in the webpage is the same as the one to update.
	If all teams in the web bet are the same as the teams in the database bet
	than a list with all predictions is returned.
	"""

	# Teams found in the web bet
	teams_web = []

	# Predictions with al ldetails
	preds_details = []

	# Extract teams and details from web bet
	for match in all_matches:
		_, _, teams, _, pred, quote, result, _ = match.text.upper().split('\n')
		team1, team2 = teams.strip().split(' - ')
		quote = float(quote.replace(',', '.'))
		label = 'WINNING' if pred == result else 'LOSING'

		# Result has to be formatted after label definition
		result = result.replace('-', '+')

		teams_web.append(team1)
		teams_web.append(team2)
		preds_details.append((team1, team2, quote, result, label))
	teams_web.sort()

	# Extract teams from database bet
	teams_db = dbf.db_select(table='predictions',
							 columns=['team1', 'team2'],
							 where=f'bet_id = {bet_id}')
	teams_db = [t for i in teams_db for t in i]
	teams_db.sort()

	# Return details if the two bets match else an empty list
	if teams_web == teams_db:
		return preds_details
	else:
		return []


def update_database(brow: webdriver, bet_id: int) -> None:

	bets_path = './/div[contains(@class, "row body-cnt-storico")]'
	bets_list = brow.find_elements_by_xpath(bets_path)
	bets_list = filter_by_state(list_of_bets=bets_list)

	for bet in bets_list:

		scroll_to_element(brow=brow, element=bet)
		time.sleep(2)

		# Save main info
		bet_info = bet.text.upper().split('\n')

		# Click and wait
		bet.click()
		time.sleep(10)

		# Extract all predictions from website
		matches_path = './/div[@class="row dettaglioEvento "]'
		wait_visible(brow, matches_path)
		matches = brow.find_elements_by_xpath(matches_path)

		# Make sure it is the right bet
		preds = cross_check_teams(all_matches=matches, bet_id=bet_id)
		if not preds:
			brow.back()
			continue

		# Update predictions table
		for tm1, tm2, quote, result, label in preds:
			dbf.db_update(table='predictions',
						  columns=['quote', 'result', 'label'],
						  values=[quote, result, label],
						  where=(f'bet_id = {bet_id} AND ' +
						         f'team1 = "{tm1}" AND team2 = "{tm2}"'))

		# Update bets table
		prize = float(bet_info[6].replace(',', '.').replace(' €', ''))
		status = 'WINNING' if bet_info[3] == 'VINCENTE' else 'LOSING'
		dbf.db_update(table='bets',
					  columns=['prize', 'result'],
					  values=[prize, status],
					  where=f'id = {bet_id}')

		# Close bet
		close_path = './/h5/button[@class="close"]'
		brow.find_element_by_xpath(close_path).click()
		time.sleep(5)
		break


def filter_by_state(list_of_bets: list) -> [webdriver]:
	return [bet for bet in list_of_bets if
	        'Vincente' in bet.text or 'Perdente' in bet.text]


def place_bet(brow: webdriver) -> None:

	button_location = './/button[@id="widget-ticket-scommetti"]'
	button = brow.find_element_by_xpath(button_location)
	scroll_to_element(brow, button)
	time.sleep(2)
	button.click()
	time.sleep(10)


def open_profile_history(brow: webdriver) -> None:

	path = './/a[@id="listBet"]'
	wait_clickable(brow, path)
	brow.find_element_by_xpath(path).click()
	time.sleep(5)


def open_profile_options(brow: webdriver) -> None:

	path = './/i[@id="iconMenuDestra"]'
	wait_clickable(brow, path)
	brow.find_element_by_xpath(path).click()
	time.sleep(5)


def set_time_filter(brow: webdriver) -> None:

	# Click time option
	path = f'.//option[@value="{cfg.BETS_FILTER}"]'
	wait_clickable(brow, path)
	brow.find_element_by_xpath(path).click()
	time.sleep(2)

	# Update bet table
	path = './/button[@id="btn-formGiocate"]'
	wait_clickable(brow, path)
	brow.find_element_by_xpath(path).click()
	time.sleep(5)


def insert_euros(brow: webdriver, euros: int) -> None:

	"""
	Fill the euros box in the website when playing the bet.
	"""

	input_euros = './/input[@id="couponTotStake"]'
	wait_visible(brow=brow, element_path=input_euros)
	euros_box = brow.find_element_by_xpath(input_euros)
	scroll_to_element(brow, euros_box)

	euros_box.send_keys(3*Keys.ARROW_RIGHT)
	time.sleep(1)
	euros_box.send_keys(5*Keys.BACKSPACE)
	time.sleep(1)
	euros_box.send_keys(euros)
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
	button_path = './/button[@id="btnAccediHeader"]'
	button = brow.find_element_by_xpath(button_path)
	scroll_to_element(brow, button)
	wait_clickable(brow, button_path)
	button.click()

	# Find the boxes to insert username and password
	user_path = './/input[@id="username"]'
	pass_path = './/input[@id="password"]'
	accedi_path = './/div[@class="RegDivBtn"]/button'
	wait_visible(brow, user_path)
	wait_visible(brow, pass_path)
	user = brow.find_element_by_xpath(user_path)
	passw = brow.find_element_by_xpath(pass_path)

	# Insert username and password and login
	user.send_keys(username)
	passw.send_keys(password)
	wait_clickable(brow, accedi_path)
	brow.find_element_by_xpath(accedi_path).click()
	time.sleep(20)

	return brow


def get_budget_from_website(brow: webdriver) -> float:

	money_path = './/span[@class="saldo-tot"]'
	money_el = brow.find_element_by_xpath(money_path)

	money_value = None
	while not money_value:
		money_value = money_el.get_attribute('innerText')

	money_value = money_value.split()[0]
	return float(money_value.replace(',', '.'))
