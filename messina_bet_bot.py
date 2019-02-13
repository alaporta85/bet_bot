import os
import random
import time
import datetime
import numpy as np
from itertools import count
from telegram.ext import Updater
from telegram.ext import CommandHandler
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import bot_functions as bf
from Functions import stats_functions as stf
from Functions import logging as log
import Classes as cl

f = open('token.txt', 'r')
updater = Updater(token=f.readline())
f.close()

lim_low = 1.8
lim_high = 3.2
n_bets = 4

dispatcher = updater.dispatcher


def allow(bot, update, args):  # DONE

	"""
	Allow users to play bet outside the decided limits.

	"""

	chat_id = update.message.chat_id

	# Only admins can allow other users
	_, role = nickname(update)
	if role != 'Admin':
		return bot.send_message(chat_id=chat_id, text='Fatti i cazzi tuoi')

	# Select correct name
	users = dbf.db_select(
			table='people',
			columns_in=['people_nick'])
	user = dbf.jaccard_result(args[0].title(), users, 3)

	if not user:
		return bot.send_message(chat_id=chat_id, text='User not found')

	# Insert user into the "allow" table
	dbf.db_insert(
			table='allow',
			columns=['allow_name'],
			values=[user])

	return bot.send_message(chat_id=chat_id, text='{} can play.'.format(user))


def cake(bot, update):  # DONE

	"""
	Send the cake.

	"""

	chat_id = update.message.chat_id
	bot.send_photo(chat_id=chat_id, photo=open('cake.png', 'rb'))


def bike(bot, update):  # DONE

	"""
	Send bike sound.

	"""

	chat_id = update.message.chat_id
	return bot.send_audio(chat_id=chat_id, audio=open('bici.mp3', 'rb'))


def cancel(bot, update):  # DONE

	"""
	Delete the 'Not Confirmed' match from 'predictions' table.

	"""

	chat_id = update.message.chat_id
	user, _ = nickname(update)

	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if user not in users_list:
		return bot.send_message(chat_id=chat_id,
								text='{}, no bet to cancel.'.format(user))

	dbf.db_delete(
			table='predictions',
	        where='pred_user = "{}" AND pred_status = "Not Confirmed"'.
	        format(user))

	return bot.send_message(chat_id=chat_id,
	                        text='{}, bet canceled.'.format(user))


def confirm(bot, update):  # DONE

	"""
	Confirm the match and update the database.

	"""

	chat_id = update.message.chat_id
	user, _ = nickname(update)

	# This a list of the users who have their bets in the status
	# 'Not Confirmed'
	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if user not in users_list:
		return bot.send_message(
				chat_id=chat_id, text='{}, no match to confirm.'.format(user))

	# Check if quote respects the limits
	limits_ok = limits_are_respected(user)
	if not limits_ok:
		return bot.send_message(chat_id=chat_id, text='Se cia 👏👏🖕🖕')

	# Delete user from 'allow' table, if present. If not, nothing happens
	dbf.db_delete(
			table='allow',
			where='allow_name = "{}"'.format(user))

	# Update the database
	bet_id, details = bf.update_db_after_confirm(user)

	# Inform users about possible duplicate matches which have been deleted
	dupl_message = bf.check_if_duplicate(user, details)
	if dupl_message:
		bot.send_message(chat_id=chat_id, text=dupl_message)

	# Inform users match is correctly added
	bot.send_message(chat_id=chat_id,
	                 text='{}, match added correctly.'.format(user))

	# Play the bet automatically
	auto_play = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where='pred_bet = {}'.format(bet_id))
	if len(auto_play) == n_bets:
		return play(bot, update, ['5'])


