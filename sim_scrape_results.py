import utils as utl
import db_functions as dbf
import selenium_functions as sf

from selenium import webdriver


def click_expander(browser: webdriver, header: webdriver) -> None:
	exp_icon_path = './/div[contains(@class, "expander icon")]'
	exp_icon = header.find_element_by_xpath(exp_icon_path)
	sf.scroll_to_element(browser, exp_icon)
	exp_icon.click()


def close_all_headers(browser: webdriver) -> webdriver:

	top = active_top_headers(browser)
	notop = active_notop_headers(browser)

	for active_header in top + notop:
		click_expander(browser, active_header)


def active_notop_headers(browser: webdriver) -> list:
	headers_path = './/div[@class="event__header"]'
	return browser.find_elements_by_xpath(headers_path)


def active_top_headers(browser: webdriver) -> list:
	headers_path = './/div[@class="event__header top"]'
	return browser.find_elements_by_xpath(headers_path)


def correct_match_is_found(tm1_name: str, tm2_name: str) -> bool:

	ids = dbf.db_select(
			table='simulations',
			columns=['id'],
			where=(f'team1 = "{tm1_name}" AND team2 = "{tm2_name}" AND '
			       'label is NULL'))

	return True if ids else False


def get_matches(browser: webdriver) -> list:
	path = './/div[contains(@class, "event__match")]'
	return browser.find_elements_by_xpath(path)


def get_teams(header: webdriver, team1_name: str, team2_name: str) -> tuple:

	info = ': '.join(header.get_attribute('innerText').split('\n')[:2])
	league = info.split(': ')[1].upper()

	league = utl.fix_league_name(league_name=league)

	teams = dbf.db_select(table='teams',
	                      columns=['name'],
	                      where=f'league = "{league}"')

	tm1 = utl.jaccard_result(in_opt=team1_name, all_opt=teams, ngrm=2)
	tm2 = utl.jaccard_result(in_opt=team2_name, all_opt=teams, ngrm=2)

	return tm1, tm2


def goal_details(goals_tm1: str, goals_tm2: str, pt_info: str) -> tuple:

	ggtm1 = int(goals_tm1)
	ggtm2 = int(goals_tm2)
	ggtm1pt, ggtm2pt = pt_info[1:-1].split(' - ')
	ggtm1pt = int(ggtm1pt)
	ggtm2pt = int(ggtm2pt)
	ggtm1st = ggtm1 - ggtm1pt
	ggtm2st = ggtm2 - ggtm2pt

	return ggtm1pt, ggtm2pt, ggtm1st, ggtm2st


def league_is_correct(header: webdriver) -> bool:
	txt = ': '.join(header.get_attribute('innerText').split('\n')[:2])
	return txt in LEAGUES


def matches_info(match_elem: webdriver) -> list:
	info = match_elem.text
	try:
		status, tm1, ggtm1, _, ggtm2, tm2, pt = info.split('\n')
	except ValueError:
		return []

	if status != 'Finale':
		return []

	return [status, tm1, ggtm1, ggtm2, tm2, pt]


URL = 'https://www.diretta.it'
LEAGUES = ['ITALIA: Serie A', 'OLANDA: Eredivisie', 'GERMANIA: Bundesliga',
		   'SPAGNA: LaLiga', 'FRANCIA: Ligue1', 'INGHILTERRA: Premier League']

brow = sf.open_browser()
brow.get(URL)

close_all_headers(browser=brow)

for top_header in active_top_headers(browser=brow):

	if league_is_correct(header=top_header):
		click_expander(browser=brow, header=top_header)
		matches = get_matches(browser=brow)

		for match in matches:
			match_info = matches_info(match_elem=match)
			if not match_info:
				continue

			status, tm1, ggtm1, ggtm2, tm2, pt = match_info

			team1, team2 = get_teams(header=top_header,
			                         team1_name=tm1,
			                         team2_name=tm2)

			ggtm1pt, ggtm2pt, ggtm1st, ggtm2st = goal_details(goals_tm1=ggtm1,
			                                                  goals_tm2=ggtm2,
			                                                  pt_info=pt)

			if not correct_match_is_found(tm1_name=team1, tm2_name=team2):
				# TODO do something
				continue

			dbf.db_update(table='simulations',
			              columns=['goals_tm1_pt', 'goals_tm2_pt',
			                       'goals_tm1_st', 'goals_tm2_st'],
			              values=[ggtm1pt, ggtm2pt, ggtm1st, ggtm2st],
			              where=(f'team1 = "{team1}" AND team2 = "{team2}" AND'
			                     ' label is NULL'))

			click_expander(browser=brow, header=top_header)

brow.close()
