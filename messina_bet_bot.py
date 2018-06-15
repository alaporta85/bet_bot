import time
import datetime
import numpy as np
from telegram.ext import Updater
from telegram.ext import CommandHandler
from selenium.common.exceptions import NoSuchElementException
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import bot_functions as bf
from Functions import stats_functions as stf
from Functions import logging as log
import Classes as cl
from nltk.metrics.distance import jaccard_distance
from nltk.util import ngrams

f = open('token.txt', 'r')
updater = Updater(token=f.readline())
f.close()

dispatcher = updater.dispatcher


def cake(bot, update):

	bot.send_photo(chat_id=update.message.chat_id, photo=open('cake.png',
	                                                          'rb'))


def cancel(bot, update):

	"""Delete the "Not Confirmed" bet from "predictions" table."""

	first_name = nickname(update.message.from_user.first_name)

	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if first_name not in users_list:
		return bot.send_message(chat_id=update.message.chat_id,
								text='{}, you have no bet to cancel.'
								.format(first_name))

	dbf.db_delete(
			table='predictions',
	        where='pred_user = "{}" AND pred_status = "Not Confirmed"'.
	        format(first_name))

	return bot.send_message(
			chat_id=update.message.chat_id,
			text='{}, your bet has been canceled.'.format(first_name))


def confirm(bot, update):

	"""
	Update the status of the bet in the "predictions" table from
	"Not Confirmed" to "Confirmed". If it is the first bet of the day it
	creates a new entry in the "bets" table and update the bet_id in the
	"predictions" table. Else, it just uses the bet_id. It also checks
	whether there are others "Not Confirmed" bets of the same match. If yes,
	they will be deleted from the "predictions" table.
	"""

	first_name = nickname(update.message.from_user.first_name)

	# This a list of the users who have their bets in the status
	# 'Not Confirmed'
	users_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user'],
	        where='pred_status = "Not Confirmed"')

	if first_name not in users_list:
		return bot.send_message(
				chat_id=update.message.chat_id,
				text='{}, no bet to confirm.'.format(first_name))

	# Check if there is any bet with status 'Pending' in the 'bets' table
	try:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
		        where='bet_status = "Pending"')[0]
	except IndexError:
		bet_id = dbf.db_insert(
				table='bets',
				columns='(bet_status, bet_result)',
				values='("Pending", "Unknown")',
				last_row=True)

	details = bf.update_pred_table_after_confirm(first_name, bet_id)

	dupl_message = bf.check_if_duplicate(first_name, details)
	if dupl_message:
		bot.send_message(chat_id=update.message.chat_id, text=dupl_message)

	return bot.send_message(chat_id=update.message.chat_id,
					        text='{}, your bet has been placed correctly.'
					        .format(first_name))


def create_summary(string):

	if string == 'before':
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Pending"')
	else:
		bet_id = dbf.db_select(
				table='bets',
				columns_in=['bet_id'],
				where='bet_status = "Placed" AND bet_result = "Unknown"')[-1]

	if string == 'before' and not bet_id:
		return 'No bets yet. Choose the first one.'

	bet_id = bet_id if not type(bet_id) == list else bet_id[0]
	summary = dbf.db_select(
			table='bets INNER JOIN predictions on pred_bet = bet_id',
			columns_in=['pred_user', 'pred_date', 'pred_team1', 'pred_team2',
			            'pred_rawbet', 'pred_quote'],
			where='bet_id = {}'.format(bet_id))

	summary = sorted(summary, key=lambda x: x[1])

	message = ''
	for user, dt, team1, team2, rawbet, quote in summary:

		dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
		hhmm = str(dt.hour).zfill(2) + ':' + str(dt.minute).zfill(2)

		message += '{}:     {}-{} ({})    {}      @<b>{}</b>\n'.format(
				user, team1, team2, hhmm, rawbet, quote)

	final_quote = np.prod(np.array([el[5] for el in summary]))
	if string == 'before':
		message2 = '\n\nPossible win with 5 euros: <b>{:.1f}</b>'.format(
				final_quote * 5)
		return message + message2
	elif string == 'after':
		message = 'Bet placed correctly.\n\n' + message
		message += '\nPossible win: <b>{:.1f}</b>'.format(final_quote * 5)
		return message