def create_list_of_matches(bet_id):  # DONE

	"""
	Create a list of the matches belonging to the bet having the passed bet_id.
	Used inside create_summary().

	:param bet_id: int

	:return: str

	"""

	message = ''

	matches = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_user', 'pred_date', 'pred_team1',
			            'pred_team2',
			            'pred_rawbet', 'pred_quote'],
			where='bet_id = {}'.format(bet_id))

	# Sort matches by datetime
	matches = sorted(matches, key=lambda x: x[1])

	final_quote = np.prod(np.array([el[5] for el in matches]))
	for user, dt, team1, team2, rawbet, quote in matches:
		# Extract the time
		dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
		hhmm = str(dt.hour).zfill(2) + ':' + str(dt.minute).zfill(2)

		message += '<b>{}</b>:     {}-{} ({})    {}      @<b>{}</b>\n'.format(
				user, team1, team2, hhmm, rawbet, quote)

	return message, final_quote


def create_summary(string):  # DONE

	"""
	Create the message with the summary of the bet depending on the string
	passed.

	:param string: -  'before' for the summary before playing the bet, used
					  inside /summary()

				   -  'after' for the summary after playing the bet, used
					  inside /play()

				   -  'remind' for the summary of all the bets placed but still
				      incomplete, used inside /remind()

	:return: str

	"""

	if string == 'before':
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')
		if not bet_id:
			return 'No bets yet. Choose the first one.'
		else:
			message, final_quote = create_list_of_matches(bet_id[0])
			last_line = ('\n\nPossible win with 5 euros: ' +
			             '<b>{:.1f}</b>'.format(final_quote * 5))
			return message + last_line

	elif string == 'after':
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Placed" AND bet_result = "Unknown"')[-1]

		message, final_quote = create_list_of_matches(bet_id[0])
		first_line = 'Bet placed correctly.\n\n'
		last_line = '\nPossible win: <b>{:.1f}</b>'.format(final_quote * 5)

		return first_line + message + last_line

	elif string == 'remind':
		message = 'Bets still incomplete:\n\n'

		incomplete_bets = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Placed" AND bet_result = "Unknown"')
		for bet_id in incomplete_bets:
			message2, final_quote = create_list_of_matches(bet_id)
			message += ('{}\nPossible win: <b>{:.1f}</b>\n\n\n'.
			            format(message2, final_quote * 5))

		return message


def delete(bot, update):  # DONE

	"""
	Delete the 'Confirmed' match from 'predictions' table.

	"""

	chat_id = update.message.chat_id
	user, _ = nickname(update)

	# Check if there is any 'Pending' bet
	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
		        where='bet_status = "Pending"')[0]
	except IndexError:
		return bot.send_message(chat_id=chat_id, text='No open bets.')

	# Check if user has a match to delete
	try:
		match_to_delete = dbf.db_select(
				table='predictions',
				columns_in=['pred_id'],
				where=('pred_bet = {} AND pred_user = "{}" AND ' +
				       'pred_status = "Confirmed"').format(bet_id, user))[0]
	except IndexError:
		return bot.send_message(chat_id=chat_id,
		                        text='{}, no match to delete.'.format(user))

	# Update the database
	bf.update_to_play_table(user, bet_id, 'delete')
	dbf.db_delete(
			table='predictions',
			where='pred_id = {}'.format(match_to_delete))

	# Check if this was the only match of the bet and, if yes, delete the bet
	# in the 'bet' table
	conf_bets_left = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where='pred_status = "Confirmed" AND pred_bet = {}'.format(bet_id))

	if not conf_bets_left:
		dbf.db_delete(
				table='bets',
		        where='bet_id = {}'.format(bet_id))

	return bot.send_message(
			chat_id=chat_id, text='{}, bet deleted.'.format(user))


def fischia(bot, update):  # DONE

	"""
	Send random photo of Mazzarri.

	"""

	chat_id = update.message.chat_id
	walter = random.choice(os.listdir('Mazzarri/'))

	return bot.send_photo(chat_id=chat_id,
	                      photo=open('Mazzarri/' + walter, 'rb'))


