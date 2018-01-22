import os
import time
import datetime
from telegram.ext import Updater
from telegram.ext import CommandHandler
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import bot_functions as bf
from Functions import stats_functions as stf
from Functions import logging as log

f = open('token.txt', 'r')
updater = Updater(token=f.readline())
f.close()

dispatcher = updater.dispatcher


def nickname(name):

	nicknames = {'Andrea': 'Testazza',
				 'Fabrizio': 'Nonno',
				 'Damiano': 'Pacco',
				 'Francesco': 'Zoppo',
				 'Gabriele': 'Nano'}

	return nicknames[name]


def played_bets(summary):

	"""Return bets played until that moment."""

	message = ''
	for bet in summary:
		user = bet[0]
		team1 = bet[1].title()
		team2 = bet[2].title()
		time = str(bet[3])[:2] + ':' + str(bet[3])[2:]
		rawbet = bet[4]
		quote = bet[5]
		message += '{}:     {}-{} ({})    {}      @<b>{}</b>\n'.format(user,
																	   team1,
																	   team2,
																	   time,
																	   rawbet,
																	   quote)

	return message


def start(bot, update):
	bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def format_text(content):

	"""Called inside help_stats() function to clean the message text."""

	message = ''.join(content)
	message = message.replace('\n\n', 'xx')
	message = message.replace('\n', ' ')
	message = message.replace('xx', '\n\n')

	return message


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


def alias(bot, update):

	"""Show all alias for each team."""

	message = sf.alias()
	bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
	                 text=message)


def info(bot, update):

	f = open('Messages/info.txt', 'r')
	content = f.readlines()
	f.close()

	message = ''
	for row in content:
		message += row

	bot.send_message(chat_id=update.message.chat_id, text=message)