def delete(bot, update):

	"""Delete the "Confirmed" bet from "predictions" table."""

	first_name = nickname(update.message.from_user.first_name)

	bet_id = dbf.db_select(
			table='bets',
			columns_in=['bet_id'],
	        where='bet_status = "Pending"')
	if not bet_id:
		return bot.send_message(chat_id=update.message.chat_id,
								text='There are no "Pending" bets.')

	bet_id = bet_id[0]

	bet_to_delete = dbf.db_select(
			table='predictions',
			columns_in=['pred_id'],
			where=('pred_bet = {} AND pred_user = "{}" AND ' +
			       'pred_status = "Confirmed"').format(bet_id, first_name))

	if not bet_to_delete:
		message = '{}, you have no bet to delete.'.format(first_name)
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
			text='{}, your bet has been deleted.'.format(first_name))


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

	if not args:
		return bot.send_message(chat_id=update.message.chat_id,
								text='Please insert the bet.')

	guess = ' '.join(args).upper()

	if guess[0] == '_' or guess[-1] == '_':
		return bot.send_message(chat_id=update.message.chat_id,
								text='Wrong format.')

	try:
		input_team, input_bet = guess.split('_')
		input_bet = input_bet.replace(' ', '').replace(',', '.')
	except ValueError:
		input_team, input_bet = (guess, '')

	team_name = jaccard_team(input_team)
	if '*' in team_name:
		league_id = 8
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

	# User sending the message
	first_name = nickname(update.message.from_user.first_name)

	warning_message = bf.check_still_to_confirm(first_name)
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
	except IndexError:
		bet_id = 0

	confirmed_matches = dbf.db_select(
			table='predictions',
			columns_in=['pred_team1', 'pred_team2'],
			where='pred_status = "Confirmed" AND pred_bet = {}'.format(bet_id))

	team1, team2, field_id, nice_bet, quote = bf.look_for_quote(team_name,
	                                                            input_bet)

	if (not confirmed_matches
	   or (team1, team2) not in confirmed_matches):

		dt = dbf.db_select(
				table='matches',
				columns_in=['match_date'],
				where='match_team1 = "{}" AND match_team2 = "{}"'.
				format(team1, team2))[0]

		team1 = team1.replace('*', '')
		team2 = team2.replace('*', '')

		# Update table
		dbf.db_insert(
				table='predictions',
				columns=('(pred_user, pred_date, pred_team1, pred_team2, ' +
				         'pred_league, pred_field, pred_rawbet, pred_quote, ' +
				         'pred_status)'),
				values='("{}", "{}", "{}", "{}", {}, {}, "{}", {}, "{}")'.
				format(first_name, dt, team1, team2, league_id, field_id,
				       nice_bet, quote, 'Not Confirmed'))

		printed_bet = '{} - {} {} @{}'.format(team1, team2, nice_bet,
											  quote)

		return bot.send_message(chat_id=update.message.chat_id,
						        text=('{}\n' + 'Use /confirm or /cancel ' +
							   'to finalize your bet.').format(
								                              printed_bet))
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


def jaccard_team(string):

	teams = dbf.db_select(
			table='teams_alias',
			columns_in=['team_alias_team', 'team_alias_name'])

	dist = 10
	tri_guess = set(ngrams(string, 3))
	team_id = 0

	for i, t in teams:
		trit = set(ngrams(t, 3))
		jd = jaccard_distance(tri_guess, trit)
		if jd < dist:
			dist = jd
			team_id = i

	team = dbf.db_select(
			table='teams',
			columns_in=['team_name'],
			where='team_id = {}'.format(team_id))[0]

	return team


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


