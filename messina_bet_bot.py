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

dispatcher = updater.dispatcher


def cake(bot, update):

	bot.send_photo(chat_id=update.message.chat_id, photo=open('cake.png', 'rb'))


def bici(bot, update):

	bot.send_audio(chat_id=update.message.chat_id, audio=open('bici.mp3', 'rb'))


def cancel(bot, update):

	"""Delete the "Not Confirmed" bet from "predictions" table."""

	user, _ = nickname(update)

	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if user not in users_list:
		return bot.send_message(chat_id=update.message.chat_id,
								text='{}, no bet to cancel.'.format(user))

	dbf.db_delete(
			table='predictions',
	        where='pred_user = "{}" AND pred_status = "Not Confirmed"'.
	        format(user))

	return bot.send_message(
			chat_id=update.message.chat_id,
			text='{}, bet canceled.'.format(user))


def confirm(bot, update):

	"""
	Update the status of the bet in the "predictions" table from
	"Not Confirmed" to "Confirmed". If it is the first bet of the day it
	creates a new entry in the "bets" table and update the bet_id in the
	"predictions" table. Else, it just uses the bet_id. It also checks
	whether there are others "Not Confirmed" bets of the same match. If yes,
	they will be deleted from the "predictions" table.
	"""

	user, _ = nickname(update)

	# This a list of the users who have their bets in the status
	# 'Not Confirmed'
	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if user not in users_list:
		return bot.send_message(
				chat_id=update.message.chat_id,
				text='{}, no bet to confirm.'.format(user))

	# Check if there is any bet with status 'Pending' in the 'bets' table
	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
		        where='bet_status = "Pending"')[0]
	except IndexError:
		bet_id = dbf.db_insert(
				table='bets',
				columns=['bet_status', 'bet_result'],
				values=['Pending', 'Unknown'],
				last_row=True)

	details = bf.update_pred_table_after_confirm(user, bet_id)

	dupl_message = bf.check_if_duplicate(user, details)
	if dupl_message:
		bot.send_message(chat_id=update.message.chat_id, text=dupl_message)

	bot.send_message(chat_id=update.message.chat_id,
	                 text='{}, bet placed correctly.'.format(user))

	auto_play = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where='pred_bet = {}'.format(bet_id))
	if len(auto_play) == 5:
		return play(bot, update, ['5'])


def create_summary(string):

	if string == 'before':
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')
	elif string == 'after':
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Placed" AND bet_result = "Unknown"')[-1]
	else:
		message = 'Following bets are still incomplete:\n\n'

		unknown_bets = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Placed" AND bet_result = "Unknown"')
		for bet_id in unknown_bets:
			message2, final_quote = create_summary_message(bet_id)
			message += ('{}\nPossible win: <b>{:.1f}</b>\n\n\n'.
			            format(message2, final_quote * 5))

		return message

	if string == 'before' and not bet_id:
		return 'No bets yet. Choose the first one.'

	bet_id = bet_id if not type(bet_id) == list else bet_id[-1]
	message, final_quote = create_summary_message(bet_id)

	if string == 'before':
		message2 = '\n\nPossible win with 5 euros: <b>{:.1f}</b>'.format(
				final_quote * 5)
		return message + message2
	elif string == 'after':
		message = 'Bet placed correctly.\n\n' + message
		message += '\nPossible win: <b>{:.1f}</b>'.format(final_quote * 5)
		return message


def create_summary_message(bet_id):

	message = ''

	summary = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_user', 'pred_date', 'pred_team1',
			            'pred_team2',
			            'pred_rawbet', 'pred_quote'],
			where='bet_id = {}'.format(bet_id))
	summary = sorted(summary, key=lambda x: x[1])
	final_quote = np.prod(np.array([el[5] for el in summary]))
	for user, dt, team1, team2, rawbet, quote in summary:
		dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
		hhmm = str(dt.hour).zfill(2) + ':' + str(dt.minute).zfill(2)

		message += '<b>{}</b>:     {}-{} ({})    {}      @<b>{}</b>\n'.format(
				user, team1, team2, hhmm, rawbet, quote)

	return message, final_quote