def format_text(content):  # DONE

	"""
	Called inside help_stats() function to clean the message text.

	"""

	message = ''.join(content)
	message = message.replace('\n\n', 'xx')
	message = message.replace('\n', ' ')
	message = message.replace('xx', '\n\n')

	return message


def get(bot, update, args):  # DONE

	"""
	Update the table 'predictions' in the database with the data relative to
	the chosen match if command is in the form:

		/play team_bet

	If the command has the form:

		/play team

	it sends all the quotes for that team's match.

	"""

	chat_id = update.message.chat_id

	# Check the format
	if not args:
		return bot.send_message(chat_id=chat_id, text='Insert the bet.')

	guess = ' '.join(args).upper()
	if guess[0] == '_' or guess[-1] == '_':
		return bot.send_message(chat_id=chat_id, text='Wrong format.')

	# Try to separate the team from the bet and replace some values
	try:
		vals2replace = [(' ', ''), ('*', ''), ('+', ''), (',', '.'),
		                ('TEMPO', 'T'),
		                ('1T', 'PT'), ('2T', 'ST'),
		                ('GOAL', 'GG'), ('NOGOAL', 'NG'),
		                ('HANDICAP', 'H'), ('HAND', 'H')]

		input_team, input_bet = guess.split('_')
		for old, new in vals2replace:
			input_bet = input_bet.replace(old, new)

	except ValueError:
		# If only the team is sent
		input_team, input_bet = guess, ''

	# Correct team name by Jaccard similarity
	team_name = dbf.select_team(input_team)

	if not team_name:
		return bot.send_message(chat_id=chat_id, text='Team not found')

	# If '*' is in the input it means it's a Champions League match
	elif '*' in input_team:
		league_id = 8
		team_name = '*' + team_name

	# Try to select the league. The IndexError occurs when the Jaccard result
	# is a team playing in Champions League but not in any of the main leagues.
	# In this case, looking for that team among any team_id != 8 would cause an
	# error. Ex: if '/play dort' is sent, meaning Dortmund, bot will recognize
	# it as PORTO and the error is given
	else:
		try:
			league_id = dbf.db_select(
					table='teams',
					columns_in=['team_league'],
					where='team_name = "{}" AND team_league != 8'.
					format(team_name))[0]
		except IndexError:
			return bot.send_message(
					chat_id=chat_id,
					text='No bets found for {}'.format(team_name))

	# If only the team is sent, 2 messages with all the quotes for that match
	# will be sent in the chat
	if not input_bet:
		try:
			message_standard, message_combo = bf.all_bets_per_team(team_name,
			                                                       league_id)

		# If, for any reason, quotes are not found
		except ValueError as e:
			message = str(e)
			return bot.send_message(chat_id=chat_id, text=message)

		bot.send_message(parse_mode='HTML', chat_id=chat_id,
		                 text=message_standard)
		return bot.send_message(parse_mode='HTML', chat_id=chat_id,
								text=message_combo)

	user, _ = nickname(update)

	# Check if user has other matches not confirmed
	warning_message = bf.check_still_to_confirm(user)
	if warning_message:
		return bot.send_message(chat_id=chat_id, text=warning_message)

	# Create the list of confirmed_matches. This list will be used to check
	# whether a match has already been chosen
	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')[0]

		confirmed_matches = dbf.db_select(
				table='predictions',
				columns_in=['pred_team1', 'pred_team2'],
				where=('pred_status = "Confirmed" AND pred_bet = {}'.
				format(bet_id)))
	except IndexError:
		confirmed_matches = []

	# Try to extract all the info about the match and the requested quote
	try:
		team1, team2, field_id, nice_bet, quote = bf.look_for_quote(team_name,
		                                                            input_bet)

	# To handle invalid bets or missing quotes
	except ValueError as e:
		return bot.send_message(chat_id=chat_id, text=str(e))

	# If match is available, update the database and send a message
	if (team1, team2) not in confirmed_matches:

		dt = dbf.db_select(
				table='matches',
				columns_in=['match_date'],
				where='match_team1 = "{}" AND match_team2 = "{}"'.
				format(team1, team2))[0]

		team1 = team1.replace('*', '')
		team2 = team2.replace('*', '')

		dbf.db_insert(
				table='predictions',
				columns=['pred_user', 'pred_date', 'pred_team1', 'pred_team2',
				         'pred_league', 'pred_field', 'pred_rawbet',
				         'pred_quote', 'pred_status'],
				values=[user, dt, team1, team2, league_id, field_id,
				        nice_bet, quote, 'Not Confirmed'])

		printed_bet = '{} - {} {} @{}'.format(team1, team2, nice_bet, quote)

		return bot.send_message(chat_id=chat_id,
						        text=('{}\n\n' +
						              '/confirm                /cancel').
						              format(printed_bet))
	else:
		return bot.send_message(chat_id=chat_id, text='Match already chosen')


