import time
from itertools import count
from selenium.webdriver.common.keys import Keys
from selenium import webdriver

import db_functions as dbf
import config as cfg
import utils as utl
from scraping_functions import (
	scroll_to_element, wait_visible, wait_clickable, all_fields_and_bets,
	extract_all_bets_from_container, extract_bet_name, get_panels
)


def add_bet_to_basket(brow: webdriver, panel_name: str,
                      field_name: str, bet_name: str) -> webdriver:

	"""
	Click the bet button and add it to the basket.
	"""

	panel = get_panels(brow=brow, specific_name=panel_name)[0]
	panel.click()
	time.sleep(3)

	field_bets = all_fields_and_bets(brow=brow)

	bets_container = [b for f, b in field_bets if f == field_name][0]

	bets_group = extract_all_bets_from_container(bets_container=bets_container)
	for bet in bets_group:
		if extract_bet_name(bet_element=bet) == bet_name:
			scroll_to_element(brow, bet)
			bet.click()
			time.sleep(5)
			break

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


def refresh_money(brow: webdriver) -> None:

	refresh_path = './/user-balance-refresh-btn'

	wait_clickable(brow, refresh_path)
	refresh = brow.find_element_by_xpath(refresh_path)
	scroll_to_element(brow, refresh)
	refresh.click()


def place_bet(brow: webdriver) -> None:

	button_location = './/button[@id="widget-ticket-scommetti"]'
	button = brow.find_element_by_xpath(button_location)
	scroll_to_element(brow, button)
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


def get_budget(brow: webdriver) -> float:

	"""
	Extract the text from the HTML element and return it as a float.
	"""

	money_path = './/span[@class="saldo-tot"]'
	money_el = brow.find_element_by_xpath(money_path)

	money_value = None
	while not money_value:
		money_value = money_el.get_attribute('innerText')

	money_value = money_value.split()[0]
	return float(money_value.replace(',', '.'))
