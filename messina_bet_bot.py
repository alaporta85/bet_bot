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
    chat_id = update.message.chat_id
    return bot.send_photo(chat_id=chat_id, photo=open('cake.png', 'rb'))


def bike(bot, update):
    chat_id = update.message.chat_id
    return bot.send_audio(chat_id=chat_id, audio=open('bici.mp3', 'rb'))


def cancel(bot, update, text: str = ''):

    """
    Delete the 'Not Confirmed' match from 'predictions' table.
    """

    chat_id = update.message.chat_id
    user = utl.get_nickname(update)

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.nothing_pending(nickname=user):
        return bot.send_message(chat_id=chat_id,
                                text='Nessun pronostico da eliminare')

    dbf.db_delete(table='predictions',
                  where=f'user = "{user}" AND status = "Not Confirmed"')
    utl.remove_bet_without_preds()

    if not text:
        return bot.send_message(chat_id=chat_id, text='Pronostico eliminato')
    else:
        return bot.send_message(chat_id=chat_id, text=text)


def confirm(bot, update):

    """
    Confirm the match and update the database.
    """

    chat_id = update.message.chat_id
    user = utl.get_nickname(update)

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.nothing_pending(nickname=user):
        return bot.send_message(chat_id=chat_id,
                                text='Nessun pronostico da confermare')

    if utl.match_already_chosen(nickname=user):
        return cancel(bot, update,
                      text='Pronostico non valido perché già presente')

    if utl.match_already_started(nickname=user):
        return cancel(bot, update, text='Match già iniziato')

    if utl.quote_outside_limits(nickname=user):
        return cancel(bot, update, text='Quota fuori limiti')

    # Remove other "Not Confirmed" preds of the same match, if any
    utl.remove_pending_same_match(nickname=user)

    # Update prediction status
    dbf.db_update(table='predictions',
                  columns=['status'],
                  values=['Confirmed'],
                  where=f'user = "{user}" AND status = "Not Confirmed"')

    # Insert bet in the table "to_play"
    bet_id = utl.get_pending_bet_id()
    utl.update_to_play_table(nickname=user, bet_id=bet_id)

    # Notify user in private chat
    bot.send_message(chat_id=chat_id, text='Pronostico aggiunto correttamente')

    # Send summary in group chat
    summary = utl.create_summary_pending_bet()
    bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID, text=summary)

    # Play the bet automatically
    if utl.autoplay():
        # TODO activate again when "play" command is ready
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


def fischia(bot, update):

    """
    Send random photo of Mazzarri.
    """

    chat_id = update.message.chat_id
    walter = random.choice(os.listdir('Mazzarri/'))
    return bot.send_photo(chat_id=chat_id,
                          photo=open(f'Mazzarri/{walter}', 'rb'))


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


def get(bot, update, args: list):

    """
    /get team     -> Return all quotes of the match, if found
    /get team_bet -> Return the requested quote, if found
    """

    chat_id = update.message.chat_id
    text = ' '.join(args).upper()

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.wrong_format(input_text=text):
        message = ('Formato non corretto. ' +
                   'Ex:\n\t- /get squadra_pronostico\n\t- /get squadra')
        return bot.send_message(chat_id=chat_id, text=message)

    team = utl.fix_team_name(text.split('_')[0])
    if not team:
        return bot.send_message(chat_id=chat_id,
                                text='Squadra non riconosciuta')

    match_details = utl.get_match_details(team_name=team)
    if not match_details:
        return bot.send_message(chat_id=chat_id,
                                text=f'Nessun match trovato per {team}')

    # If only team is sent, send all quotes of that match
    if '_' not in text:
        standard, combo = utl.all_bets_per_team(team_name=team)

        if not combo:
            return bot.send_message(chat_id=chat_id, text=standard)

        bot.send_message(parse_mode='MarkdownV2', chat_id=chat_id,
                         text=f'`{standard}`')
        return bot.send_message(parse_mode='MarkdownV2', chat_id=chat_id,
                                text=f'`{combo}`')

    # Try to recognize the bet sent by user
    bet = text.split('_')[1]
    bet = utl.fix_bet_name(bet)
    if not bet:
        return bot.send_message(chat_id=chat_id,
                                text='Pronostico non riconosciuto')

    # Extract match details
    match_id, league, team1, team2, dt, _ = match_details[0]
    team1 = team1.replace('*', '')
    team2 = team2.replace('*', '')

    quote = utl.get_bet_quote(match_id=match_id, bet_name=bet)
    if not quote:
        return bot.send_message(chat_id=chat_id, text='Pronostico non quotato')

    bet_id = utl.get_pending_bet_id()
    if not bet_id:
        bet_id = utl.insert_new_bet_entry()

    # Insert prediction as "Not Confirmed"
    user = utl.get_nickname(update)
    pred_id = dbf.db_insert(
            table='predictions',
            columns=['bet_id', 'user', 'date', 'team1', 'team2',
                     'league', 'bet_alias', 'quote', 'status'],
            values=[bet_id, user, dt, team1, team2,
                    league, bet, quote, 'Not Confirmed'],
            last_index=True)

    # Remove other pending predictions the user might have
    dbf.db_delete(table='predictions',
                  where=(f'id != {pred_id} AND user = "{user}" AND ' +
                         'status = "Not Confirmed"'))

    # Ask user for confirmation
    bet_details = '{} - {} {} @{}'.format(team1, team2, bet, quote)
    message = f'{bet_details}\n\n/confirm                /cancel'
    return bot.send_message(chat_id=chat_id, text=message)


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


