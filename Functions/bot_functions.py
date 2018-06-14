import datetime
import pandas as pd
from Functions import db_functions as dbf
from Functions import logging as log


logger = log.get_flogger()


def check_still_to_confirm(first_name):

	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
			where='pred_status = "Not Confirmed"')

	if first_name in users_list:

		ref_list = dbf.db_select(
				table='predictions',
				columns_in=['pred_team1', 'pred_team2',
							'pred_rawbet', 'pred_quote'],
				where='pred_status = "Not Confirmed" AND pred_user = "{}"'.
				format(first_name))

		team1, team2, bet, bet_quote = ref_list[0]

		printed_bet = '{} - {} {} @{}'.format(team1, team2, bet, bet_quote)

		message = ('{}, you still have one bet to confirm.\n'.format(
				   first_name) + ('{}\n' + 'Use /confirm or /cancel to ' +
				   'finalize your bet.').format(printed_bet))

		return message

	else:
		return False


def update_tables_and_ref_list(first_name, bet_id):

	"""
	Called inside the command /confirm.
	Insert a new row in the 'bets' table if needed and update the columns
	pred_bet and pred_status of the table 'predictions'. Return a list
	containing the tuple (team1, team2, league_id) of the match which is
	beign confirmed. It will be used inside the function check_if_duplicate
	to delete all the Not Confirmed bets relative to same match, if present,
	from the 'predictions' table.
	"""

	if not bet_id:

		# If not, we create it and update 'matches' table
		bet_id = dbf.db_insert(
				table='bets',
				columns='(bet_status, bet_result)',
				values='("Pending", "Unknown")',
				last_row=True)

	dbf.db_update(
			table='predictions',
			columns='pred_bet = {}, pred_status = "Confirmed"'.format(bet_id),
			where='pred_user = "{}" AND pred_status = "Not Confirmed"'.
			format(first_name))

	ref_list = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_team1', 'pred_team2', 'pred_league'],
			where='bet_id = {} AND pred_user = "{}"'.format(bet_id,
															first_name))

	return ref_list


def check_if_duplicate(first_name, match, ref_list):

	message = ''

	pred_id = match[0]
	user = match[1]
	team1 = match[2]
	team2 = match[3]
	league = match[4]

	if (team1, team2, league) in ref_list:
		dbf.db_delete(
				table='predictions',
				where='pred_id = {}'.format(pred_id))

		message = ('{}, your bet on the match '.format(user) +
				   '{} - {} has '.format(team1, team2) +
				   'been canceled because ' +
				   '{} confirmed first.'.format(first_name))

	return message


def create_matches_to_play(bet_id):

	"""
	Called inside the command /play_bet.
	Return a list of tuples representing the matches to be added in the
	basket.
	"""

	data = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_team1', 'pred_team2',
						'pred_league', 'pred_field'],
			where='bet_id = {}'.format(bet_id))

	matches_to_play = []

	for team1, team2, league, field_id in data:

		if league == 8:
			team1 = '*' + team1
			team2 = '*' + team2

		field_name, field_value = dbf.db_select(
				table='fields',
				columns_in=['field_name', 'field_value'],
				where='field_id = {}'.format(field_id))[0]


		url = dbf.db_select(
				table='matches',
				columns_in=['match_url'],
				where=('match_team1 = "{}" AND '.format(team1) +
					   'match_team2 = "{}" AND '.format(team2) +
					   'match_league = {}'.format(league)))[0]

		matches_to_play.append((team1, team2, field_name, field_value, url))

	return matches_to_play