def help_quote(bot, update):  # DONE

	"""
	Instructions to insert the correct bet.

	"""

	chat_id = update.message.chat_id

	f = open('Messages/help_quote.txt', 'r')
	content = f.readlines()
	f.close()

	message = ''
	for row in content:
		message += row

	return bot.send_message(chat_id=chat_id, text=message)


def help_stats(bot, update):  # DONE

	"""
	Instructions to use statistic commands.

	"""

	chat_id = update.message.chat_id

	f = open('Messages/help_stats.txt', 'r')
	content = f.readlines()
	f.close()

	message = format_text(content)

	return bot.send_message(chat_id=chat_id, text=message)


def info(bot, update):  # DONE

	"""
	Send message of general info.

	"""

	chat_id = update.message.chat_id

	f = open('Messages/info.txt', 'r')
	content = f.readlines()
	f.close()

	message = ''
	for row in content:
		message += row

	return bot.send_message(chat_id=chat_id, text=message)


def limits_are_respected(username):  # DONE

	"""
	Check if quotes limits are respected.
	:param username: str

	:return: bool

	"""

	users_allowed = dbf.db_select(
			table='allow',
			columns_in=['allow_name'])

	pred_id, quote = dbf.db_select(
			table='predictions',
			columns_in=['pred_id', 'pred_quote'],
			where=('pred_user = "{}" '.format(username) +
			       'AND pred_status = "Not Confirmed"'))[0]

	if (quote < lim_low or quote > lim_high) and username not in users_allowed:
		dbf.db_delete(
				table='predictions',
				where='pred_id = {}'.format(pred_id))
		return False
	else:
		return True


def match(bot, update, args):  # DONE

	"""
	Return the matches of the requested day.

	"""

	chat_id = update.message.chat_id

	if not args:
		return bot.send_message(chat_id=chat_id,
								text='Insert the day. Ex. /match sab')
	try:
		message = bf.matches_per_day(args[0])
		return bot.send_message(parse_mode='HTML', chat_id=chat_id,
						        text=message)
	except SyntaxError as e:
		return bot.send_message(chat_id=chat_id, text=str(e))


def matiz(bot, update):  # DONE

	"""
	Send matiz photo.

	"""

	chat_id = update.message.chat_id

	return bot.send_photo(chat_id=chat_id, photo=open('matiz.png', 'rb'))


