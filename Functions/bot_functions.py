import datetime
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import logging as log

logger = log.get_flogger()


def check_still_to_confirm(db, c, first_name):

	# This a list of the users who have their bets in the status
	# 'Not Confirmed'
	users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
								   pred_status = "Not Confirmed"'''))
	users_list = [element[0] for element in users_list]

	if first_name in users_list:

		ref_list = list(c.execute(
				'''SELECT pred_team1, pred_team2, pred_rawbet, pred_quote FROM
				   predictions WHERE pred_status = "Not Confirmed" AND
				   pred_user = ?''', (first_name,)))
		db.close()

		team1, team2, bet, bet_quote = ref_list[0]

		printed_bet = '{} - {} {} @{}'.format(team1, team2, bet, bet_quote)

		message = ('{}, you still have one bet to confirm.\n'.format(
				   first_name) + ('{}\n' + 'Use /confirm or /cancel to ' +
				   'finalize your bet.').format(printed_bet))

		return message

	else:
		return False


def update_tables_and_ref_list(db, c, first_name, bet_id):

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
		c.execute('''INSERT INTO bets (bet_status, bet_result)
		VALUES (?, ?)''', ('Pending', 'Unknown'))

		bet_id = c.lastrowid

	c.execute('''UPDATE predictions SET pred_bet = ?, pred_status = "Confirmed"
			  WHERE pred_user = ? AND pred_status = "Not Confirmed"''',
			  (bet_id, first_name))

	ref_list = list(c.execute('''SELECT pred_team1, pred_team2, pred_league
							  FROM bets INNER JOIN predictions on
							  pred_bet = bet_id WHERE bet_id = ? AND
							  pred_user = ?''', (bet_id, first_name)))

	db.commit()

	return ref_list


def check_if_duplicate(c, first_name, match, ref_list):

	message = ''

	pred_id = match[0]
	user = match[1]
	team1 = match[2]
	team2 = match[3]
	league = match[4]

	if (team1, team2, league) in ref_list:
		c.execute('''DELETE FROM predictions WHERE pred_id = ?''',
				  (pred_id,))
		message = ('{}, your bet on the match '.format(user) +
				   '{} - {} has '.format(team1, team2) +
				   'been canceled because ' +
				   '{} confirmed first.'.format(first_name))

	return message


def create_matches_to_play(c, bet_id):

	"""
	Called inside the command /play_bet.
	Return a list of tuples representing the matches to be added in the
	basket.
	"""

	some_data = list(c.execute('''SELECT pred_team1, pred_team2, pred_league,
							   pred_field FROM bets INNER JOIN predictions on
							   pred_bet = bet_id WHERE bet_id = ?''',
							   (bet_id,)))
	matches_to_play = []

	for match in some_data:
		team1 = match[0]
		team2 = match[1]
		league = match[2]
		field_id = match[3]

		if league == 8:
			team1 = '*' + team1
			team2 = '*' + team2

		field_name, field_value = list(c.execute('''SELECT field_name,
												 field_value FROM fields WHERE
												 field_id = ?''',
												 (field_id,)))[0]

		url = list(c.execute('''SELECT match_url FROM matches WHERE
							 match_team1 = ? AND match_team2 = ? AND
							 match_league = ?''', (team1, team2,
												   league)))[0][0]

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

	message = ''
	requested_day = format_day(day)

	db, c = dbf.start_db()
	try:
		bet_id = list(c.execute('''SELECT bet_id FROM bets WHERE
								bet_status = "Pending" '''))[0][0]
	except IndexError:
		bet_id = 0

	confirmed_matches = list(c.execute('''SELECT pred_league, pred_team1,
									   pred_team2, pred_time FROM bets INNER
									   JOIN predictions on pred_bet = bet_id
									   WHERE bet_id = ?''', (bet_id,)))

	for league in sf.countries:

		league_id = list(c.execute('''SELECT league_id FROM leagues WHERE
								   league_name = ?''', (league,)))[0][0]

		matches_to_print = list(c.execute('''SELECT match_id, match_team1,
										  match_team2, match_time FROM matches
										  WHERE match_date = ? AND
										  match_league = ?''', (requested_day,
																league_id)))
		for match in confirmed_matches:
			try:
				match_id = list(c.execute('''SELECT match_id FROM matches WHERE
										  match_league = ? AND match_team1 = ?
										  AND match_team2 = ?''',
										  (league_id, match[1],
										   match[2])))[0][0]
			except IndexError:
				continue

			new_tuple = (match_id, match[1], match[2], match[3])

			if new_tuple in matches_to_print:
				matches_to_print.remove(new_tuple)

		if matches_to_print:
			message += '\n\n<b>{}</b>'.format(league)
			for match in matches_to_print:
				match_id = match[0]
				team1 = match[1].replace('*', '')
				team2 = match[2].replace('*', '')
				match_time = str(match[3]).zfill(4)
				match_time = match_time[:2] + ':' + match_time[2:]

				try:
					short_team1 = list(c.execute('''SELECT team_short_value
												 FROM teams_short WHERE
												 team_short_name = ?''',
												 (team1,)))[0][0]
				except IndexError:
					short_team1 = team1[:3]
				try:
					short_team2 = list(c.execute('''SELECT team_short_value
												 FROM teams_short WHERE
												 team_short_name = ?''',
												 (team2,)))[0][0]
				except IndexError:
					short_team2 = team2[:3]

				quote1 = list(c.execute('''SELECT quote_value FROM quotes WHERE
										quote_match = ? AND quote_field = 1''',
										(match_id,)))[0][0]
				quoteX = list(c.execute('''SELECT quote_value FROM quotes WHERE
										quote_match = ? AND quote_field = 2''',
										(match_id,)))[0][0]
				quote2 = list(c.execute('''SELECT quote_value FROM quotes WHERE
										quote_match = ? AND quote_field = 3''',
										(match_id,)))[0][0]

				quote1 = format_quote(quote1)
				quoteX = format_quote(quoteX)
				quote2 = format_quote(quote2)

				message += '\n<code>{} {}-{} {} {} {}</code>'.format(
																match_time,
																short_team1,
																short_team2,
																quote1,
																quoteX,
																quote2)

	db.close()

	if message:
		return message
	else:
		return 'No matches on the selected day.'


def format_day(input_day):

	"""
	Take the input_day in the form 'lun', 'mar', 'mer'..... and return
	the corresponding date as an integer. If on May 16th 1985 (Thursday)
	command format_day('sab') is sent, output will be:

		19850518
	"""

	weekdays = {'lun': 0,
				'mar': 1,
				'mer': 2,
				'gio': 3,
				'ven': 4,
				'sab': 5,
				'dom': 6}

	if input_day not in weekdays:

		raise SyntaxError('Not a valid day. Options are: lun, mar, mer, ' +
						  'gio, ven, sab, dom.')

	today_date = datetime.date.today()
	today_weekday = datetime.date.today().weekday()

	days_shift = weekdays[input_day] - today_weekday
	if days_shift < 0:
		days_shift += 7
	new_date = str(today_date + datetime.timedelta(days=days_shift))
	new_date = int(new_date.replace('-', ''))

	return new_date


def all_bets_per_team(db, c, team_name, league_id):

	"""
	Return two text messages: one showing all the standard bets and the
	other one the combo. Both of them are relative to the match of the
	league whose id is "league_id" and team "team_name" is playing.
	"""

	fields2avoid = [i for i in range(17, 31)]

	try:
		match_id, team1, team2 = list(
				c.execute('''SELECT match_id, match_team1, match_team2 FROM
							 matches WHERE match_league = ? AND
							 (match_team1 = ? OR match_team2 = ?)''',
						 (league_id, team_name, team_name,)))[0]
	except IndexError:
		db.close()
		raise ValueError('Quotes not available')

	team1 = team1.replace('*', '')
	team2 = team2.replace('*', '')

	message_standard = '<b>{} - {}: STANDARD</b>\n'.format(team1, team2)
	message_combo = '<b>{} - {}: COMBO</b>\n'.format(team1, team2)

	fields = list(c.execute('''SELECT field_id, field_value FROM fields'''))
	fields = [el for el in fields if el[0] not in fields2avoid]

	fields_added = []
	for field_id, field_value in fields:
		field_name = list(c.execute('''SELECT field_name FROM fields WHERE
									   field_id = ?''', (field_id,)))[0][0]
		if field_name not in fields_added:
			fields_added.append(field_name)
			if '+' not in field_name:
				COMBO = False
				message_standard += '\n\n<i>{}</i>'.format(field_name)
			else:
				COMBO = True
				message_combo += '\n\n<i>{}</i>'.format(field_name)
		try:
			quote = list(c.execute('''SELECT quote_value FROM quotes WHERE
								   quote_match = ? AND quote_field = ?''',
								   (match_id, field_id)))[0][0]
		except IndexError:
			if not COMBO:
				message_standard += '\n<b>{}</b>: NOT FOUND'.format(
																   field_value)
			else:
				message_combo += '\n<b>{}</b>: NOT FOUND'.format(field_value)
			continue

		if not COMBO:
			message_standard += '\n<b>{}</b>:    @{}'.format(field_value,
															 quote)
		else:
			message_combo += '\n<b>{}</b>:    @{}'.format(field_value, quote)

	return message_standard, message_combo


def look_for_quote(text):

	"""
	Take the input from the user and look into the db for the requested
	quote. Return five variables which will be used later to update the
	"predictions" table in the db.
	"""

	input_team, input_bet = text.split('_')

	db, c = dbf.start_db()

	try:
		field_id = list(c.execute('''SELECT field_alias_field FROM fields_alias
									 WHERE field_alias_name = ? ''',
								  (input_bet,)))[0][0]
		nice_bet = list(c.execute('''SELECT field_nice_value FROM fields
									 WHERE field_id = ? ''',
								  (field_id,)))[0][0]
	except IndexError:
		db.close()
		raise SyntaxError('Bet not valid.')

	try:
		team_id = list(c.execute('''SELECT team_alias_team FROM teams_alias
									WHERE team_alias_name = ? ''',
								 (input_team,)))[0][0]
	except IndexError:
		db.close()
		raise SyntaxError('Team not valid.')

	team_name = list(c.execute('''SELECT team_name FROM teams INNER JOIN
							   teams_alias on team_alias_team = team_id WHERE
							   team_id = ? ''', (team_id,)))[0][0]

	if '*' in input_team:
		league_id = 8
	else:
		league_id = list(c.execute('''SELECT team_league FROM teams
								   WHERE team_name = ? AND team_league != 8''',
								   (team_name,)))[0][0]

	try:
		team1, team2 = list(c.execute('''SELECT match_team1, match_team2 FROM
									  matches WHERE match_team1 = ? OR
									  match_team2 = ?''', (team_name,
									  team_name)))[0]
	except IndexError:
		db.close()
		raise ValueError('Quotes not available')

	match_id = list(c.execute('''SELECT match_id FROM matches
							  WHERE match_team1 = ? AND match_team2 = ?''',
							  (team1, team2)))[0][0]


	try:
		quote = list(c.execute('''SELECT quote_value FROM quotes
							   WHERE quote_match = ? AND quote_field = ?''',
							   (match_id, field_id)))[0][0]
	except IndexError:
		raise ValueError('Quote not available for this match')

	db.close()

	return team1, team2, field_id, league_id, nice_bet, quote