def delete(bot, update):

	"""Delete the "Confirmed" bet from "predictions" table."""

	user, _ = nickname(update)

	bet_id = dbf.db_select(
			table='bets',
			columns_in=['bet_id'],
	        where='bet_status = "Pending"')
	if not bet_id:
		return bot.send_message(chat_id=update.message.chat_id,
								text='No "Pending" bets.')

	bet_id = bet_id[0]

	bet_to_delete = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where=('pred_bet = {} AND pred_user = "{}" AND ' +
			       'pred_status = "Confirmed"').format(bet_id, user))

	if not bet_to_delete:
		message = '{}, no bet to delete.'.format(user)
		return bot.send_message(chat_id=update.message.chat_id,
								text=message)

	dbf.db_delete(
			table='predictions',
			where='pred_id = {}'.format(bet_to_delete[0]))

	conf_bets_left = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where='pred_status = "Confirmed" AND pred_bet = {}'.format(bet_id))

	if not conf_bets_left:
		dbf.db_delete(
				table='bets',
		        where='bet_id = {}'.format(bet_id))

	return bot.send_message(
			chat_id=update.message.chat_id,
			text='{}, bet deleted.'.format(user))


def fischia(bot, update):

	walter = random.choice(os.listdir('Mazzarri/'))

	bot.send_photo(chat_id=update.message.chat_id,
	               photo=open('Mazzarri/' + walter, 'rb'))


def format_text(content):

	"""Called inside help_stats() function to clean the message text."""

	message = ''.join(content)
	message = message.replace('\n\n', 'xx')
	message = message.replace('\n', ' ')
	message = message.replace('xx', '\n\n')

	return message


def get(bot, update, args):

	"""
	Update the table "predictions" in the db with the data relative to the
	chosen match. pred_status will be set to "Not Confirmed".
	"""
	logger.info('Get Request Received')

	if not args:
		return bot.send_message(chat_id=update.message.chat_id,
								text='Insert the bet.')

	guess = ' '.join(args).upper()

	if guess[0] == '_' or guess[-1] == '_':
		return bot.send_message(chat_id=update.message.chat_id,
								text='Wrong format.')

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
		input_team, input_bet = (guess, '')

	team_name = dbf.select_team(input_team)

	if not team_name:
		return bot.send_message(chat_id=update.message.chat_id,
		                        text='Squadra non trovata')
	elif '*' in input_team:
		league_id = 8
		team_name = '*' + team_name
	else:
		league_id = dbf.db_select(
				table='teams',
				columns_in=['team_league'],
				where='team_name = "{}" AND team_league != 8'.
				format(team_name))[0]

	if not input_bet:
		try:
			message_standard, message_combo = bf.all_bets_per_team(team_name,
			                                                       league_id)
		except ValueError as e:
			message = str(e)
			return bot.send_message(chat_id=update.message.chat_id,
			                        text=message)

		bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
						 text=message_standard)
		return bot.send_message(parse_mode='HTML',
								chat_id=update.message.chat_id,
								text=message_combo)

	user, _ = nickname(update)

	warning_message = bf.check_still_to_confirm(user)
	if warning_message:
		return bot.send_message(chat_id=update.message.chat_id,
								text=warning_message)

	# Used to create the list confirmed_matches. This list will be used to
	# check whether a match has already been chosen
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

	try:
		team1, team2, field_id, nice_bet, quote = bf.look_for_quote(team_name,
		                                                            input_bet)
	except ValueError as e:
		return bot.send_message(chat_id=update.message.chat_id, text=str(e))

	if (not confirmed_matches
	   or (team1, team2) not in confirmed_matches):

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

		return bot.send_message(chat_id=update.message.chat_id,
						        text=('{}\n\n' +
						              '/confirm                /cancel').
						              format(printed_bet))
	else:
		message = 'Match already chosen.'
		return bot.send_message(chat_id=update.message.chat_id,
		                        text=message)


