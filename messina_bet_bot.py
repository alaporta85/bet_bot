# -*- coding: utf-8 -*-

import os
import random
import time
import datetime
from itertools import count
from telegram.ext import CommandHandler

from Functions import utils as utl
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import bot_functions as bf
# from Functions import stats_functions as stf
from Functions import logging_file as log
# import Classes as cl
import config as cfg


def cake(bot, update):

	"""
	Send the cake.
	"""

	chat_id = update.message.chat_id
	return bot.send_photo(chat_id=chat_id, photo=open('cake.png', 'rb'))


def bike(bot, update):

	"""
	Send bike sound.
	"""

	chat_id = update.message.chat_id
	return bot.send_audio(chat_id=chat_id, audio=open('bici.mp3', 'rb'))


def cancel(bot, update):

	"""
	Delete the 'Not Confirmed' match from 'predictions' table.
	"""

	chat_id = update.message.chat_id
	user = utl.get_nickname(update)

	if utl.nothing_pending(nickname=user):
		return bot.send_message(chat_id=chat_id, text='No bet to cancel.')

	dbf.db_delete(table='predictions',
	              where=f'user = "{user}" AND status = "Not Confirmed"')

	return bot.send_message(chat_id=chat_id, text='Bet canceled.')


def confirm(bot, update):

	"""
	Confirm the match and update the database.
	"""

	chat_id = update.message.chat_id
	user = utl.get_nickname(update)

	if utl.nothing_pending(nickname=user):
		return bot.send_message(chat_id=chat_id, text='No match to confirm.')

	# Check if quote respects the limits
	if utl.outside_quote_limits(nickname=user):
		return bot.send_message(chat_id=chat_id, text='Se cia 👏👏🖕🖕')

	# Update the database
	bet_id = utl.update_db_after_confirm(nickname=user)

	# Inform users match is correctly added
	bot.send_message(chat_id=chat_id, text='Match added correctly.')

	message = utl.create_summary(euros=5)
	bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID, text=message)

	# Play the bet automatically
	if utl.autoplay(bet_id):
		return False#play(bot, update, ['5'])


