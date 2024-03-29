# -*- coding: utf-8 -*-

import os
import time
import random
import datetime

from telegram.ext import CommandHandler

import utils as utl
import config as cfg
import db_functions as dbf
import scraping_functions as scrf
import play_update_functions as plupf
import stats_functions as stf
import jobs as jobs


def bike(update, context):
    chat_id = update.message.chat_id
    return context.bot.send_audio(chat_id=chat_id,
                                  audio=open('bici.mp3', 'rb'))


def budget(update, context):
    chat_id = update.message.chat_id
    budget = utl.get_budget_from_db()
    return context.bot.send_message(chat_id=chat_id, text=f'{budget}€')


def cake(update, context):
    chat_id = update.message.chat_id
    return context.bot.send_photo(chat_id=chat_id,
                                  photo=open('cake.png', 'rb'))


def cancel(update, context, text: str = ''):

    """
    Delete the 'Not Confirmed' match from 'predictions' table.
    """

    chat_id = update.message.chat_id
    user = utl.get_nickname(update)

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.nothing_pending(nickname=user):
        return context.bot.send_message(chat_id=chat_id,
                                text='Nessun pronostico da eliminare')

    dbf.db_delete(table='predictions',
                  where=f'user = "{user}" AND status = "Not Confirmed"')
    utl.remove_bet_without_preds()

    if not text:
        return context.bot.send_message(chat_id=chat_id,
                                        text='Pronostico eliminato')
    else:
        return context.bot.send_message(chat_id=chat_id, text=text)


def confirm(update, context):

    """
    Confirm the match and update the database.
    """

    chat_id = update.message.chat_id
    user = utl.get_nickname(update)

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.nothing_pending(nickname=user):
        return context.bot.send_message(chat_id=chat_id,
                                text='Nessun pronostico da confermare')

    if utl.match_already_chosen(nickname=user):
        return cancel(update, context,
                      text='Pronostico non valido perché già presente')

    if utl.match_already_started(table='predictions', nickname=user):
        return cancel(update, context, text='Match già iniziato')

    if utl.quote_outside_limits(nickname=user):
        return cancel(update, context, text='Quota fuori limiti')

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
    context.bot.send_message(chat_id=chat_id,
                             text='Pronostico aggiunto correttamente')

    # Send summary in group chat
    summary = utl.create_summary_pending_bet()
    context.bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID,
                             text=summary)

    # Play the bet automatically
    if utl.autoplay():
        return play(update, context)


def delete(update, context):

    """
    Delete the 'Confirmed' match from 'predictions' table.
    """

    chat_id = update.message.chat_id
    user = utl.get_nickname(update)

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    pred_to_delete = utl.prediction_to_delete(nickname=user)
    if not pred_to_delete:
        return context.bot.send_message(chat_id=chat_id,
                                text='Nessun pronostico da eliminare')

    dbf.db_delete(table='predictions', where=f'id = {pred_to_delete}')

    dbf.db_delete(table='to_play', where=f'pred_id = {pred_to_delete}')

    utl.remove_bet_without_preds()

    context.bot.send_message(chat_id=chat_id, text='Pronostico eliminato')

    # Send summary in group chat
    summary_updated = utl.create_summary_pending_bet()
    return context.bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID,
                            text=f'Pronostico eliminato.\n\n{summary_updated}')


def fischia(update, context):

    """
    Send random photo of Mazzarri.
    """

    chat_id = update.message.chat_id
    walter = random.choice(os.listdir('Mazzarri/'))
    return context.bot.send_photo(chat_id=chat_id,
                          photo=open(f'Mazzarri/{walter}', 'rb'))


