from telegram.ext import Updater
from telegram.ext import CommandHandler
import selenium_lottomatica as sl
import db_functions as dbf
import datetime

f = open('/Users/andrea/Desktop/token.txt', 'r')
updater = Updater(token=f.readline())
f.close()
dispatcher = updater.dispatcher


def todays_date():

    date = str(datetime.date.today())
    date = '{}-{}-{}'.format(date.split('-')[2],
                             date.split('-')[1],
                             date.split('-')[0])

    return date


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def ask_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='''
There are 7 leagues available:

    - SERIE A
    - SERIE B
    - PREMIER LEAGUE
    - PRIMERA DIVISION
    - BUNDESLIGA
    - LIGUE 1
    - EREDIVISIE


If the bet is one of the following:

    - ESITO FINALE 1X2
    - UNDER/OVER
    - ESITO 1 TEMPO 1X2
    - UNDER/OVER PRIMO TEMPO
    - UNDER/OVER SECONDO TEMPO
    - GOAL/NO GOAL
    - ESITO FINALE 1X2 HANDICAP
    - ESITO FINALE 1X2 + GOAL/NOGOAL
    - ESITO FINALE 1X2 + U/O
    - DOPPIA CHANCE + UNDER/OVER
    - GOAL/NOGOAL + U/O 2,5

The message has to be sent in the form 'team_bet'.

    Example1: milan_x pt
    Example2: milan_gg + over 2.5
    Example3: milan_under 3.5 pt


IMPORTANT:

    1. 'team' can be either team1 or team2, it does NOT matter.
    2. 'team' and 'bet' ALWAYS need to be separated by '_'.
    3. different parts of the bet need a blank space as separator:

        - wrong: milan_over2.5
        - correct: milan_over 2.5

    4. 'combo' bets need the sign ' + ' as separator (notice blank spaces):

        - wrong: milan_gg over 2.5
        - wrong: milan_gg+over 2.5
        - correct: milan_gg + over 2.5

    5. CAPS do NOT matter: 'milan' and 'MILAN' they both work.


If the bet is not between those fields, message has to be sent in the form
'league_team_field_bet'.

    Example1: serie a_milan_esito 1 tempo/finale_1-x
    Example2: primera division_real madrid_pari/dispari_pari
    Example3: ligue 1_nizza_tricombo_1 ng under

In this case all inputs need to be EXACTLY as in the webpage.''')


def quote(bot, update, args):

    '''It finds the quote, save the bet in temporary and quotes2017 tables
       and send a message to summarize the bet and check it.'''

    # User sending the message
    first_name = update.message.from_user.first_name

    # Today's date
    date = todays_date()

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
    guess = ' '.join(args).upper()

    try:
        league, team1, team2, bet, bet_quote, field, url = (
                sl.look_for_quote(guess))

        # Update tables
        db, c = dbf.start_db()
        c.execute('''INSERT INTO matches (url, user, date, league, team1,
                                          team2, field, bet, quote, status)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (url, first_name, date, league, team1, team2,
                   field, bet, bet_quote, 'Not Confirmed'))

        db.commit()
        db.close()

        printed_bet = '{} - {} {} {} @{}'.format(team1, team2, field, bet,
                                                 bet_quote)

        bot.send_message(chat_id=update.message.chat_id,
                         text=('{}\n' +
                               'Use /confirm or /cancel to finalize your bet.')
                         .format(printed_bet))

    except ValueError:
        # If input is wrong
        message = sl.look_for_quote(guess)
        bot.send_message(chat_id=update.message.chat_id, text=message)


def confirm(bot, update):

    '''Delete the bet from the temporary table and update the staus in
       quote2017'''

    first_name = update.message.from_user.first_name
    date = todays_date()

    bet_id = dbf.get_value('bets_id', 'bets', 'date', date)

    db, c = dbf.start_db()

    if not bet_id:

        c.execute('''INSERT INTO bets (date, result) VALUES (?, ?)''',
                  (date, 'Unknown'))
        last_id = c.lastrowid

        c.execute('''UPDATE matches SET bets_id = ?, status = ? WHERE user = ?
                  AND status = ?''', (last_id, 'Confirmed',
                                      first_name, 'Not Confirmed'))
    else:
        c.execute('''UPDATE matches SET bets_id = ?, status = ? WHERE user = ?
                  AND status = ?''', (bet_id, 'Confirmed',
                                      first_name, 'Not Confirmed'))

    db.commit()
    db.close()

    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been placed correctly.'
                     .format(first_name))


def cancel(bot, update):

    '''Delete the bet from the temporary and quote2017 tables.'''

    first_name = update.message.from_user.first_name
    db, c = dbf.start_db()
    c.execute('''DELETE FROM matches WHERE user = ? and status = ?''',
              (first_name, 'Not Confirmed'))
    db.commit()
    db.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been canceled.'.format(first_name))


start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', ask_help)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
updater.start_polling()