def new_quotes(bot, update, args):

	"""
	Fill the db with the new quotes for the chosen leagues.

	:param bot:
	:param update:
	:param args: list, Ex. [serie a, bundesliga]

	:return:

	"""

	chat_id = update.message.chat_id

	try:
		_, role = nickname(update)
	except AttributeError:
		role = 'Admin'

	if role == 'Admin':
		if not args:
			message = 'Insert leagues. Ex. /new_quotes serie a, ligue 1'
			return bot.send_message(chat_id=chat_id, text=message)

		args = ' '.join(args).split(',')
		args = [arg[1:] if arg[0] == ' ' else arg for arg in args]
		args = [arg[:-1] if arg[-1] == ' ' else arg for arg in args]
		for arg in args:
			if arg.upper() not in sf.countries:
				leagues = ', '.join([league for league in sf.countries])
				return bot.send_message(
						chat_id=chat_id,
						text='Possible options: {}'.format(leagues))

		leagues = [arg.upper() for arg in args]
		for league in leagues:
			league_id = dbf.db_select(
					table='leagues',
					columns_in=['league_id'],
					where='league_name = "{}"'.format(league))[0]

			matches = dbf.db_select(
					table='matches',
					columns_in=['match_id'],
					where='match_league = {}'.format(league_id))

			for match in matches:
				dbf.db_delete(
						table='quotes',
						where='quote_match = {}'.format(match))
				dbf.db_delete(
						table='matches',
						where='match_id = {}'.format(match))

		start = time.time()
		logger.info('NEW_QUOTES - Nightly job: Updating quote...')
		sf.fill_db_with_quotes(leagues)
		end = time.time() - start
		minutes = int(end//60)
		seconds = round(end % 60)
		logger.info('NEW_QUOTES - Whole process took {}:{}.'.format(minutes,
																	seconds))
	else:
		return bot.send_message(chat_id=update.message.chat_id,
		                        text='Fatti i cazzi tuoi')


def nickname(update):

	name = update.message.from_user.first_name

	user, role = dbf.db_select(
			table='people',
			columns_in=['people_nick', 'people_role'],
			where='people_name = "{}"'.format(name))[0]

	return user, role


def night_quotes(bot, update):

	"""
	Fill the db with the new quotes for all the leagues.

	:param bot:
	:param update:

	:return:

	"""

	try:
		_, role = nickname(update)
	except AttributeError:
		role = 'Admin'

	print('a')
	if role == 'Admin':
		leagues = [league for league in sf.countries]

		# Delete old data from the two tables
		dbf.empty_table('quotes')
		dbf.empty_table('matches')

		start = time.time()
		logger.info('NIGHT_QUOTES - Nightly job: Updating quote...')
		sf.fill_db_with_quotes(leagues)
		end = time.time() - start
		minutes = int(end // 60)
		seconds = round(end % 60)
		logger.info('NIGHT_QUOTES - Whole process took {}:{}.'.format(minutes,
		                                                            seconds))
	# else:
	# 	return bot.send_message(chat_id=chat_id, text='Fatti i cazzi tuoi')


def play(bot, update, args):  # DONE

	"""
	Play the bet online.

	:param bot: -
	:param update: -
	:param args: list, amount to play. Ex. [5]

	:return: nothing

	"""
	chat_id = update.message.chat_id

	euros = bf.check_if_input_is_correct(args)
	if type(euros) == str:
		return bot.send_message(chat_id=chat_id, text=euros)

	# Check if there is any bet which has not been confirmed by any user
	warn = bf.one_or_more_preds_are_not_confirmed()
	if warn:
		return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=warn)

	# Check if there is any bet to play and, if yes, select the id
	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
		        where='bet_status = "Pending"')[0]
	except IndexError:
		return bot.send_message(chat_id=chat_id, text='No bets to play.')

	# Check whether there are matches already started
	late = bf.check_if_too_late(bet_id)
	if late:
		return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=late)

	# This message will be updated during the process to keep track of all
	# the steps
	dynamic_message = 'Matches added: {}'
	sent = bot.send_message(chat_id=chat_id, text=dynamic_message.format(0))

	# To identify the message
	mess_id = sent.message_id

	# Create a list with all the preds to play
	# matches_to_play = bf.create_matches_to_play(bet_id)
	matches_to_play = dbf.db_select(table='to_play')

	# Add all the preds to the basket and update the message inside the chat
	browser = None
	for i, (tm1, tm2, field, bet, url) in enumerate(matches_to_play):

		browser = sf.connect_to(some_url=url, browser=browser)
		if not i:
			browser = sf.connect_to(some_url=url, browser=browser)
		basket_msg = sf.add_bet_to_basket(
				browser, (field, bet), i, dynamic_message)
		logger.info('PLAY - {}-{}  {} added'.format(tm1, tm2, bet))

		bot.edit_message_text(
				chat_id=chat_id, message_id=mess_id, text=basket_msg)

	# Insert the amount to bet
	sf.insert_euros(browser, euros)

	# Log in
	sf.login(browser)
	logger.info('PLAY - Logged')
	bot.edit_message_text(chat_id=chat_id, message_id=mess_id, text='Logged')

	# Money left before playing the bet
	money_before = sf.money(browser)

	# Click the button to place the bet
	sf.click_scommetti(browser)
	time.sleep(10)

	# Money after clicking the button
	money_after = sf.money(browser)

	# Verify money has the new value. If not, refresh the value and check again
	# up to 10 times
	c = count(1)
	while next(c) < 10 and money_after != (money_before - euros):
		sf.refresh_money(browser)
		time.sleep(2)
		money_after = sf.money(browser)

	if money_after == money_before - euros:

		logger.info('PLAY - Bet has been played.')

		# Update bet table
		dbf.db_update(
				table='bets',
				columns=['bet_date', 'bet_euros', 'bet_status'],
				values=[datetime.datetime.now(), euros, 'Placed'],
				where='bet_status = "Pending"')

		# Empty table with bets
		dbf.empty_table(table='to_play')

		# Print the summary
		msg = create_summary('after')
		msg += '\nMoney left: <b>{}</b>'.format(money_after)
		bot.send_message(parse_mode='HTML', chat_id=chat_id, text=msg)
	else:
		msg = 'Money left did not change, try again the command /play.'
		bot.send_message(chat_id=update.message.chat_id, text=msg)

	browser.quit()