def get(update, context):

    """
    /get team       -> Return all quotes of the match, if found
    /get team_bet   -> Return the requested quote, if found
    /get team_quote -> Return all the bets with the specified quote, if found
    """

    args = context.args
    chat_id = update.message.chat_id
    text = ' '.join(args).upper()

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if utl.wrong_format(input_text=text):
        message = ('Formato non corretto. ' +
                   'Ex:\n\t- /get squadra_pronostico\n\t- /get squadra')
        return context.bot.send_message(chat_id=chat_id, text=message)

    team = utl.fix_team_name(text.split('_')[0])
    if not team:
        return context.bot.send_message(chat_id=chat_id,
                                text='Squadra non riconosciuta')

    match_details = utl.get_match_details(team_name=team)
    if not match_details:
        return context.bot.send_message(chat_id=chat_id,
                                text=f'Nessun match trovato per {team}')

    # If only team is sent, send all quotes of that match
    if '_' not in text:
        standard, combo = utl.all_bets_per_team(team_name=team)

        if not combo:
            return context.bot.send_message(chat_id=chat_id, text=standard)

        context.bot.send_message(parse_mode='MarkdownV2', chat_id=chat_id,
                                 text=f'`{standard}`')
        return context.bot.send_message(parse_mode='MarkdownV2',
                                        chat_id=chat_id, text=f'`{combo}`')

    # Try to recognize the bet sent by user
    bet = text.split('_')[1]
    bet = utl.fix_bet_name(bet)
    if not bet:
        return context.bot.send_message(chat_id=chat_id,
                                text='Pronostico non riconosciuto')

    # Extract match details
    match_id, league, team1, team2, dt, _ = match_details[0]
    team1 = team1.replace('*', '')
    team2 = team2.replace('*', '')

    quote = utl.get_bet_quote(match_id=match_id, bet_name=bet)
    if not quote:
        return context.bot.send_message(chat_id=chat_id,
                                        text='Pronostico non quotato')

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
    return context.bot.send_message(chat_id=chat_id, text=message)


# def info(update, context):
#
#     # TODO rewrite message
#
#     chat_id = update.message.chat_id
#     if utl.wrong_chat(chat_id=chat_id):
#         message_id = update.message.message_id
#         context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
#         return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
#                                 text='Usa questo gruppo per i comandi.')
#
#     f = open('Messages/info.txt', 'r')
#     content = f.readlines()
#     f.close()
#
#     message = ''
#     for row in content:
#         message += row
#
#     return context.bot.send_message(chat_id=chat_id, text=message)


def match(update, context):

    """
    Return the matches of the requested day.
    """

    args = context.args
    chat_id = update.message.chat_id

    if utl.wrong_chat(chat_id=chat_id):
        message_id = update.message.message_id
        context.bot.deleteMessage(chat_id=chat_id, message_id=message_id)
        return context.bot.send_message(chat_id=utl.get_user_chat_id(update),
                                text='Usa questo gruppo per i comandi.')

    if not args:
        message = 'Inserisci il giorno. Ex: /match sab'
        return context.bot.send_message(chat_id=chat_id, text=message)

    dayname = args[0][:3]
    isoweekday = utl.from_dayname_to_iso(dayname=dayname)
    if not isoweekday:
        message = 'Giorno non trovato'
    else:
        dt = utl.weekday_to_dt(isoweekday=isoweekday)
        message = utl.matches_per_day(dt=dt)
    return context.bot.send_message(parse_mode='MarkdownV2', chat_id=chat_id,
                            text=f'`{message}`')


def matiz(update, context):
    chat_id = update.message.chat_id
    return context.bot.send_photo(chat_id=chat_id,
                                  photo=open('matiz.png', 'rb'))


# def new_quotes(update, context, args):  # DONE
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
# 		return context.bot.send_message(chat_id=update.message.chat_id,
# 		                        text='Fatti i cazzi tuoi')
# 	else:
#
# 		if not args:
# 			message = 'Insert leagues. Ex. /new_quotes serie a, ligue 1'
# 			return context.bot.send_message(chat_id=chat_id, text=message)
#
# 		# Format the input and send a warning if it is wrong
# 		args = ' '.join(args).split(',')
# 		args = [arg[1:] if arg[0] == ' ' else arg for arg in args]
# 		args = [arg[:-1] if arg[-1] == ' ' else arg for arg in args]
# 		for arg in args:
# 			if arg.upper() not in cfg.countries:
# 				leagues = ', '.join([league for league in cfg.countries])
# 				return context.bot.send_message(
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


# DONE
def night_quotes(update, context):

    """
    Fill the db with the new quotes for all leagues.
    """

    if utl.get_role(update) == 'Admin':
        cfg.JOB_QUEUE.run_once(jobs.job_night_quotes, when=3)
    else:
        chat_id = update.message.chat_id
        return context.bot.send_message(chat_id=chat_id,
                                        text='Fatti i cazzi tuoi')