# def delete(bot, update):  # DONE
#
# 	"""
# 	Delete the 'Confirmed' match from 'predictions' table.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	user = utl.get_nickname(update)
#
# 	# Check if there is any 'Pending' bet
# 	try:
# 		bet_id = dbf.db_select(
# 				table='bets',
# 				columns_in=['bet_id'],
# 		        where='bet_status = "Pending"')[0]
# 	except IndexError:
# 		return bot.send_message(chat_id=chat_id, text='No open bets.')
#
# 	# Check if user has a match to delete
# 	try:
# 		match_to_delete = dbf.db_select(
# 				table='predictions',
# 				columns_in=['pred_id'],
# 				where=('pred_bet = {} AND pred_user = "{}" AND ' +
# 				       'pred_status = "Confirmed"').format(bet_id, user))[0]
# 	except IndexError:
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='{}, no match to delete.'.format(user))
#
# 	# Update the database
# 	bf.update_to_play_table(user, bet_id, 'delete')
# 	dbf.db_delete(
# 			table='predictions',
# 			where='pred_id = {}'.format(match_to_delete))
#
# 	# Check if this was the only match of the bet and, if yes, delete the bet
# 	# in the 'bet' table
# 	conf_bets_left = dbf.db_select(
# 			table='predictions',
# 			columns_in=['pred_id'],
# 			where='pred_status = "Confirmed" AND pred_bet = {}'.format(bet_id))
#
# 	if not conf_bets_left:
# 		dbf.db_delete(
# 				table='bets',
# 		        where='bet_id = {}'.format(bet_id))
#
# 	return bot.send_message(
# 			chat_id=chat_id, text='{}, bet deleted.'.format(user))
#
#
# def fischia(bot, update):  # DONE
#
# 	"""
# 	Send random photo of Mazzarri.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	walter = random.choice(os.listdir('Mazzarri/'))
#
# 	return bot.send_photo(chat_id=chat_id,
# 	                      photo=open('Mazzarri/' + walter, 'rb'))
#
#
# def format_text(content):  # DONE
#
# 	"""
# 	Called inside help_stats() function to clean the message text.
#
# 	"""
#
# 	message = ''.join(content)
# 	message = message.replace('\n\n', 'xx')
# 	message = message.replace('\n', ' ')
# 	message = message.replace('xx', '\n\n')
#
# 	return message
#
#
# def get(bot, update, args):  # DONE
#
# 	"""
# 	Update the table 'predictions' in the database with the data relative to
# 	the chosen match if command is in the form:
#
# 		/play team_bet
#
# 	If the command has the form:
#
# 		/play team
#
# 	it sends all the quotes for that team's match.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	if chat_id == cfg.GROUP_ID:
# 		# TODO send messages to each private chat instead of group chat
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='Usa il gruppo privato')
# 	else:
# 		name = update.message.from_user.first_name
# 		dbf.db_update(
# 				table='people',
# 				columns=['people_private_group'],
# 				values=[chat_id],
# 				where=f'people_name = "{name}"')
#
# 	# Check the format
# 	if not args:
# 		return bot.send_message(chat_id=chat_id, text='Insert the bet.')
#
# 	guess = ' '.join(args).upper()
# 	if guess[0] == '_' or guess[-1] == '_':
# 		return bot.send_message(chat_id=chat_id, text='Wrong format.')
#
# 	# Try to separate the team from the bet and replace some values
# 	try:
# 		vals2replace = [(' ', ''), ('*', ''), ('+', ''), (',', '.'),
# 		                ('TEMPO', 'T'),
# 		                ('1T', 'PT'), ('2T', 'ST'),
# 		                ('GOAL', 'GG'), ('NOGOAL', 'NG'),
# 		                ('HANDICAP', 'H'), ('HAND', 'H')]
#
# 		input_team, input_bet = guess.split('_')
# 		for old, new in vals2replace:
# 			input_bet = input_bet.replace(old, new)
#
# 	except ValueError:
# 		# If only the team is sent
# 		input_team, input_bet = guess, ''
#
# 	# Correct team name by Jaccard similarity
# 	team_name = dbf.select_team(input_team)
#
# 	if not team_name:
# 		return bot.send_message(chat_id=chat_id, text='Team not found')
#
# 	# If '*' is in the input it means it's a Champions League match
# 	elif '*' in input_team:
# 		league_id = 8
# 		team_name = '*' + team_name
#
# 	# Try to select the league. The IndexError occurs when the Jaccard result
# 	# is a team playing in Champions League but not in any of the main leagues.
# 	# In this case, looking for that team among any team_id != 8 would cause an
# 	# error. Ex: if '/play dort' is sent, meaning Dortmund, bot will recognize
# 	# it as PORTO and the error is given
# 	else:
# 		try:
# 			league_id = dbf.db_select(
# 					table='teams',
# 					columns_in=['team_league'],
# 					where='team_name = "{}" AND team_league != 8'.
# 					format(team_name))[0]
# 		except IndexError:
# 			return bot.send_message(
# 					chat_id=chat_id,
# 					text='No bets found for {}'.format(team_name))
#
# 	# If only the team is sent, 2 messages with all the quotes for that match
# 	# will be sent in the chat
# 	if not input_bet:
# 		try:
# 			message_standard, message_combo = bf.all_bets_per_team(team_name,
# 			                                                       league_id)
#
# 		# If, for any reason, quotes are not found
# 		except ValueError as e:
# 			message = str(e)
# 			return bot.send_message(chat_id=chat_id, text=message)
#
# 		bot.send_message(parse_mode='HTML', chat_id=chat_id,
# 		                 text=message_standard)
# 		return bot.send_message(parse_mode='HTML', chat_id=chat_id,
# 								text=message_combo)
#
# 	user = utl.get_nickname(update)
#
# 	# Check if user has other matches not confirmed
# 	warning_message = bf.check_still_to_confirm(user)
# 	if warning_message:
# 		return bot.send_message(chat_id=chat_id, text=warning_message)
#
# 	# Create the list of confirmed_matches. This list will be used to check
# 	# whether a match has already been chosen
# 	try:
# 		bet_id = dbf.db_select(
# 				table='bets',
# 				columns_in=['bet_id'],
# 				where='bet_status = "Pending"')[0]
#
# 		confirmed_matches = dbf.db_select(
# 				table='predictions',
# 				columns_in=['pred_team1', 'pred_team2'],
# 				where=('pred_status = "Confirmed" AND pred_bet = {}'.
# 				format(bet_id)))
# 	except IndexError:
# 		confirmed_matches = []
#
# 	# Try to extract all the info about the match and the requested quote
# 	try:
# 		team1, team2, field_id, nice_bet, quote = bf.look_for_quote(team_name,
# 		                                                            input_bet)
#
# 	# To handle invalid bets or missing quotes
# 	except ValueError as e:
# 		return bot.send_message(chat_id=chat_id, text=str(e))
#
# 	# If match is available, update the database and send a message
# 	if (team1, team2) not in confirmed_matches:
#
# 		dt = dbf.db_select(
# 				table='matches',
# 				columns_in=['match_date'],
# 				where='match_team1 = "{}" AND match_team2 = "{}"'.
# 				format(team1, team2))[0]
#
# 		team1 = team1.replace('*', '')
# 		team2 = team2.replace('*', '')
#
# 		dbf.db_insert(
# 				table='predictions',
# 				columns=['pred_user', 'pred_date', 'pred_team1', 'pred_team2',
# 				         'pred_league', 'pred_field', 'pred_rawbet',
# 				         'pred_quote', 'pred_status'],
# 				values=[user, dt, team1, team2, league_id, field_id,
# 				        nice_bet, quote, 'Not Confirmed'])
#
# 		printed_bet = '{} - {} {} @{}'.format(team1, team2, nice_bet, quote)
#
# 		return bot.send_message(chat_id=chat_id,
# 						        text=('{}\n\n' +
# 						              '/confirm                /cancel').
# 						              format(printed_bet))
# 	else:
# 		return bot.send_message(chat_id=chat_id, text='Match already chosen')
#
#
# def help_quote(bot, update):  # DONE
#
# 	"""
# 	Instructions to insert the correct bet.
# 	"""
#
# 	chat_id = update.message.chat_id
# 	if chat_id == cfg.GROUP_ID:
# 		# TODO send messages to each private chat instead of group chat
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='Usa il gruppo privato')
#
# 	f = open('Messages/help_quote.txt', 'r')
# 	content = f.readlines()
# 	f.close()
#
# 	message = ''
# 	for row in content:
# 		message += row
#
# 	return bot.send_message(chat_id=chat_id, text=message)
#
#
# def help_stats(bot, update):  # DONE
#
# 	"""
# 	Instructions to use statistic commands.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	if chat_id == cfg.GROUP_ID:
# 		# TODO send messages to each private chat instead of group chat
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='Usa il gruppo privato')
#
# 	f = open('Messages/help_stats.txt', 'r')
# 	content = f.readlines()
# 	f.close()
#
# 	message = format_text(content)
#
# 	return bot.send_message(chat_id=chat_id, text=message)
#
#
# def info(bot, update):  # DONE
#
# 	"""
# 	Send message of general info.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	if chat_id == cfg.GROUP_ID:
# 		# TODO send messages to each private chat instead of group chat
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='Usa il gruppo privato')
#
# 	f = open('Messages/info.txt', 'r')
# 	content = f.readlines()
# 	f.close()
#
# 	message = ''
# 	for row in content:
# 		message += row
#
# 	return bot.send_message(chat_id=chat_id, text=message)
#
#
# def match(bot, update, args):  # DONE
#
# 	"""
# 	Return the matches of the requested day.
# 	"""
#
# 	chat_id = update.message.chat_id
# 	if chat_id == cfg.GROUP_ID:
# 		# TODO send messages to each private chat instead of group chat
# 		return bot.send_message(chat_id=chat_id,
# 		                        text='Usa il gruppo privato')
#
# 	if not args:
# 		return bot.send_message(chat_id=chat_id,
# 								text='Insert the day. Ex. /match sab')
# 	try:
# 		message = bf.matches_per_day(args[0])
# 		return bot.send_message(parse_mode='HTML', chat_id=chat_id,
# 						        text=message)
# 	except SyntaxError as e:
# 		return bot.send_message(chat_id=chat_id, text=str(e))
#
#
# def matiz(bot, update):  # DONE
#
# 	"""
# 	Send matiz photo.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	return bot.send_photo(chat_id=chat_id, photo=open('matiz.png', 'rb'))
#
#
# def new_quotes(bot, update, args):  # DONE
#
# 	"""
# 	Fill the db with the new quotes for the chosen leagues.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	try:
# 		role = utl.get_role(update)
# 	except AttributeError:
# 		role = 'Admin'
#
# 	if role != 'Admin':
# 		return bot.send_message(chat_id=update.message.chat_id,
# 		                        text='Fatti i cazzi tuoi')
# 	else:
#
# 		if not args:
# 			message = 'Insert leagues. Ex. /new_quotes serie a, ligue 1'
# 			return bot.send_message(chat_id=chat_id, text=message)
#
# 		# Format the input and send a warning if it is wrong
# 		args = ' '.join(args).split(',')
# 		args = [arg[1:] if arg[0] == ' ' else arg for arg in args]
# 		args = [arg[:-1] if arg[-1] == ' ' else arg for arg in args]
# 		for arg in args:
# 			if arg.upper() not in cfg.countries:
# 				leagues = ', '.join([league for league in cfg.countries])
# 				return bot.send_message(
# 						chat_id=chat_id,
# 						text='Possible options: {}'.format(leagues))
#
# 		# For each league requested, delete all the match already present in
# 		# the database
# 		leagues = [arg.upper() for arg in args]
# 		for league in leagues:
# 			league_id = dbf.db_select(
# 					table='leagues',
# 					columns_in=['league_id'],
# 					where='league_name = "{}"'.format(league))[0]
#
# 			matches = dbf.db_select(
# 					table='matches',
# 					columns_in=['match_id'],
# 					where='match_league = {}'.format(league_id))
#
# 			for match in matches:
# 				dbf.db_delete(
# 						table='quotes',
# 						where='quote_match = {}'.format(match))
# 				dbf.db_delete(
# 						table='matches',
# 						where='match_id = {}'.format(match))
#
# 		# Start scraping
# 		start = time.time()
# 		logger.info('NEW_QUOTES - Nightly job: Updating quote...')
# 		sf.fill_db_with_quotes(leagues)
# 		end = time.time() - start
# 		mins = int(end//60)
# 		secs = round(end % 60)
# 		logger.info(f'NEW_QUOTES - Whole process took {mins}:{secs}.')
#
#
def night_quotes(bot, update):

	"""
	Fill the db with the new quotes for all the leagues.
	"""

	try:
		role = utl.get_role(update)
	except AttributeError:
		role = 'Admin'

	if role == 'Admin':

		# Start scraping
		start = time.time()
		logger.info('NIGHT_QUOTES - Nightly job: Updating quote...')
		sf.scrape_all_quotes()
		end = time.time() - start
		mins = int(end // 60)
		secs = round(end % 60)
		logger.info(f'NIGHT_QUOTES - Whole process took {mins}:{secs}.')

	else:
		chat_id = update.message.chat_id
		return bot.send_message(chat_id=chat_id, text='Fatti i cazzi tuoi')


# def play(bot, update, args):  # DONE
#
# 	"""
# 	Play the bet online.
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	euros = bf.check_if_input_is_correct(args)
# 	if type(euros) == str:
# 		return bot.send_message(chat_id=chat_id, text=euros)
#
# 	# Check if there is any bet which has not been confirmed by any user
# 	warn = bf.one_or_more_preds_are_not_confirmed()
# 	if warn:
# 		return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=warn)
#
# 	# Check if there is any bet to play and, if yes, select the id
# 	try:
# 		bet_id = dbf.db_select(
# 				table='bets',
# 				columns_in=['bet_id'],
# 		        where='bet_status = "Pending"')[0]
# 	except IndexError:
# 		return bot.send_message(chat_id=chat_id, text='No bets to play.')
#
# 	# Check whether there are matches already started
# 	late = bf.check_if_too_late(bet_id)
# 	if late:
# 		return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=late)
#
# 	# Log in
# 	sent = bot.send_message(chat_id=cfg.GROUP_ID, text='Matches added: 0')
#
# 	# To identify the message
# 	mess_id = sent.message_id
#
#   TODO change for connect_to()
# 	browser = sf.go_to_lottomatica()
#
# 	# This message will be updated during the process to keep track of all
# 	# the steps
# 	dynamic_message = 'Matches added: {}'
#
# 	# Create a list with all the preds to play
# 	matches_to_play = dbf.db_select(table='to_play')
#
# 	# Add all the preds to the basket and update the message inside the chat
# 	for i, (tm1, tm2, field, bet, url) in enumerate(matches_to_play):
#
# 		browser = sf.connect_to(some_url=url, browser=browser)
#
# 		# First time we refresh the page to close the cookies bar.
# 		# browser.refresh() does not work
# 		if not i:
# 			browser = sf.connect_to(some_url=url, browser=browser)
#
# 		basket_msg = sf.add_bet_to_basket(
# 				browser, (field, bet), i, dynamic_message)
# 		logger.info('PLAY - {}-{}  {} added'.format(tm1, tm2, bet))
#
# 		bot.edit_message_text(
# 				chat_id=cfg.GROUP_ID, message_id=mess_id, text=basket_msg)
#
# 	bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id, text='Logging')
# 	browser = sf.login(browser=browser)
# 	logger.info('PLAY - Logged')
# 	bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id, text='Logged')
#
# 	# Insert the amount to bet
# 	sf.insert_euros(browser, euros)
#
# 	# Money left before playing the bet
# 	money_before = sf.money(browser)
#
# 	# Click the button to place the bet
# 	sf.click_scommetti(browser)
# 	time.sleep(10)
#
# 	# Money after clicking the button
# 	money_after = sf.money(browser)
#
# 	# Verify money has the new value. If not, refresh the value and check again
# 	# up to 1000 times
# 	c = count(1)
# 	while next(c) < 1000 and money_after != (money_before - euros):
# 		# sf.refresh_money(browser)
# 		browser.refresh()
# 		time.sleep(2)
# 		money_after = sf.money(browser)
#
# 	if money_after == money_before - euros:
#
# 		logger.info('PLAY - Bet has been played.')
#
# 		# Update bet table
# 		dbf.db_update(
# 				table='bets',
# 				columns=['bet_date', 'bet_euros', 'bet_status'],
# 				values=[datetime.datetime.now(), euros, 'Placed'],
# 				where='bet_status = "Pending"')
#
# 		# Empty table with bets
# 		dbf.empty_table(table='to_play')
#
# 		# Print the summary
# 		msg = create_summary(when='after', euros=euros)
# 		msg += '\nMoney left: <b>{}</b>'.format(money_after)
# 		bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID, text=msg)
# 	else:
# 		msg = 'Money left did not change, try again the command /play.'
# 		bot.send_message(chat_id=cfg.GROUP_ID, text=msg)
#
# 	browser.quit()
#
#
# def remind(bot, update):  # DONE
#
# 	"""
# 	Send a message to remind the matches of a bet which is still open.
#
# 	"""
#
# 	chat_id = update.message.chat_id
# 	message = create_summary(when='remind', euros=5)
#
# 	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)
#
#
# def score(bot, update, args):  # DONE
#
# 	"""
# 	Send the bar plot of the score.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	if not args:
# 		return bot.send_photo(chat_id=chat_id,
# 		                      photo=open('score_2019-2020.png', 'rb'))
# 	elif args[0] == 'general':
# 		return bot.send_photo(chat_id=chat_id,
# 		                      photo=open('score_GENERAL.png', 'rb'))
# 	else:
# 		try:
# 			return bot.send_photo(
# 					chat_id=chat_id,
# 					photo=open('score_{}.png'.format(args[0]), 'rb'))
# 		except FileNotFoundError:
# 			return bot.send_message(
# 					chat_id=chat_id,
# 					text='Wrong format. Ex: 2017-2018 or "general"')
#
#
# def send_log(bot, update):  # DONE
#
# 	"""
# 	Send the log.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	return bot.send_document(chat_id=chat_id,
# 	                         document=open('logs/bet_bot.log', 'rb'))
#
#
# def series(bot, update):  # DONE
#
# 	"""
# 	Send bar plot of positive and negative series.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	return bot.send_photo(chat_id=chat_id, photo=open('series.png', 'rb'))
#
#
# def sotm(bot, update):  # DONE
#
# 	"""
# 	Send tbar plot of the best/worst per month.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	return bot.send_photo(chat_id=chat_id, photo=open('sotm.png', 'rb'))
#
#
# def start(bot, update):  # DONE
#
# 	"""
# 	Start the bot.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	return bot.send_message(chat_id=chat_id, text="Iannelli suca")
#
#
# def stats(bot, update):  # DONE
#
# 	"""
# 	Send some stats.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	message_money = stf.money()
# 	message_perc = stf.abs_perc()
# 	message_teams = stf.stats_on_teams()
# 	message_bets = stf.stats_on_bets()
# 	message_quotes = stf.stats_on_quotes()
# 	message_combos = stf.stats_on_combos()
#
# 	fin_mess = (message_money + message_perc + message_teams +
# 	            message_bets + message_quotes + message_combos)
#
# 	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=fin_mess)
#
#
# def summary(bot, update):  # DONE
#
# 	"""
# 	Send the summary of the matches already confirmed before playong the bet.
#
# 	"""
#
# 	chat_id = update.message.chat_id
#
# 	message = create_summary(when='before', euros=5)
#
# 	return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)
#
#
# def update_results(bot, update):
#
# 	"""
# 	Once all matches in the bet are concluded, update the database.
#
# 	"""
#
# 	ref_list = dbf.db_select(
# 			table='bets',
# 			columns_in=['bet_id', 'bet_date'],
# 			where='bet_status = "Placed" AND bet_result = "Unknown"')
# 	ref_list.sort(key=lambda x: x[0], reverse=True)
# 	logger.info('UPDATE - Selecting Placed bets...')
#
# 	if not ref_list:
# 		logger.info('UPDATE - No bets must be updated')
# 		return bot.send_message(chat_id=update.message.chat_id,
# 		                        text='No bets to update.')
#
# 	try:
#   TODO change for connect_to()
# 		browser = sf.go_to_lottomatica()
# 	except ConnectionError as e:
# 		return bot.send_message(chat_id=update.message.chat_id, text=e)
# 	time.sleep(3)
#
# 	sf.login(browser)
# 	time.sleep(3)
#
# 	try:
# 		sf.go_to_personal_area(browser)
#
# 		sf.go_to_placed_bets(browser, 0)
#
# 		bets_updated = sf.analyze_main_table(browser, ref_list)
#
# 	except ConnectionError as e:
# 		browser.quit()
# 		return bot.send_message(chat_id=update.message.chat_id, text=str(e))
#
# 	browser.quit()
#
# 	if bets_updated:
# 		dt = datetime.datetime.now()
# 		last_update = '*Last update:x    {}/{}/{} at {}:{}'.format(
# 				dt.day, dt.month, dt.year, dt.hour, dt.minute)
# 		dbf.empty_table(table='last_results_update')
# 		dbf.db_insert(table='last_results_update',
# 		              columns=['message'],
# 		              values=[last_update])
# 		cl.bets, cl.preds = cl.update_bets_preds()
# 		cl.players = {name: cl.Player(name) for name in cl.partecipants}
# 		cl.stats = cl.Stats()
# 		logger.info('UPDATE - Database updated correctly.')
# 	else:
# 		logger.info('No completed bets were found.')


cake_handler = CommandHandler('cake', cake)
bici_handler = CommandHandler('bici', bike)
cancel_handler = CommandHandler('cancel', cancel)
confirm_handler = CommandHandler('confirm', confirm)
# delete_handler = CommandHandler('delete', delete)
# fischia_handler = CommandHandler('fischia', fischia)
# get_handler = CommandHandler('get', get, pass_args=True)
# help_quote_handler = CommandHandler('help_quote', help_quote)
# help_stats_handler = CommandHandler('help_stats', help_stats)
# info_handler = CommandHandler('info', info)
# log_handler = CommandHandler('log', send_log)
# match_handler = CommandHandler('match', match, pass_args=True)
# matiz_handler = CommandHandler('matiz', matiz)
# new_quotes_handler = CommandHandler('new_quotes', new_quotes, pass_args=True)
night_quotes_handler = CommandHandler('night_quotes', night_quotes)
# play_handler = CommandHandler('play', play, pass_args=True)
# remind_handler = CommandHandler('remind', remind)
# score_handler = CommandHandler('score', score, pass_args=True)
# series_handler = CommandHandler('series', series)
# sotm_handler = CommandHandler('sotm', sotm)
# start_handler = CommandHandler('start', start)
# stats_handler = CommandHandler('stats', stats)
# summary_handler = CommandHandler('summary', summary)
# update_handler = CommandHandler('update', update_results)

# Nightly quotes updating
update_quotes = cfg.UPDATER.job_queue
# update_quotes.run_repeating(night_quotes, 86400,
#                             first=datetime.time(1, 00, 00))

update_tables = cfg.UPDATER.job_queue
# update_tables.run_repeating(update_results, 86400,
# 							first=datetime.time(3, 00, 00))

# cfg.DISPATCHER.add_handler(start_handler)
# cfg.DISPATCHER.add_handler(help_quote_handler)
# cfg.DISPATCHER.add_handler(help_stats_handler)
# cfg.DISPATCHER.add_handler(info_handler)
# cfg.DISPATCHER.add_handler(get_handler)
cfg.DISPATCHER.add_handler(confirm_handler)
cfg.DISPATCHER.add_handler(cancel_handler)
# cfg.DISPATCHER.add_handler(delete_handler)
# cfg.DISPATCHER.add_handler(play_handler)
# cfg.DISPATCHER.add_handler(update_handler)
# cfg.DISPATCHER.add_handler(summary_handler)
# cfg.DISPATCHER.add_handler(score_handler)
cfg.DISPATCHER.add_handler(cake_handler)
cfg.DISPATCHER.add_handler(bici_handler)
# cfg.DISPATCHER.add_handler(series_handler)
# cfg.DISPATCHER.add_handler(stats_handler)
# cfg.DISPATCHER.add_handler(sotm_handler)
# cfg.DISPATCHER.add_handler(match_handler)
# cfg.DISPATCHER.add_handler(new_quotes_handler)
cfg.DISPATCHER.add_handler(night_quotes_handler)
# cfg.DISPATCHER.add_handler(log_handler)
# cfg.DISPATCHER.add_handler(remind_handler)
# cfg.DISPATCHER.add_handler(matiz_handler)
# cfg.DISPATCHER.add_handler(fischia_handler)

logger = log.set_logging()
cfg.UPDATER.start_polling()
logger.info('Bet_Bot started.')
cfg.UPDATER.idle()