def remind(bot, update):

	chat_id = update.message.chat_id
	message = create_summary('remind')

	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)


def score(bot, update, args):

	chat_id = update.message.chat_id

	if not args:
		return bot.send_photo(chat_id=chat_id,
		                      photo=open('score_2018-2019.png', 'rb'))
	elif args[0] == 'general':
		return bot.send_photo(chat_id=chat_id,
		                      photo=open('score_GENERAL.png', 'rb'))
	else:
		try:
			return bot.send_photo(
					chat_id=chat_id,
					photo=open('score_{}.png'.format(args[0]), 'rb'))
		except FileNotFoundError:
			return bot.send_message(
					chat_id=chat_id,
					text='Wrong format. Ex: 2017-2018 or "general"')


def send_log(bot, update):

	chat_id = update.message.chat_id

	return bot.send_document(chat_id=chat_id,
	                         document=open('logs/bet_bot.log', 'rb'))


def series(bot, update):

	chat_id = update.message.chat_id

	return bot.send_photo(chat_id=chat_id, photo=open('series.png', 'rb'))


def sotm(bot, update):

	chat_id = update.message.chat_id
	return bot.send_photo(chat_id=chat_id, photo=open('sotm.png', 'rb'))


def start(bot, update):

	chat_id = update.message.chat_id
	return bot.send_message(chat_id=chat_id, text="Iannelli suca")


def stats(bot, update):

	chat_id = update.message.chat_id

	message_money = stf.money()
	message_perc = stf.abs_perc()
	message_teams = stf.stats_on_teams()
	message_bets = stf.stats_on_bets()
	message_quotes = stf.stats_on_quotes()
	message_combos = stf.stats_on_combos()

	fin_mess = (message_money + message_perc + message_teams +
	            message_bets + message_quotes + message_combos)

	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=fin_mess)


def summary(bot, update):

	chat_id = update.message.chat_id

	message = create_summary('before')

	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)