# def play(update, context):
#
#     """
#     Play the bet online.
#     """
#
#     # Check matches to play
#     available = utl.get_preds_available_to_play()
#     if not available:
#         pending_txt = utl.remove_not_confirmed_before_play()
#         too_late_txt = utl.remove_too_late_before_play()
#         message = f'{pending_txt}\n{too_late_txt}\n\nNessun pronostico attivo'
#         return context.bot.send_message(chat_id=cfg.GROUP_ID, text=message)
#
#     args = context.args
#     # Euros to bet
#     euros = utl.euros_to_play(args)
#
#     # Message to update
#     n_bets = len(available)
#     live_info = 'Pronostici aggiunti: {}/{}'
#     mess_id = context.bot.send_message(chat_id=cfg.GROUP_ID,
#                                text=live_info.format(0, n_bets)).message_id
#
#     # Go to main page
#     brow = scrf.open_browser()
#     brow.get(cfg.MAIN_PAGE)
#     time.sleep(5)
#     scrf.deny_cookies(brow=brow)
#     time.sleep(5)
#
#     # Add all predictions
#     for i, (url, panel, field, bet) in enumerate(available, 1):
#         brow.get(url)
#         plupf.add_bet_to_basket(brow, panel, field, bet)
#         context.bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id,
#                               text=live_info.format(i, n_bets))
#
#     # Insert euros to bet
#     plupf.insert_euros(brow, euros)
#
#     # Login
#     brow = plupf.login(brow=brow)
#     live_info = f'Pronostici aggiunti: {n_bets}/{n_bets}\n\nLogged in'
#     context.bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id,
#                           text=live_info)
#
#     # Budget before playing
#     money_before = plupf.get_budget(brow)
#
#     # Place bet
#     plupf.place_bet(brow)
#
#     # Budget after playing
#     money_after = plupf.get_money_after(brow, before=money_before)
#
#     if money_after < money_before:
#         cfg.LOGGER.info('PLAY - Bet has been played.')
#
#         if money_after != money_before - euros:
#             msg = "L'importo scommesso è diverso da quello selezionato."
#             context.bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID,
#                                      text=msg)
#             cfg.LOGGER.info(f'PLAY - {msg}. Money before: {money_before}, '
#                             f'euros placed: {euros},'
#                             f'money after: {money_after}')
#
#         # Retrieve bet_id
#         bet_id = utl.get_pending_bet_id()
#
#         # Update bet table
#         dbf.db_update(
#                 table='bets',
#                 columns=['date', 'euros', 'status'],
#                 values=[datetime.datetime.now().replace(microsecond=0),
#                         euros, 'Placed'],
#                 where=f'id = {bet_id}')
#
#         # Empty table with bets
#         dbf.empty_table(table='to_play')
#
#         # Update table with budget
#         utl.update_budget(budget=money_after)
#
#         # Send summary
#         prize = utl.get_quotes_prod(bet_id=bet_id)
#         msg = 'Scommessa giocata correttamente.\n\n'
#         msg += utl.create_list_of_matches(bet_id=bet_id)
#         msg += f'\nVincita: <b>{prize*euros: .2f} €</b>\n\n\n'
#         msg += f'\nBudget aggiornato: <b>{money_after} €</b>'
#         context.bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID,
#                                  text=msg)
#     else:
#         msg = 'Non è stato possibile giocare la scommessa.'
#         context.bot.send_message(chat_id=cfg.GROUP_ID, text=msg)
#
#     brow.quit()