def new_quotes(bot, update):

	"""Fill the db with the new quotes."""

	start = time.time()
	logger.info('NEW_QUOTES - Nightly job: Updating quote...')
	sf.fill_db_with_quotes()
	end = time.time() - start
	minutes = int(end//60)
	seconds = round(end % 60)
	logger.info('NEW_QUOTES - Whole process took {}:{}.'.format(minutes,
																seconds))


def nickname(name):

	nicknames = {'Andrea': 'Testazza',
				 'Fabrizio': 'Nonno',
				 'Damiano': 'Pacco',
				 'Francesco': 'Zoppo',
				 'Gabriele': 'Nano'}

	return nicknames[name]


def play(bot, update, args):

	"""
	Manage the login and play the bet. Args input is the amount of euros
	to bet.
	"""

	if not args:
		return bot.send_message(chat_id=update.message.chat_id, text=(
				'Please insert the amount to bet. Ex: /play 5'))
	try:
		euros = int(args[0])
		if euros < 2:
			message = 'Minimum amount is 2 Euros.'
			return bot.send_message(chat_id=update.message.chat_id,
									text=message)
	except ValueError:
		message = 'Amount has to be integer.'
		return bot.send_message(chat_id=update.message.chat_id,
								text=message)

	not_conf_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user', 'pred_team1', 'pred_team2', 'pred_field',
			            'pred_rawbet'],
			where='pred_status = "Not Confirmed"')

	if not_conf_list:
		bot.send_message(chat_id=update.message.chat_id,
						 text='There are still Not Confirmed bets:')
		for match in not_conf_list:
			bot.send_message(chat_id=update.message.chat_id,
							 text=('{}\n{} - {}\n{}\n{}'.format(match[0],
								   match[1], match[2], match[3], match[4])))

		return bot.send_message(chat_id=update.message.chat_id,
								text=('/confirm or /cancel each of them and ' +
									  'then play again.'))

	# bet_id of the Pending bet
	bet_id = dbf.db_select(
			table='bets',
			columns_in=['bet_id'],
	        where='bet_status = "Pending"')[0]
	if not bet_id:
		return bot.send_message(chat_id=update.message.chat_id,
								text='No bets to play.')

	# Check whether there are matches already started
	invalid_bets = dbf.check_before_play(bet_id)
	if invalid_bets:
		message = '{}, {} - {} was scheduled on {} at {}. Too late.'
		for x in range(len(invalid_bets)):
			bet = invalid_bets[x]
			dt = datetime.datetime.strptime(bet[1], '%Y-%m-%d %H:%M:%S')
			date_to_print = (str(dt.year) + '/' + str(dt.month) + '/' +
			                 str(dt.day))
			time_to_print = (str(dt.hour) + ':' + str(dt.minute))
			if x < len(invalid_bets) - 1:
				logger.info('PLAY - Too late for the following bet: ' +
							'{}: {} - {}.'.format(bet[0], bet[2], bet[3]))
				bot.send_message(chat_id=update.message.chat_id,
								 text=message.format(bet[0], bet[2], bet[3],
													 date_to_print,
													 time_to_print))
			else:
				return bot.send_message(chat_id=update.message.chat_id,
										text=message.format(bet[0], bet[1],
															bet[2],
															date_to_print,
															time_to_print))

	# This message will be updated during the process to keep track of all
	# the steps
	dynamic_message = 'Please wait while placing the bet.\nMatches added: {}'
	sent = bot.send_message(chat_id=update.message.chat_id,
							text=dynamic_message.format(0))

	# mess_id will be used to update the message
	mess_id = sent.message_id

	matches_to_play = bf.create_matches_to_play(bet_id)

	browser = sf.go_to_lottomatica(0)
	logger.info('PLAY - Connected to Lottomatica')
	count = 0
	for match in matches_to_play:
		try:
			basket_message = sf.add_bet_to_basket(browser, match, count,
												  dynamic_message)
			logger.info('PLAY - {}-{}  {} '.format(
					match[0], match[1], match[3]) + 'added')

			bot.edit_message_text(chat_id=update.message.chat_id,
								  message_id=mess_id, text=basket_message)
			count += 1
		except ConnectionError as e:
			logger.info('PLAY - Problems adding {}'.format(match))
			return bot.send_message(chat_id=update.message.chat_id,
									text=str(e))

	logger.info('PLAY - All matches added')
	time.sleep(5)
	bot.edit_message_text(chat_id=update.message.chat_id, message_id=mess_id,
						  text='Checking everything is fine...')

	sf.insert_euros(browser, euros)

	sf.login(browser)
	logger.info('PLAY - Logged in')
	bot.edit_message_text(chat_id=update.message.chat_id,
						  message_id=mess_id,
						  text='Logged in')

	# Money left before playing the bet
	money_before = sf.money(browser)

	try:
		sf.find_scommetti_box(browser)
	except ConnectionError as e:
		browser.quit()
		logger.info(str(e))
		return bot.send_message(chat_id=update.message.chat_id, text=str(e))

	logger.info('PLAY - Bet has been played.')
	dbf.db_update(
			table='bets',
			columns=('bet_date = "{}", bet_euros = {}, ' +
					 'bet_status = "{}"').format(
					datetime.datetime.now(), euros, 'Placed'),
			where='bet_status = "Pending"')
	logger.info('PLAY - "bets" db table updated')

	bot.edit_message_text(chat_id=update.message.chat_id,
						  message_id=mess_id, text='Done!')

	time.sleep(30)

	# Money after playing the bet
	money_after = sf.money(browser)

	if money_after == money_before - euros:

		# Print the summary
		message = create_summary('after')
		message += '\nMoney left: <b>{}</b>'.format(money_after)
		bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
						 text=message)
	else:
			bot.send_message(chat_id=update.message.chat_id,
			                 text=('Money left did not change, try again ' +
			                       'the command /play.'))

	browser.quit()


