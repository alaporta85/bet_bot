import db_functions as dbf
import selenium_functions as sf


def update_fields(url):

	brow = sf.open_browser()
	brow.get(url)
	brow.refresh()
	fields_in_db = dbf.db_select(table='fields',
	                             columns=['name'],
	                             where='')
	# TODO open_panels() changed
	sf.open_panels(brow)

	fields_bets = sf.all_fields_and_bets(brow)
	for field_name, bets in fields_bets:

		active = "{'active':selection.selected}"
		all_bets = bets.find_elements_by_xpath(
				f'.//div[@ng-class="{active}"]')
		for bet in all_bets:
			name = sf.extract_bet_name(bet)
			if f'{field_name}_{name}' in fields_in_db:
				dbf.db_update(table='fields',
				              columns=['found'],
				              values=['ACTIVE'],
				              where=f'name = "{field_name}_{name}"')

		inactive = "selection-disabled ng-scope"
		all_bets = bets.find_elements_by_xpath(
				f'.//div[@class="{inactive}"]')
		for bet in all_bets:
			name = sf.extract_bet_name(bet)
			if f'{field_name}_{name}' in fields_in_db:
				dbf.db_update(table='fields',
				              columns=['found'],
				              values=['INACTIVE'],
				              where=f'name = "{field_name}_{name}"')


URL = None
update_fields(URL)