def help_quote(bot, update):

	"""Instructions to insert the correct bet."""

	f = open('Messages/help_quote.txt', 'r')
	content = f.readlines()
	f.close()

	message = ''
	for row in content:
		message += row

	bot.send_message(chat_id=update.message.chat_id, text=message)


def help_stats(bot, update):

	"""Instructions to use statistic commands."""

	f = open('Messages/help_stats.txt', 'r')
	content = f.readlines()
	f.close()

	message = format_text(content)

	bot.send_message(chat_id=update.message.chat_id, text=message)


def info(bot, update):

	f = open('Messages/info.txt', 'r')
	content = f.readlines()
	f.close()

	message = ''
	for row in content:
		message += row

	bot.send_message(chat_id=update.message.chat_id, text=message)


def match(bot, update, args):

	"""Return the matches of the requested day."""

	if not args:
		return bot.send_message(chat_id=update.message.chat_id,
								text='Insert the day. Ex. /match sab')
	try:
		message = bf.matches_per_day(args[0])
		bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
						 text=message)
	except SyntaxError as e:
		return bot.send_message(chat_id=update.message.chat_id, text=str(e))


def matiz(bot, update):

	bot.send_photo(chat_id=update.message.chat_id,
	               photo=open('matiz.png', 'rb'))


# def new_quotes(bot, update):
#
# 	"""
# 	Fill the db with the new quotes for the chosen leagues.
#
# 	:param bot:
# 	:param update:
#
# 	:return:
#
# 	"""
#
# 	try:
# 		_, role = nickname(update)
# 	except AttributeError:
# 		role = 'Admin'
#
# 	if role == 'Admin':
#
# 		# Delete old data from the two tables
# 		dbf.empty_table('quotes')
# 		dbf.empty_table('matches')
#
# 		start = time.time()
# 		logger.info('NEW_QUOTES - Nightly job: Updating quote...')
# 		sf.fill_db_with_quotes()
# 		end = time.time() - start
# 		minutes = int(end//60)
# 		seconds = round(end % 60)
# 		logger.info('NEW_QUOTES - Whole process took {}:{}.'.format(minutes,
# 																	seconds))
# 	else:
# 		return bot.send_message(chat_id=update.message.chat_id,
# 		                        text='Fatti i cazzi tuoi')



def new_quotes(bot, update, args):

	"""
	Fill the db with the new quotes for the chosen leagues.

	:param bot:
	:param update:
	:param args: list, Ex. [serie a, bundesliga]

	:return:

	"""

	try:
		_, role = nickname(update)
	except AttributeError:
		role = 'Admin'

	if role == 'Admin':
		if not args:
			return bot.send_message(
					chat_id=update.message.chat_id,
					text=('Insert leagues. ' +
					      'Ex. /new_quotes serie a, primera division'))

		args = ' '.join(args).split(',')
		args = [arg[1:] if arg[0] == ' ' else arg for arg in args]
		args = [arg[:-1] if arg[-1] == ' ' else arg for arg in args]
		for arg in args:
			if arg.upper() not in sf.countries:
				leagues = ', '.join([league for league in sf.countries])
				return bot.send_message(
						chat_id=update.message.chat_id,
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
	else:
		return bot.send_message(chat_id=update.message.chat_id,
		                        text='Fatti i cazzi tuoi')


def play(bot, update, args):    # DONE

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
	matches_to_play = bf.create_matches_to_play(bet_id)

	# Add all the preds to the basket and update the message inside the chat
	browser = None
	for i, (tm1, tm2, field, bet, url) in enumerate(matches_to_play):

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
	logger.info('PLAY - Bet has been played.')

	# Update bet table
	dbf.db_update(
			table='bets',
			columns=['bet_date', 'bet_euros', 'bet_status'],
			values=[datetime.datetime.now(), euros, 'Placed'],
			where='bet_status = "Pending"')

	# Let the chat know and then wait
	bot.edit_message_text(chat_id=chat_id, message_id=mess_id, text='Done!')
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

		# Print the summary
		msg = create_summary('after')
		msg += '\nMoney left: <b>{}</b>'.format(money_after)
		bot.send_message(parse_mode='HTML', chat_id=chat_id, text=msg)
	else:
		msg = 'Money left did not change, try again the command /play.'
		bot.send_message(chat_id=update.message.chat_id, text=msg)

	browser.quit()


def remind(bot, update):

	message = create_summary('resume')

	return bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
	                        text=message)


