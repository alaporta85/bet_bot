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
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
updater.start_polling()