def get(bot, update, args):

	"""
	Update the table "predictions" in the db with the data relative to the
	chosen match. pred_status will be set to "Not Confirmed".
	"""

	if not args:
		return bot.send_message(chat_id=update.message.chat_id,
								text='Please insert the bet.')

	guess = ' '.join(args).upper()

	if '_' not in guess:

		db, c = dbf.start_db()
		team_id = list(c.execute('''SELECT team_alias_team FROM teams_alias
								 WHERE team_alias_name = ?''', (guess,)))
		if team_id:
			team_id = team_id[0][0]
			team_name, league_id = list(c.execute('''SELECT team_name,
												  team_league FROM teams WHERE
												  team_id = ?''',
												  (team_id,)))[0]

			try:
				message_standard, message_combo = sf.all_bets_per_team(
						db, c, team_name, league_id)
				db.close()
			except ValueError as e:
				db.close()
				message = str(e)
				return bot.send_message(chat_id=update.message.chat_id,
				                        text=message)

			bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
							 text=message_standard)
			return bot.send_message(parse_mode='HTML',
									chat_id=update.message.chat_id,
									text=message_combo)
		else:
			return bot.send_message(chat_id=update.message.chat_id,
									text='Request not valid.')

	elif guess[0] == '_' or guess[-1] == '_':
		return bot.send_message(chat_id=update.message.chat_id,
								text='Wrong format.')

	# User sending the message
	first_name = nickname(update.message.from_user.first_name)

	team, bet = guess.split('_')
	bet = bet.replace(' ', '')
	bet = bet.replace(',', '.')
	guess = '_'.join([team, bet])

	db, c = dbf.start_db()

	warning_message = bf.check_still_to_confirm(db, c, first_name)
	if warning_message:
		db.close()
		return bot.send_message(chat_id=update.message.chat_id,
								text=warning_message)

	# Used to create the list confirmed_matches. This list will be used to
	# check whether a match has already been chosen
	bet_id = dbf.get_value('bet_id', 'bets', 'bet_status', 'Pending')
	confirmed_matches = list(c.execute('''SELECT pred_team1, pred_team2
									   FROM predictions WHERE
									   pred_status = "Confirmed"
									   AND pred_bet = ?''', (bet_id,)))

	try:

		team1, team2, field_id, league_id, nice_bet, quote = sf.look_for_quote(
																		guess)

		if (not confirmed_matches
		   or (team1, team2) not in confirmed_matches):

			match_date, match_time = list(c.execute('''SELECT match_date,
													match_time FROM matches
													WHERE match_team1 = ? and
													match_team2 = ?''',
													(team1, team2)))[0]

			team1 = team1.replace('*', '')
			team2 = team2.replace('*', '')

			# Update table
			c.execute('''INSERT INTO predictions (pred_user, pred_date,
												  pred_time, pred_team1,
												  pred_team2, pred_league,
												  pred_field, pred_rawbet,
												  pred_quote, pred_status)
					  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
					  (first_name, match_date, match_time, team1, team2,
					   league_id, field_id, nice_bet, quote, 'Not Confirmed'))

			db.commit()
			db.close()

			printed_bet = '{} - {} {} @{}'.format(team1, team2, nice_bet,
												  quote)

			return bot.send_message(chat_id=update.message.chat_id,
							        text=('{}\n' + 'Use /confirm or /cancel ' +
								   'to finalize your bet.').format(
									                              printed_bet))
		else:
			db.close()
			message = 'Match already chosen. Please change your bet.'
			return bot.send_message(chat_id=update.message.chat_id,
			                        text=message)

	except SyntaxError as e:
		db.close()
		message = str(e)
		return bot.send_message(chat_id=update.message.chat_id, text=message)

	except ConnectionError as e:
		db.close()
		message = str(e)
		return bot.send_message(chat_id=update.message.chat_id, text=message)

	except ValueError as e:
		db.close()
		message = str(e)
		return bot.send_message(chat_id=update.message.chat_id, text=message)


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

	db, c = dbf.start_db()

	# This a list of the users who have their bets in the status
	# 'Not Confirmed'
	users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
								pred_status = "Not Confirmed"'''))
	users_list = [element[0] for element in users_list]

	if first_name not in users_list:
		db.close()
		return bot.send_message(chat_id=update.message.chat_id,
								text='{}, you have no bet to confirm.'
								.format(first_name))

	# Check if there is any bet with status 'Pending' in the 'bets' table
	bet_id = dbf.get_value('bet_id', 'bets', 'bet_status', 'Pending')

	ref_list = bf.update_tables_and_ref_list(db, c, first_name, bet_id)

	# Now we delete all the bets of the same match which have not been
	# confirmed
	not_confirmed_matches = list(c.execute('''SELECT pred_id, pred_user,
										   pred_team1, pred_team2, pred_league
										   FROM predictions WHERE
										   pred_status = "Not Confirmed" '''))

	for match in not_confirmed_matches:
		dupl_message = bf.check_if_duplicate(c, first_name, match, ref_list)
		if dupl_message:
			bot.send_message(chat_id=update.message.chat_id, text=dupl_message)

	db.commit()
	db.close()

	return bot.send_message(chat_id=update.message.chat_id,
					        text='{}, your bet has been placed correctly.'
					        .format(first_name))