def matches_per_day(day):

	"""
	Return a message containing all the matches scheduled for the day "day".
	Input "day" needs to have the correct form in order to be handled by
	the function format_day.
	"""

	def format_quote(afloat):
		if len(str(afloat).split('.')[0]) == 3:
			return int(str(afloat).split('.')[0])
		elif len(str(afloat).split('.')[0]) == 2:
			return '{:>.1f}'.format(afloat)
		else:
			return '{:>.2f}'.format(afloat)

	def prep_all_matches(df):

		df['ymd'] = df['match_date'].apply(
				lambda x: datetime.datetime.strptime(
						x, '%Y-%m-%d %H:%M:%S').date())
		df['hm'] = df['match_date'].apply(
				lambda x: datetime.datetime.strptime(
						x, '%Y-%m-%d %H:%M:%S').time())
		df.drop('match_date', axis=1, inplace=True)

		return df[df['ymd'] == dt].drop('ymd', axis=1)

	def prep_confirmed(df):

		df.columns = ['match_date', 'match_team1',
					  'match_team2', 'match_league']
		df['match_id'] = 0
		df = df[['match_id', 'match_league', 'match_team1',
				 'match_team2', 'match_date']]

		df['hm'] = df['match_date'].apply(
				lambda x: datetime.datetime.strptime(
						x, '%Y-%m-%d %H:%M:%S').time())

		return df.drop('match_date', axis=1)

	def league_name(number):

		name = dbf.db_select(
				table='leagues',
				columns_in=['league_name'],
				where='league_id = {}'.format(number))[0]

		return name

	weekdays = {'lun': 0, 'mar': 1, 'mer': 2, 'gio': 3,
				'ven': 4, 'sab': 5, 'dom': 6}

	message = ''
	dt = datetime.date.today()
	requested_day = weekdays[day]
	while dt.weekday() != requested_day:
		dt += datetime.timedelta(1)

	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')[0]
	except IndexError:
		bet_id = 0

	all_matches = dbf.db_select(
			table='matches',
			columns_out=['match_url'],
			dataframe=True)

	all_matches = prep_all_matches(all_matches)

	confirmed = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_date', 'pred_team1',
						'pred_team2', 'pred_league'],
			where='bet_id = {}'.format(bet_id),
			dataframe=True)
	if len(confirmed):

		confirmed = prep_confirmed(confirmed)

		all_matches = pd.concat([all_matches, confirmed]).drop_duplicates(
			subset=['match_team1', 'match_team2'], keep=False)

	if not len(all_matches):
		return 'No matches on the selected day.'

	else:
		leagues = all_matches['match_league'].unique()
		for i in leagues:
			league = league_name(i)
			message += '\n\n<b>{}</b>'.format(league)

			df_temp = all_matches[all_matches['match_league'] == i]
			for j in range(len(df_temp)):
				id_, _, team1, team2, hhmm = df_temp.iloc[j]
				team1 = team1.replace('*', '')
				team2 = team2.replace('*', '')
				hhmm = '{}:{}'.format(hhmm.hour, str(hhmm.minute).zfill(2))

				try:
					short_team1 = dbf.db_select(
							table='teams_short',
							columns_in=['team_short_value'],
							where='team_short_name = "{}"'.format(team1))[0]
				except IndexError:
					short_team1 = team1[:3]
				try:
					short_team2 = dbf.db_select(
							table='teams_short',
							columns_in=['team_short_value'],
							where='team_short_name = "{}"'.format(team2))[0]
				except IndexError:
					short_team2 = team2[:3]

				quote1 = dbf.db_select(
						table='quotes',
						columns_in=['quote_value'],
						where='quote_match = {} AND quote_field = 1'.
						format(id_))[0]

				quoteX = dbf.db_select(
						table='quotes',
						columns_in=['quote_value'],
						where='quote_match = {} AND quote_field = 2'.
						format(id_))[0]

				quote2 = dbf.db_select(
						table='quotes',
						columns_in=['quote_value'],
						where='quote_match = {} AND quote_field = 3'.
						format(id_))[0]

				quote1 = format_quote(quote1)
				quoteX = format_quote(quoteX)
				quote2 = format_quote(quote2)

				message += '\n<code>{} {}-{} {} {} {}</code>'.format(
																hhmm,
																short_team1,
																short_team2,
																quote1,
																quoteX,
																quote2)

		return message


def all_bets_per_team(team_name, league_id):

	"""
	Return two text messages: one showing all the standard bets and the
	other one the combo. Both of them are relative to the match of the
	league whose id is "league_id" and team "team_name" is playing.
	"""

	fields2avoid = ([i for i in range(4, 14)] + [i for i in range(17, 31)] +
	                [i for i in range(152, 157)])

	try:
		match_id, team1, team2 = dbf.db_select(
				table='matches',
				columns_in=['match_id', 'match_team1', 'match_team2'],
				where=('match_league = {} AND ' +
					   '(match_team1 = "{}" OR match_team2 = "{}")').
				format(league_id, team_name, team_name))[0]
	except IndexError:
		raise ValueError('Quotes not available')

	team1 = team1.replace('*', '')
	team2 = team2.replace('*', '')

	message_standard = '<b>{} - {}: STANDARD</b>\n'.format(team1, team2)
	message_combo = '<b>{} - {}: COMBO</b>\n'.format(team1, team2)

	fields = dbf.db_select(
			table='fields',
			columns_in=['field_id', 'field_value'])
	fields = [el for el in fields if el[0] not in fields2avoid]

	fields_added = []
	COMBO = False
	for field_id, field_value in fields:
		field_name = dbf.db_select(
				table='fields',
				columns_in=['field_name'],
				where='field_id = {}'.format(field_id))[0]

		if field_name not in fields_added:
			fields_added.append(field_name)
			if '+' not in field_name:
				COMBO = False
				message_standard += '\n\n<i>{}</i>'.format(field_name)
			else:
				COMBO = True
				message_combo += '\n\n<i>{}</i>'.format(field_name)

		quote = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = "{}"'.
				format(match_id, field_id))[0]

		cond = type(quote) == str
		if not cond:
			quote = '@' + str(quote)

		if not COMBO:
			message_standard += '\n<b>{}</b>:    {}'.format(field_value,
															quote)
		else:
			message_combo += '\n<b>{}</b>:    {}'.format(field_value, quote)

	return message_standard, message_combo


def look_for_quote(team_name, input_bet):

	"""
	Take the input from the user and look into the db for the requested
	quote. Return five variables which will be used later to update the
	"predictions" table in the db.
	"""

	try:
		field_id = dbf.db_select(
				table='fields_alias',
				columns_in=['field_alias_field'],
				where='field_alias_name = "{}"'.format(input_bet))[0]

		nice_bet = dbf.db_select(
				table='fields',
				columns_in=['field_nice_value'],
				where='field_id = {}'.format(field_id))[0]

	except IndexError:
		raise SyntaxError('Bet not valid.')

	try:
		match_id, team1, team2 = dbf.db_select(
				table='matches',
				columns_in=['match_id', 'match_team1', 'match_team2'],
				where='match_team1 = "{}" OR match_team2 = "{}"'.
				format(team_name, team_name))[0]
	except IndexError:
		raise ValueError('Quotes not available')

	try:
		quote = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = {}'.
				format(match_id, field_id))[0]
	except IndexError:
		raise ValueError('Quote not available for this match')

	return team1, team2, field_id, nice_bet, quote