def score(bot, update):

	bot.send_photo(chat_id=update.message.chat_id, photo=open('score.png',
															  'rb'))


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

	message = create_summary('before')
	return bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
	                        text=message)


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

	browser = sf.go_to_lottomatica(0)
	time.sleep(3)

	sf.login(browser)
	time.sleep(3)

	# Close popup
	try:
		cancel = './/a[@id="id-popup-quote-stellari-btnAnnulla"]'
		browser.find_element_by_xpath(cancel).click()
	except NoSuchElementException:
		pass

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


start_handler = CommandHandler('start', start)
help_quote_handler = CommandHandler('help_quote', help_quote)
help_stats_handler = CommandHandler('help_stats', help_stats)
info_handler = CommandHandler('info', info)
get_handler = CommandHandler('get', get, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
delete_handler = CommandHandler('delete', delete)
play_handler = CommandHandler('play', play, pass_args=True)
update_handler = CommandHandler('update', update_results)
summary_handler = CommandHandler('summary', summary)
score_handler = CommandHandler('score', score)
cake_handler = CommandHandler('cake', cake)
series_handler = CommandHandler('series', series)
stats_handler = CommandHandler('stats', stats)
sotm_handler = CommandHandler('sotm', sotm)
match_handler = CommandHandler('match', match, pass_args=True)
new_quotes_handler = CommandHandler('new_quotes', new_quotes)
log_handler = CommandHandler('log', send_log)

# Nightly quotes updating
update_quotes = updater.job_queue
update_quotes.run_repeating(new_quotes, 86400, first=datetime.time(1, 00, 00))

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
dispatcher.add_handler(series_handler)
dispatcher.add_handler(stats_handler)
dispatcher.add_handler(sotm_handler)
dispatcher.add_handler(match_handler)
dispatcher.add_handler(new_quotes_handler)
dispatcher.add_handler(log_handler)

logger = log.set_logging()
updater.start_polling()
logger.info('Bet_Bot started.')
updater.idle()