def cancel(bot, update):

	"""Delete the "Not Confirmed" bet from "predictions" table."""

	first_name = nickname(update.message.from_user.first_name)
	db, c = dbf.start_db()

	users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
								pred_status = "Not Confirmed"'''))
	users_list = [element[0] for element in users_list]

	if first_name not in users_list:
		db.close()
		return bot.send_message(chat_id=update.message.chat_id,
								text='{}, you have no bet to cancel.'
								.format(first_name))

	c.execute('''DELETE FROM predictions WHERE pred_user = ? AND
			  pred_status = "Not Confirmed"''', (first_name,))

	db.commit()
	db.close()
	return bot.send_message(chat_id=update.message.chat_id,
					        text='{}, your bet has been canceled.'.format(
							                                       first_name))


def delete(bot, update):

	"""Delete the "Confirmed" bet from "predictions" table."""

	first_name = nickname(update.message.from_user.first_name)
	db, c = dbf.start_db()

	bet_id = list(c.execute('''SELECT bet_id FROM bets WHERE
							bet_status = "Pending"'''))
	if not bet_id:
		db.close()
		return bot.send_message(chat_id=update.message.chat_id,
								text='There are no "Pending" bets.')

	bet_id = bet_id[0][0]
	bet_to_delete = list(c.execute('''SELECT pred_id FROM predictions WHERE
								   pred_bet = ? AND pred_user = ? AND
								   pred_status = "Confirmed"''',
								   (bet_id, first_name)))
	if not bet_to_delete:
		db.close()
		message = '{}, you have no bet to delete.'.format(first_name)
		return bot.send_message(chat_id=update.message.chat_id,
								text=message)

	bet_to_delete = bet_to_delete[0][0]
	c.execute('''DELETE FROM predictions WHERE pred_id = ?''',
			  (bet_to_delete,))
	db.commit()

	conf_bets_left = list(c.execute('''SELECT pred_id FROM predictions WHERE
									pred_status = "Confirmed" AND
									pred_bet = ?''', (bet_id,)))

	if not conf_bets_left:
		c.execute('''DELETE FROM bets WHERE bet_id = ?''', (bet_id,))
		db.commit()

	db.close()
	return bot.send_message(chat_id=update.message.chat_id,
					        text='{}, your bet has been deleted.'.format(
							                                       first_name))


def play(bot, update, args):

	"""
	Manage the login and play the bet. Args input is the amount of euros
	to bet.
	"""

	def money(browser, xpath):

		"""Extract the text from the HTML element and return it as a float."""

		final_money = browser.find_element_by_xpath(xpath).text
		final_money = final_money.replace('Saldo: ', '')
		final_money = final_money.replace(' €', '')
		final_money = float(final_money.replace(',', '.'))

		return final_money


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

	db, c = dbf.start_db()
	not_conf_list = list(c.execute('''SELECT pred_user, pred_team1, pred_team2,
								   pred_field, pred_rawbet FROM predictions
								   WHERE pred_status = "Not Confirmed" '''))
	if not_conf_list:
		bot.send_message(chat_id=update.message.chat_id,
						 text='There are still Not Confirmed bets:')
		for match in not_conf_list:
			bot.send_message(chat_id=update.message.chat_id,
							 text=('{}\n{} - {}\n{}\n{}'.format(match[0],
								   match[1], match[2], match[3], match[4])))

		db.close()

		return bot.send_message(chat_id=update.message.chat_id,
								text=('/confirm or /cancel each of them and ' +
									  'then play again.'))

	# bet_id of the Pending bet
	bet_id = dbf.get_value('bet_id', 'bets', 'bet_status', 'Pending')
	if not bet_id:
		db.close()
		return bot.send_message(chat_id=update.message.chat_id,
								text='No bets to play.')

	# Check whether there are matches already started
	invalid_bets = dbf.check_before_play(db, c)
	if invalid_bets:
		message = '{}, {} - {} was scheduled on {} at {}. Too late.'
		for x in range(len(invalid_bets)):
			bet = invalid_bets[x]
			date_to_print = (str(bet[3])[6:] + '/' + str(bet[3])[4:6] + '/' +
							 str(bet[3])[:4])
			time_to_print = str(bet[4])[:2] + ':' + str(bet[4])[2:]
			if x < len(invalid_bets) - 1:
				logger.info('PLAY - Too late for the following bet: ' +
							'{} , {}, {}.'.format(bet[0], bet[1], bet[2]))
				bot.send_message(chat_id=update.message.chat_id,
								 text=message.format(bet[0], bet[1], bet[2],
													 date_to_print,
													 time_to_print))
			else:
				db.close()
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

	matches_to_play = bf.create_matches_to_play(c, bet_id)

	db.close()

	browser = sf.go_to_lottomatica(0)
	logger.info('PLAY - Connected to Lottomatica')
	count = 0
	for match in matches_to_play:
		try:
			basket_message = bf.add_bet_to_basket(browser, match, count,
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

	# Find the basket with all the bets
	try:
		basket = ('.//nav[@id="toolbarForHidden"]/ul/' +
				  'li[@class="toolbar-nav-item ng-scope"]/a')
		sf.wait_clickable(browser, 20, basket)

		browser.find_element_by_xpath(basket).click()
		logger.info('PLAY - Basket icon clicked')
	except TimeoutException:
		browser.quit()
		logger.info('PLAY - Unable to click the basket')
		return bot.send_message(chat_id=update.message.chat_id,
								text=('Problem during placing the bet. ' +
									  'Please check your internet ' +
									  'connection and try again.'))

	summary_path = ('.//div[@id="toolbarContent"]/div[@id="basket"]' +
					'//ul//span[contains(@class,"col-sm-12")]')

	summary_element = browser.find_element_by_xpath(summary_path)

	# and extract the actual number of bets present in the basket
	matches_played = int(summary_element.text.split(' ')[2][1:-1])

	# If this number is equal to the number of bets chosen to play
	if matches_played == len(matches_to_play):

		possible_win = bf.insert_euros(browser, euros)

		browser.find_element_by_xpath(basket).click()

		# Make the login
		sf.login(browser)
		logger.info('PLAY - Logged in')
		bot.edit_message_text(chat_id=update.message.chat_id,
							  message_id=mess_id,
							  text='Logged in')

		money_left_path = ('.//div[@class="user-details-header clearfix ' +
		                   'reduce-margin-bottom-for-collapsed-login-box"]' +
		                   '/div[2]/div[1]')

		button_location = './/div[@class="change-bet ng-scope"]'

		try:
			sf.wait_visible(browser, 20, money_left_path)
			sf.wait_visible(browser, 20, button_location)
		except TimeoutException:
			browser.quit()
			logger.info('PLAY - "SCOMMETTI" container not found')
			return bot.send_message(chat_id=update.message.chat_id,
							 text=('Problem during placing the bet. ' +
								   'Please check if the bet is valid or ' +
								   'the connection and try again.'))

		# Money left before playing the bet
		money_before = money(browser, money_left_path)

		sf.scroll_to_element(browser, 'true',
							 browser.find_element_by_xpath(
									 button_location))

		try:
			button_path = ('.//button[@class="button-default no-margin-' +
						   'bottom ng-scope"]')

			button_list = browser.find_elements_by_xpath(button_path)
		except NoSuchElementException:
			logger.info('PLAY - "AGGIORNA" button is visible')
			button_path = './/button[@class="button-default"]'
			button_list = browser.find_elements_by_xpath(button_path)
			for element in button_list:
				if element.is_displayed():
					print(element.text)
					element.click()
					time.sleep(3)
					break

		for element in button_list:
			if element.is_displayed():
				print(element.text)
				element.click()
				logger.info('PLAY - Bet has been played. Possible win: ' +
							'{}'.format(possible_win))
				db, c = dbf.start_db()
				c.execute('''UPDATE bets SET bet_date = ?, bet_euros = ?,
						  bet_prize = ?, bet_status = ? WHERE
						  bet_status = "Pending" ''',
						  (dbf.todays_date()[0], euros, possible_win,
						   'Placed'))
				db.commit()
				logger.info('PLAY - "bets" db table updated')
				db.close()

				bot.edit_message_text(chat_id=update.message.chat_id,
									  message_id=mess_id, text='Done!')
				break

		time.sleep(5)

		# Money after playing the bet
		money_after = money(browser, money_left_path)

		if money_after == money_before - euros:

			# Print the summary
			message = 'Bet placed correctly.\n\n'
			db, c = dbf.start_db()
			bet_id_list = list(c.execute(
				'''SELECT bet_id FROM bets WHERE bet_result = "Unknown" '''))
			bet_id_list = [element[0] for element in bet_id_list]
			bet_id = bet_id_list[-1]
			summary = list(c.execute('''SELECT pred_user, pred_team1,
									 pred_team2, pred_time, pred_rawbet,
									 pred_quote, pred_date FROM bets INNER JOIN
									 predictions on pred_bet = bet_id WHERE
									 bet_id = ?''', (bet_id,)))

			db.close()
			summary = sorted(sorted(summary, key=lambda x: x[3]),
			                 key=lambda x: x[6])
			message += (played_bets(summary) +
			            '\nPossible win: <b>{}</b>'.format(possible_win) +
			            '\nMoney left: <b>{}</b>'.format(money_after))
			bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
							 text=message)
		else:
			bot.send_message(chat_id=update.message.chat_id,
			                 text=('Money left did not change, try again ' +
			                       'the command /play.'))
	else:
		bot.send_message(chat_id=update.message.chat_id,
						 text=('Not all matches have been added, try again ' +
							   'the command /play.'))

	# browser.quit()


def update_results(bot, update):

	"""
	Updates the columns "bet_result", "pred_result" and "pred_label" in the
	database.
	"""

	db, c = dbf.start_db()
	ref_list = list(c.execute('''SELECT bet_id, bet_date FROM bets WHERE
							  bet_status = "Placed" AND bet_result = "Unknown"
							  '''))
	logger.info('UPDATE - Selecting Placed bets...')
	db.close()

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
		bf.go_to_personal_area(browser, 0)

		bf.go_to_placed_bets(browser, 0)

		bets_updated = bf.analyze_main_table(browser, ref_list, 0)

	except ConnectionError as e:
		browser.quit()
		return bot.send_message(chat_id=update.message.chat_id, text=str(e))

	browser.quit()

	if bets_updated:
		logger.info('UPDATE - Database updated correctly.')
	else:
		logger.info('No completed bets were found.')


def summary(bot, update):

	bet_id = dbf.get_value('bet_id', 'bets', 'bet_status', 'Pending')
	db, c = dbf.start_db()
	summary = list(c.execute('''SELECT pred_user, pred_team1, pred_team2,
							 pred_time, pred_rawbet, pred_quote, pred_date 
							 FROM bets INNER JOIN predictions on
							 pred_bet = bet_id WHERE bet_id = ?''', (bet_id,)))

	db.close()
	if summary:
		summary = sorted(sorted(summary, key=lambda x: x[3]),
						 key=lambda x: x[6])
		final_quote = 1
		all_quotes = [element[5] for element in summary]
		for quote in all_quotes:
			final_quote *= quote

		message1 = played_bets(summary)
		message2 = '\n\nPossible win with 5 euros: <b>{:.1f}</b>'.format(
				final_quote*5)
		message = message1 + message2
	else:
		message = 'No bets yet. Choose the first one.'

	bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
					 text=message)


def score(bot, update):

	stf.new_score()
	bot.send_photo(chat_id=update.message.chat_id, photo=open('score.png',
															  'rb'))
	os.remove('score.png')


def aver_quote(bot, update):

	stf.aver_quote()
	bot.send_photo(chat_id=update.message.chat_id, photo=open('aver_quote.png',
															  'rb'))
	os.remove('aver_quote.png')


def euros_lost(bot, update):

	stf.euros_lost_for_one_bet()
	bot.send_photo(chat_id=update.message.chat_id, photo=open('euros_lost.png',
															  'rb'))
	os.remove('euros_lost.png')


def series(bot, update):

	stf.series()
	bot.send_photo(chat_id=update.message.chat_id, photo=open('series.png',
															  'rb'))
	os.remove('series.png')


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


def send_log(bot, update):

	bot.send_document(chat_id=update.message.chat_id,
	                  document=open('logs/bet_bot.log', 'rb'))


start_handler = CommandHandler('start', start)
help_quote_handler = CommandHandler('help_quote', help_quote)
help_stats_handler = CommandHandler('help_stats', help_stats)
alias_handler = CommandHandler('alias', alias)
info_handler = CommandHandler('info', info)
get_handler = CommandHandler('get', get, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
delete_handler = CommandHandler('delete', delete)
play_handler = CommandHandler('play', play, pass_args=True)
update_handler = CommandHandler('update', update_results)
summary_handler = CommandHandler('summary', summary)
score_handler = CommandHandler('score', score)
aver_quote_handler = CommandHandler('aver_quote', aver_quote)
euros_lost_handler = CommandHandler('euros_lost', euros_lost)
series_handler = CommandHandler('series', series)
stats_handler = CommandHandler('stats', stats)
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
dispatcher.add_handler(alias_handler)
dispatcher.add_handler(info_handler)
dispatcher.add_handler(get_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(delete_handler)
dispatcher.add_handler(play_handler)
dispatcher.add_handler(update_handler)
dispatcher.add_handler(summary_handler)
dispatcher.add_handler(score_handler)
dispatcher.add_handler(aver_quote_handler)
dispatcher.add_handler(euros_lost_handler)
dispatcher.add_handler(series_handler)
dispatcher.add_handler(stats_handler)
dispatcher.add_handler(match_handler)
dispatcher.add_handler(new_quotes_handler)
dispatcher.add_handler(log_handler)

logger = log.set_logging()
updater.start_polling()
logger.info('Bet_Bot started.')
updater.idle()