def score(bot, update, args):

	if not args:
		bot.send_photo(chat_id=update.message.chat_id,
		               photo=open('score_2018-2019.png', 'rb'))
	elif args[0] == 'general':
		bot.send_photo(chat_id=update.message.chat_id,
		               photo=open('score_GENERAL.png', 'rb'))
	else:
		try:
			bot.send_photo(chat_id=update.message.chat_id,
			               photo=open('score_{}.png'.format(args[0]), 'rb'))
		except FileNotFoundError:
			bot.send_message(chat_id=update.message.chat_id,
			                 text='Wrong format. Ex: 2017-2018 or "general"')


def send_log(bot, update):

	bot.send_document(chat_id=update.message.chat_id,
	                  document=open('logs/bet_bot.log', 'rb'))


def series(bot, update):

	bot.send_photo(chat_id=update.message.chat_id, photo=open('series.png',
															  'rb'))


def sotm(bot, update):
	bot.send_photo(chat_id=update.message.chat_id, photo=open('sotm.png',
	                                                          'rb'))


def start(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def stats(bot, update):

	message_money = stf.money()
	message_perc = stf.abs_perc()
	message_teams = stf.stats_on_teams()
	message_bets = stf.stats_on_bets()
	message_quotes = stf.stats_on_quotes()
	message_combos = stf.stats_on_combos()

	fin_mess = (message_money + message_perc + message_teams +
	            message_bets + message_quotes + message_combos)

	bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
	                 text=fin_mess)


def summary(bot, update):

	logger.info('PROVA1')
	message = create_summary('before')
	logger.info('PROVA2')
	sent = bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
	                        text=message)
	logger.info('INFO - SUMMARY Datetime of the message is:')
	logger.info('{}'.format(sent.date))


def update_results(bot, update):

	"""
	Updates the columns "bet_result", "pred_result" and "pred_label" in the
	database.
	"""

	ref_list = dbf.db_select(
			table='bets',
			columns_in=['bet_id', 'bet_date'],
			where='bet_status = "Placed" AND bet_result = "Unknown"')
	logger.info('UPDATE - Selecting Placed bets...')

	if not ref_list:
		logger.info('UPDATE - No bets must be updated')
		return bot.send_message(chat_id=update.message.chat_id,
								text='No bets to update.')

	try:
		browser = sf.go_to_lottomatica()
	except ConnectionError as e:
		return bot.send_message(chat_id=update.message.chat_id, text=e)
	time.sleep(3)

	sf.login(browser)
	time.sleep(3)

	try:
		sf.go_to_personal_area(browser, 0)

		sf.go_to_placed_bets(browser, 0)

		bets_updated = sf.analyze_main_table(browser, ref_list, 0)

	except ConnectionError as e:
		browser.quit()
		return bot.send_message(chat_id=update.message.chat_id, text=str(e))

	browser.quit()

	if bets_updated:
		cl.bets, cl.preds = cl.update_bets_preds()
		cl.players = {name: cl.Player(name) for name in cl.partecipants}
		cl.stats = cl.Stats()
		logger.info('UPDATE - Database updated correctly.')
	else:
		logger.info('No completed bets were found.')


cake_handler = CommandHandler('cake', cake)
bici_handler = CommandHandler('bici', bici)
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

logger = log.set_logging()
updater.start_polling()
logger.info('Bet_Bot started.')
updater.idle()