def matiz(bot, update):
    chat_id = update.message.chat_id
    return bot.send_photo(chat_id=chat_id, photo=open('matiz.png', 'rb'))


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


def night_quotes(bot, update):

    """
    Fill the db with the new quotes for all leagues.
    """

    try:
        role = utl.get_role(update)
    except AttributeError:
        role = 'Admin'

    if role == 'Admin':

        # Start scraping
        start = time.time()
        cfg.LOGGER.info('NIGHT_QUOTES - Nightly job: Updating quote...')
        sf.scrape_all_quotes()
        mins, secs = utl.time_needed(start)
        cfg.LOGGER.info(f'NIGHT_QUOTES - Whole process took {mins}:{secs}.')

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
# TODO change for match_already_started()
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


def remind(bot, update):

    """
    Send a message to remind the matches of a bet which is Placed but
    still open.
    """

    chat_id = update.message.chat_id
    message = utl.create_summary_placed_bets()
    return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)


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


def send_log(bot, update):
    chat_id = update.message.chat_id
    return bot.send_document(chat_id=chat_id,
                             document=open('logs/bet_bot.log', 'rb'))


def series(bot, update):

    """
    Send bar plot of positive and negative series.
    """

    chat_id = update.message.chat_id
    return bot.send_photo(chat_id=chat_id, photo=open('series.png', 'rb'))


def sotm(bot, update):

    """
    Send bar plot of the best/worst per month.
    """

    chat_id = update.message.chat_id
    return bot.send_photo(chat_id=chat_id, photo=open('sotm.png', 'rb'))


def start(bot, update):
    chat_id = update.message.chat_id
    return bot.send_message(chat_id=chat_id, text="Iannelli suca")


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


def summary(bot, update):

    """
    Send the summary of the matches already confirmed before playong the bet.
    """

    chat_id = update.message.chat_id
    message = utl.create_summary_pending_bet()
    return bot.send_message(parse_mode='HTML', chat_id=chat_id, text=message)


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
fischia_handler = CommandHandler('fischia', fischia)
get_handler = CommandHandler('get', get, pass_args=True)
# help_quote_handler = CommandHandler('help_quote', help_quote)
# help_stats_handler = CommandHandler('help_stats', help_stats)
# info_handler = CommandHandler('info', info)
log_handler = CommandHandler('log', send_log)
# match_handler = CommandHandler('match', match, pass_args=True)
matiz_handler = CommandHandler('matiz', matiz)
# new_quotes_handler = CommandHandler('new_quotes', new_quotes, pass_args=True)
night_quotes_handler = CommandHandler('night_quotes', night_quotes)
# play_handler = CommandHandler('play', play, pass_args=True)
remind_handler = CommandHandler('remind', remind)
# score_handler = CommandHandler('score', score, pass_args=True)
series_handler = CommandHandler('series', series)
sotm_handler = CommandHandler('sotm', sotm)
start_handler = CommandHandler('start', start)
# stats_handler = CommandHandler('stats', stats)
summary_handler = CommandHandler('summary', summary)
# update_handler = CommandHandler('update', update_results)

# Nightly quotes updating
update_quotes = cfg.UPDATER.job_queue
# update_quotes.run_repeating(night_quotes, 86400,
#                             first=datetime.time(1, 00, 00))

update_tables = cfg.UPDATER.job_queue
# update_tables.run_repeating(update_results, 86400,
# 							first=datetime.time(3, 00, 00))

cfg.DISPATCHER.add_handler(start_handler)
# cfg.DISPATCHER.add_handler(help_quote_handler)
# cfg.DISPATCHER.add_handler(help_stats_handler)
# cfg.DISPATCHER.add_handler(info_handler)
cfg.DISPATCHER.add_handler(get_handler)
cfg.DISPATCHER.add_handler(confirm_handler)
cfg.DISPATCHER.add_handler(cancel_handler)
# cfg.DISPATCHER.add_handler(delete_handler)
# cfg.DISPATCHER.add_handler(play_handler)
# cfg.DISPATCHER.add_handler(update_handler)
cfg.DISPATCHER.add_handler(summary_handler)
# cfg.DISPATCHER.add_handler(score_handler)
cfg.DISPATCHER.add_handler(cake_handler)
cfg.DISPATCHER.add_handler(bici_handler)
cfg.DISPATCHER.add_handler(series_handler)
# cfg.DISPATCHER.add_handler(stats_handler)
cfg.DISPATCHER.add_handler(sotm_handler)
# cfg.DISPATCHER.add_handler(match_handler)
# cfg.DISPATCHER.add_handler(new_quotes_handler)
cfg.DISPATCHER.add_handler(night_quotes_handler)
cfg.DISPATCHER.add_handler(log_handler)
cfg.DISPATCHER.add_handler(remind_handler)
cfg.DISPATCHER.add_handler(matiz_handler)
cfg.DISPATCHER.add_handler(fischia_handler)

cfg.UPDATER.start_polling()
cfg.LOGGER.info('Bet_Bot started.')
cfg.UPDATER.idle()
