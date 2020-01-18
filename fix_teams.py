from Functions import db_functions as dbf


def fill_teams_table():
	import re

	leagues = dbf.db_select(table='leagues', columns_in=['league_id'])

	dbf.empty_table(table='teams_short')
	teams = []
	shorts = []

	for league in leagues:
		old_teams = dbf.db_select(
				table='teams',
				columns_in=['team_name'],
				where=f'team_league={league}')
		old_teams = set(old_teams)

		new_teams = dbf.db_select(
				table='matches',
				columns_in=['match_team1', 'match_team2'],
				where=f'match_league = {league}')
		new_teams = [el for pair in new_teams for el in pair]
		new_teams = set(new_teams)

		if new_teams - old_teams:

			dbf.db_delete(table='teams', where=f'team_league = {league}')
			for team in new_teams:
				dbf.db_insert(
						table='teams',
						columns=['team_league', 'team_name'],
						values=[league, team])

				short = team.replace(' ', '')
				short = re.findall(r'[*A-Z]+', short)[0]
				short = short[:3] if league != 8 else short[:4]

				if short not in shorts:
					dbf.db_insert(
							table='teams_short',
							columns=['team_short_league', 'team_short_name',
							         'team_short_value'],
							values=[league, team, short])
					teams.append(team)
					shorts.append(short)

				else:
					dbf.db_insert(
							table='teams_short',
							columns=['team_short_league', 'team_short_name'],
							values=[league, team])
					teams.append(team)
					print(f'Team {team} needs short name')


def check_manual_short_names():

	shorts = dbf.db_select(
				table='teams_short',
				columns_in=['team_short_name', 'team_short_value'])
	shorts = [value for short in shorts for name, value in (short, )]

	for short in shorts:
		c = shorts.count(short)
		if c > 1:
			print(f'Check short name {short}')
