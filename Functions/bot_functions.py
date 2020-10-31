import datetime
import pandas as pd
import db_functions as dbf


def check_if_duplicate(first_name, details):

	"""
	Check whether there are Not Confirmed preds of the match which is being
	confirmed. If any, they will be deleted.

	:param first_name: str

	:param details: tuple, (team1, team2, league_id). Output of the function
					update_pred_table_after_confirm.


	:return: str, warning message for the deleted bets
	"""

	message = ''
	users2del = []

	not_conf_matches = dbf.db_select(
			table='predictions',
			columns_in=['pred_id', 'pred_user', 'pred_team1', 'pred_team2',
			            'pred_league'],
			where='pred_status = "Not Confirmed"')

	for match in not_conf_matches:
		pred_id = match[0]
		user = match[1]
		team1 = match[2]
		team2 = match[3]
		league = match[4]

		if (team1, team2, league) == details:
			dbf.db_delete(
					table='predictions',
					where='pred_id = {}'.format(pred_id))
			users2del.append(user)

			message = ('{}, your bet on the match '.format('/'.join(users2del)) +
					   '{} - {} has '.format(team1, team2) +
					   'been canceled because ' +
					   '{} confirmed first.'.format(first_name))

	return message


def check_if_input_is_correct(user_input):    # DONE

	# Warning message if amount is missing
	if not user_input:
		return 'Insert the amount. Ex: /play 5'

	# Check that input is an integer number >= 2
	try:
		euros = int(user_input[0])
		if euros < 2:
			return 'Minimum amount is 2 Euros.'
		else:
			return euros

	except ValueError:
		return 'Amount has to be integer.'


def look_for_quote(team_name, input_bet):

	"""
	Called inside the command /get.
	Take the input from the user and look into the db for the requested
	quote.

	:param team_name: str

	:param input_bet: str


	:return: (str, str, int, str, float)
	"""

	try:
		field_id = dbf.db_select(
				table='fields_alias',
				columns_in=['field_alias_field'],
				where='field_alias_name = "{}"'.format(input_bet))[-1]

		nice_bet = dbf.db_select(
				table='fields',
				columns_in=['field_nice_value'],
				where='field_id = {}'.format(field_id))[0]

	except IndexError:
		raise ValueError('Bet not valid.')

	try:
		match_id, team1, team2 = dbf.db_select(
				table='matches',
				columns_in=['match_id', 'match_team1', 'match_team2'],
				where='match_team1 = "{}" OR match_team2 = "{}"'.
				format(team_name, team_name))[0]
	except IndexError:
		raise ValueError('Quotes not available for {}'.format(team_name))

	try:
		quote = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = {}'.
				format(match_id, field_id))[0]
	except IndexError:
		raise ValueError('Quote not available for this match')

	return team1, team2, field_id, nice_bet, quote


def matches_per_day(day):

	"""
	Called inside the command /match.
	Return a message containing all the matches scheduled for that day.

	:param day: str, one of [lun, mar, mer, gio, ven, sab, dom]


	:return: str
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
		df = df.loc[:, ['match_id', 'match_league', 'match_team1',
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

	def short_names(string1, string2):

		try:
			short_team1 = dbf.db_select(
					table='teams_short',
					columns_in=['team_short_value'],
					where='team_short_name = "{}"'.format(string1))[0]
		except IndexError:
			short_team1 = string1[:3]
		try:
			short_team2 = dbf.db_select(
					table='teams_short',
					columns_in=['team_short_value'],
					where='team_short_name = "{}"'.format(string2))[0]
		except IndexError:
			short_team2 = string2[:3]

		return short_team1, short_team2

	def quotes(match_id):

		quote1 = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = 1'.
				format(match_id))[0]

		quoteX = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = 2'.
				format(match_id))[0]

		quote2 = dbf.db_select(
				table='quotes',
				columns_in=['quote_value'],
				where='quote_match = {} AND quote_field = 3'.
				format(match_id))[0]

		quote1 = format_quote(quote1)
		quoteX = format_quote(quoteX)
		quote2 = format_quote(quote2)

		return quote1, quoteX, quote2

	weekdays = {'lun': 0, 'mar': 1, 'mer': 2, 'gio': 3,
				'ven': 4, 'sab': 5, 'dom': 6}

	message = ''
	dt = datetime.date.today()
	try:
		requested_day = weekdays[day]
	except KeyError:
		raise SyntaxError('Not a valid day')

	while dt.weekday() != requested_day:
		dt += datetime.timedelta(1)

	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')[0]

		confirmed = dbf.db_select(
				table='bets INNER JOIN predictions on pred_bet = bet_id',
				columns_in=['pred_date', 'pred_team1',
				            'pred_team2', 'pred_league'],
				where='bet_id = {}'.format(bet_id),
				dataframe=True)
	except IndexError:
		confirmed = []

	all_matches = dbf.db_select(
			table='matches',
			columns_out=['match_url'],
			dataframe=True)

	if not len(all_matches):
		return 'MATCHES table empty.'

	all_matches = prep_all_matches(all_matches)
	if not len(all_matches):
		return 'No matches on the selected day.'

	if len(confirmed):
		confirmed = prep_confirmed(confirmed)

		all_matches = (pd.concat([all_matches, confirmed, confirmed]).
			drop_duplicates(subset=['match_team1', 'match_team2'],
		                keep=False))
		if not len(all_matches):
			return 'All matches are chosen.'

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

			short_team1, short_team2 = short_names(team1, team2)

			quote1, quoteX, quote2 = quotes(id_)

			message += ('\n<code>{} {}-{} {} {} {}</code>'.
						format(hhmm, short_team1, short_team2,
						quote1, quoteX, quote2))

	return message


def one_or_more_preds_are_not_confirmed():   # DONE

	not_conf_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user', 'pred_team1', 'pred_team2', 'pred_rawbet',
			            'pred_quote'],
			where='pred_status = "Not Confirmed"')

	if not_conf_list:
		message = 'There are still Not Confirmed bets:'

		for user, team1, team2, bet, quote in not_conf_list:
			message += '\n\n<b>{}</b>: {} - {}  {} <b>@{}</b>'.format(
					user, team1, team2, bet, quote)

		return message + '\n\n/confirm or /cancel and then play again.'

	else:
		return None