def update_results(bot, update):

	"""
	Updates the columns "bet_result", "pred_result" and "pred_label" in the
	database.
	"""

	chat_id = update.message.chat_id

	ref_list = dbf.db_select(
			table='bets',
			columns_in=['bet_id', 'bet_date'],
			where='bet_status = "Placed" AND bet_result = "Unknown"')
	logger.info('UPDATE - Selecting Placed bets...')

	if not ref_list:
		logger.info('UPDATE - No bets must be updated')
		return bot.send_message(chat_id=chat_id, text='No bets to update.')

	try:
		browser = sf.go_to_lottomatica()
	except ConnectionError as e:
		return bot.send_message(chat_id=chat_id, text=e)
	time.sleep(3)

	sf.login(browser)
	time.sleep(3)

	try:
		sf.go_to_personal_area(browser, 0)

		sf.go_to_placed_bets(browser, 0)

		bets_updated = sf.analyze_main_table(browser, ref_list, 0)

	except ConnectionError as e:
		browser.quit()
		return bot.send_message(chat_id=chat_id, text=str(e))

	browser.quit()

	if bets_updated:
		cl.bets, cl.preds = cl.update_bets_preds()
		cl.players = {name: cl.Player(name) for name in cl.partecipants}
		cl.stats = cl.Stats()
		logger.info('UPDATE - Database updated correctly.')
	else:
		logger.info('No completed bets were found.')


allow_handler = CommandHandler('allow', allow, pass_args=True)
cake_handler = CommandHandler('cake', cake)
bici_handler = CommandHandler('bici', bike)
cancel_handler = CommandHandler('cancel', cancel)
confirm_handler = CommandHandler('confirm', confirm)
delete_handler = CommandHandler('delete', delete)
fischia_handler = CommandHandler('fischia', fischia)
get_handler = CommandHandler('get', get, pass_args=True)
help_quote_handler = CommandHandler('help_quote', help_quote)
help_stats_handler = CommandHandler('help_stats', help_stats)
info_handler = CommandHandler('info', info)
log_handler = CommandHandler('log', send_log)
match_handler = CommandHandler('match', match, pass_args=True)
matiz_handler = CommandHandler('matiz', matiz)
new_quotes_handler = CommandHandler('new_quotes', new_quotes, pass_args=True)
night_quotes_handler = CommandHandler('night_quotes', night_quotes)
play_handler = CommandHandler('play', play, pass_args=True)
remind_handler = CommandHandler('remind', remind)
score_handler = CommandHandler('score', score, pass_args=True)
series_handler = CommandHandler('series', series)
sotm_handler = CommandHandler('sotm', sotm)
start_handler = CommandHandler('start', start)
stats_handler = CommandHandler('stats', stats)
summary_handler = CommandHandler('summary', summary)
update_handler = CommandHandler('update', update_results)

# Nightly quotes updating
update_quotes = updater.job_queue
update_quotes.run_repeating(night_quotes, 86400,
                            first=datetime.time(1, 00, 00))

update_tables = updater.job_queue
update_tables.run_repeating(update_results, 86400,
							first=datetime.time(5, 00, 00))

dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_quote_handler)
dispatcher.add_handler(help_stats_handler)
dispatcher.add_handler(info_handler)
dispatcher.add_handler(get_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(delete_handler)
dispatcher.add_handler(play_handler)
dispatcher.add_handler(update_handler)
dispatcher.add_handler(summary_handler)
dispatcher.add_handler(score_handler)
dispatcher.add_handler(cake_handler)
dispatcher.add_handler(bici_handler)
dispatcher.add_handler(series_handler)
dispatcher.add_handler(stats_handler)
dispatcher.add_handler(sotm_handler)
dispatcher.add_handler(match_handler)
dispatcher.add_handler(new_quotes_handler)
dispatcher.add_handler(night_quotes_handler)
dispatcher.add_handler(log_handler)
dispatcher.add_handler(remind_handler)
dispatcher.add_handler(matiz_handler)
dispatcher.add_handler(fischia_handler)
dispatcher.add_handler(allow_handler)

logger = log.set_logging()
updater.start_polling()
logger.info('Bet_Bot started.')
updater.idle()
