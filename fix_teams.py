import re
import db_functions as dbf


def fill_teams_table():

	leagues = dbf.db_select(table='leagues', columns=['name'], where='')

	shorts = []
	for league in leagues:
		old_teams = dbf.db_select(
				table='teams',
				columns=['name'],
				where=f'league = "{league}"')
		old_teams = set(old_teams)

		new_teams = dbf.db_select(
				table='matches',
				columns=['team1', 'team2'],
				where=f'league = "{league}"')
		new_teams = [el for pair in new_teams for el in pair]
		new_teams = set(new_teams)

		if new_teams - old_teams:

			dbf.db_delete(table='teams', where=f'league = "{league}"')
			for team in new_teams:
				dbf.db_insert(
						table='teams',
						columns=['league', 'name'],
						values=[league, team])

				short = team.replace(' ', '')
				short = re.findall(r'[*A-Z]+', short)[0]
				short = short[:3] if league != 'CHAMPIONS LEAGUE' else short[:4]

				if short not in shorts:
					dbf.db_update(
							table='teams',
							columns=['short'],
							values=[short],
							where=f'name = "{team}"')
					shorts.append(short)

				else:
					dbf.db_update(
							table='teams',
							columns=['short'],
							values=['-'],
							where=f'name = "{team}"')


def check_manual_short_names():

	shorts = dbf.db_select(table='teams', columns=['short'], where='')

	for short in shorts:
		c = shorts.count(short)
		if c > 1:
			print(f'Check short name {short}')


# Run this function
# fill_teams_table()

# Check in db the short names and fix the ones that are NULL

# Then run the function below to double check
# check_manual_short_names()