def play(update, context):

    """
    Play the bet online.
    """

    # Check matches to play
    available = utl.get_preds_available_to_play()
    if not available:
        pending_txt = utl.remove_not_confirmed_before_play()
        too_late_txt = utl.remove_too_late_before_play()
        message = f'{pending_txt}\n{too_late_txt}\n\nNessun pronostico attivo'
        return context.bot.send_message(chat_id=cfg.GROUP_ID, text=message)

    args = context.args
    # Euros to bet
    euros = utl.euros_to_play(args)

    # Message to update
    n_bets = len(available)
    live_info = 'Pronostici aggiunti: {}/{}'
    mess_id = context.bot.send_message(chat_id=cfg.GROUP_ID,
                               text=live_info.format(0, n_bets)).message_id

    # Go to main page
    brow = scrf.open_browser(url=cfg.MAIN_PAGE)

    # Add all predictions
    for i, (url, panel, field, bet) in enumerate(available, 1):
        brow.get(url)
        plupf.add_bet_to_basket(brow, panel, field, bet)
        context.bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id,
                              text=live_info.format(i, n_bets))

    # Insert euros to bet
    plupf.insert_euros(brow, euros)

    # Login
    brow = plupf.login(brow=brow)
    live_info = f'Pronostici aggiunti: {n_bets}/{n_bets}\n\nLogged in'
    context.bot.edit_message_text(chat_id=cfg.GROUP_ID, message_id=mess_id,
                          text=live_info)

    # Place bet
    plupf.place_bet(brow)

    cfg.LOGGER.info('PLAY - Bet has been played.')

    # Retrieve bet_id
    bet_id = utl.get_pending_bet_id()

    # Update bet table
    dbf.db_update(
            table='bets',
            columns=['date', 'euros', 'status'],
            values=[datetime.datetime.now().replace(microsecond=0),
                    euros, 'Placed'],
            where=f'id = {bet_id}')

    # Empty table with bets
    dbf.empty_table(table='to_play')

    # Update table with budget
    new_budget = round(utl.get_budget_from_db() - euros, 2)
    utl.update_budget(budget=new_budget)

    # Send summary
    prize = utl.get_quotes_prod(bet_id=bet_id)
    msg = 'Scommessa giocata correttamente.\n\n'
    msg += utl.create_list_of_matches(bet_id=bet_id)
    msg += f'\nVincita: <b>{prize*euros: .2f} €</b>\n\n\n'
    msg += f'\nBudget aggiornato: <b>{new_budget} €</b>'
    context.bot.send_message(parse_mode='HTML', chat_id=cfg.GROUP_ID,
                             text=msg)

    brow.quit()


def qrange(update, context):
    args = context.args
    chat_id = update.message.chat_id

    if utl.qrange_input_is_wrong(args):
        message = utl.qrange_input_is_wrong(user_input=args)
        return context.bot.send_message(chat_id=chat_id, text=message)

    day, *quotes = args[0].split('_')
    quotes = [float(i.replace(',', '.')) for i in quotes]
    qmin, qmax = sorted(quotes)

    print('a')


def remind(update, context):

    """
    Send a message to remind the matches of a bet which is Placed but
    still open.
    """

    chat_id = update.message.chat_id
    message = utl.create_summary_placed_bets()
    return context.bot.send_message(parse_mode='HTML', chat_id=chat_id,
                                    text=message)


def score(update, context):

    """
    Send the bar plot of the score.
    """

    args = context.args
    chat_id = update.message.chat_id

    if not args:
        return context.bot.send_photo(chat_id=chat_id,
                              photo=open(f'score_{cfg.YEARS[-1]}.png', 'rb'))

    year = args[0]
    try:
        return context.bot.send_photo(
                chat_id=chat_id,
                photo=open(f'score_{year}.png', 'rb'))
    except FileNotFoundError:
        return context.bot.send_message(
                chat_id=chat_id,
                text='Formato incorrecto. Ex: 2017-2018 or "general"')


def send_log(update, context):
    chat_id = update.message.chat_id
    return context.bot.send_document(chat_id=chat_id,
                             document=open('logs/bet_bot.log', 'rb'))


def series(update, context):

    """
    Send bar plot of positive and negative series.
    """

    chat_id = update.message.chat_id
    return context.bot.send_photo(chat_id=chat_id,
                                  photo=open('series.png', 'rb'))


def sotm(update, context):

    """
    Send bar plot of the best/worst per month.
    """

    chat_id = update.message.chat_id
    return context.bot.send_photo(chat_id=chat_id,
                                  photo=open('sotm.png', 'rb'))


def start(update, context):
    chat_id = update.message.chat_id
    return context.bot.send_message(chat_id=chat_id, text="Iannelli suca")


