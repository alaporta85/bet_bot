import utils as utl
import db_functions as dbf
import selenium_functions as sf


URL = 'https://www.diretta.it'
LEAGUES = ['ITALIA: Serie A', 'OLANDA: Eredivisie', 'GERMANIA: Bundesliga',
		   'SPAGNA: LaLiga', 'FRANCIA: Ligue1', 'INGHILTERRA: Premier League']

brow = sf.open_browser()
brow.get(URL)

active_top_headers_path = './/div[@class="event__header top"]'
active_top_headers = brow.find_elements_by_xpath(active_top_headers_path)

active_notop_headers_path = './/div[@class="event__header"]'
active_notop_headers = brow.find_elements_by_xpath(active_notop_headers_path)

active_headers = active_top_headers + active_notop_headers
for active_header in active_headers:
	exp_icon_path = './/div[contains(@class, "expander icon")]'
	exp_icon = active_header.find_element_by_xpath(exp_icon_path)
	sf.scroll_to_element(brow, exp_icon)
	exp_icon.click()

for active_header in active_top_headers:
	txt = ': '.join(active_header.get_attribute('innerText').split('\n')[:2])
	if txt in LEAGUES:
		league = txt.split(': ')[1].upper()
		sf.scroll_to_element(brow, active_header)
		exp_icon_path = './/div[contains(@class, "expander icon")]'
		exp_icon = active_header.find_element_by_xpath(exp_icon_path)
		exp_icon.click()

		matches = brow.find_elements_by_xpath(
				'.//div[contains(@class, "event__match")]')
		for match in matches:
			info = match.text

			try:
				status, tm1, ggtm1, _, ggtm2, tm2, pt = info.split('\n')
			except ValueError:
				continue

			if status != 'Finale':
				continue

			ggtm1 = int(ggtm1)
			ggtm2 = int(ggtm2)
			ggtm1pt, ggtm2pt = pt[1:-1].split(' - ')
			ggtm1pt = int(ggtm1pt)
			ggtm2pt = int(ggtm2pt)
			ggtm1st = ggtm1 - ggtm1pt
			ggtm2st = ggtm2 - ggtm2pt

			league = utl.fix_league_name(league_name=league)

			teams = dbf.db_select(table='teams',
			                      columns=['name'],
			                      where=f'league = "{league}"')

			tm1 = utl.jaccard_result(in_opt=tm1, all_opt=teams, ngrm=2)
			tm2 = utl.jaccard_result(in_opt=tm2, all_opt=teams, ngrm=2)

			ids = dbf.db_select(
					table='simulations',
					columns=['id'],
					where=(f'team1 = "{tm1}" AND team2 = "{tm2}" AND '
					       'label is NULL'))
			if not ids:
				# TODO do something
				continue

			dbf.db_update(table='simulations',
			              columns=['goals_tm1_pt', 'goals_tm2_pt',
			                       'goals_tm1_st', 'goals_tm2_st'],
			              values=[ggtm1pt, ggtm2pt, ggtm1st, ggtm2st],
			              where=(f'team1 = "{tm1}" AND team2 = "{tm2}" AND '
			                     'label is NULL'))

			sf.scroll_to_element(brow, active_header)
			exp_icon = active_header.find_element_by_xpath(exp_icon_path)
			exp_icon.click()

			print()