def stats(update, context):

    chat_id = update.message.chat_id

    message_money = stf.money()
    message_perc = stf.abs_perc()
    message_teams = stf.stats_on_teams()
    message_bets = stf.stats_on_bets()
    message_quotes = stf.stats_on_quotes()
    message_combos = stf.stats_on_combos()

    fin_mess = (message_money + message_perc + message_teams +
                message_bets + message_quotes + message_combos)

    return context.bot.send_message(parse_mode='HTML', chat_id=chat_id,
                                    text=fin_mess)


def summary(update, context):

    """
    Send the summary of the matches already confirmed before playong the bet.
    """

    chat_id = update.message.chat_id
    message = utl.create_summary_pending_bet()
    return context.bot.send_message(parse_mode='HTML', chat_id=chat_id,
                                    text=message)


def update_score(update, context):
    cfg.JOB_QUEUE.run_once(jobs.job_update_score, when=3,
                           context=update.message.chat_id)


bici_handler = CommandHandler('bici', bike)
budget_handler = CommandHandler('budget', budget)
cake_handler = CommandHandler('cake', cake)
cancel_handler = CommandHandler('cancel', cancel)
confirm_handler = CommandHandler('confirm', confirm)
delete_handler = CommandHandler('delete', delete)
fischia_handler = CommandHandler('fischia', fischia)
get_handler = CommandHandler('get', get)
# info_handler = CommandHandler('info', info)
log_handler = CommandHandler('log', send_log)
match_handler = CommandHandler('match', match)
matiz_handler = CommandHandler('matiz', matiz)
# new_quotes_handler = CommandHandler('new_quotes', new_quotes)
night_quotes_handler = CommandHandler('night_quotes', night_quotes)
play_handler = CommandHandler('play', play)
qrange_handler = CommandHandler('qrange', qrange)
remind_handler = CommandHandler('remind', remind)
score_handler = CommandHandler('score', score)
series_handler = CommandHandler('series', series)
sotm_handler = CommandHandler('sotm', sotm)
start_handler = CommandHandler('start', start)
stats_handler = CommandHandler('stats', stats)
summary_handler = CommandHandler('summary', summary)
update_handler = CommandHandler('update', update_score)

# Update database
cfg.JOB_QUEUE.run_repeating(jobs.job_update_score, interval=86400,
                            first=utl.get_start_time(hh=0, mm=15, ss=0))

# # Scrape quotes
cfg.JOB_QUEUE.run_repeating(jobs.job_night_quotes, interval=86400,
                            first=utl.get_start_time(hh=0, mm=30, ss=0))

cfg.DISPATCHER.add_handler(start_handler)
# cfg.DISPATCHER.add_handler(info_handler)
cfg.DISPATCHER.add_handler(get_handler)
cfg.DISPATCHER.add_handler(confirm_handler)
cfg.DISPATCHER.add_handler(cancel_handler)
cfg.DISPATCHER.add_handler(delete_handler)
cfg.DISPATCHER.add_handler(play_handler)
cfg.DISPATCHER.add_handler(update_handler)
cfg.DISPATCHER.add_handler(summary_handler)
cfg.DISPATCHER.add_handler(score_handler)
cfg.DISPATCHER.add_handler(cake_handler)
cfg.DISPATCHER.add_handler(bici_handler)
cfg.DISPATCHER.add_handler(budget_handler)
cfg.DISPATCHER.add_handler(series_handler)
cfg.DISPATCHER.add_handler(stats_handler)
cfg.DISPATCHER.add_handler(sotm_handler)
cfg.DISPATCHER.add_handler(match_handler)
# cfg.DISPATCHER.add_handler(new_quotes_handler)
cfg.DISPATCHER.add_handler(night_quotes_handler)
cfg.DISPATCHER.add_handler(qrange_handler)
cfg.DISPATCHER.add_handler(log_handler)
cfg.DISPATCHER.add_handler(remind_handler)
cfg.DISPATCHER.add_handler(matiz_handler)
cfg.DISPATCHER.add_handler(fischia_handler)

os.system('python Classes.py')
cfg.UPDATER.start_polling()
cfg.LOGGER.info('Bet_Bot started.')
cfg.UPDATER.idle()
