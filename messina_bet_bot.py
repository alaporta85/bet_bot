from telegram.ext import Updater
from telegram.ext import CommandHandler
import selenium_lottomatica as sl
import db_functions as dbf
import datetime
import sqlite3

f = open('/Users/andrea/Desktop/token.txt', 'r')
updater = Updater(token=f.readline())
f.close()
dispatcher = updater.dispatcher


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def quote(bot, update, args):

    '''It finds the quote, save the bet in temporary and quotes2017 tables
       and send a message to summarize the bet and check it.'''

    # User sending the message
    first_name = update.message.from_user.first_name

    # Today's date
    date = str(datetime.date.today())
    date = '%s-%s-%s' % (date.split('-')[2],
                         date.split('-')[1],
                         date.split('-')[0])

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
    guess = ' '.join(args).upper()

    try:
        team1, team2, right_bet, bet_quote, field, url = sl.look_for_quote(
                guess)

        # Update tables
        db, c = dbf.start_db()
        c.execute('''INSERT INTO quotes2017 (user, date, team1, team2, field,
                                             bet, quote)
                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (first_name, date, team1, team2, field, right_bet,
                   bet_quote))

        last_id = c.lastrowid

        c.execute('''INSERT INTO temporary (id, user, url, field, bet)
                   VALUES (?, ?, ?, ?, ?)''', (last_id, first_name, url, field,
                                               right_bet))

        db.commit()
        db.close()

        bet = '%s - %s %s %s @%.1f' % (team1, team2, field, right_bet,
                                       float(bet_quote))

        bot.send_message(chat_id=update.message.chat_id,
                         text=('%s\n' +
                               'Use /confirm or /cancel to finalize your bet.')
                         % bet)

    except ValueError:
        # If input is wrong
        message = sl.look_for_quote(guess)
        bot.send_message(chat_id=update.message.chat_id, text=message)


def confirm(bot, update):

    '''Delete the bet from the temporary table and update the staus in
       quote2017'''

    first_name = update.message.from_user.first_name
    user_id = dbf.get_value('id', 'temporary', 'user', first_name)
    dbf.delete_content('temporary', user_id)

    db, c = dbf.start_db()

    c.execute('''UPDATE quotes2017 SET status = 'Waiting' WHERE id = ?''',
              (user_id,))

    db.commit()

    bot.send_message(chat_id=update.message.chat_id,
                     text='%s, your bet has been placed correctly.'
                     % first_name)


def cancel(bot, update):

    '''Delete the bet from the temporary and quote2017 tables.'''

    first_name = update.message.from_user.first_name
    user_id = dbf.get_value('id', 'temporary', 'user', first_name)
    dbf.delete_content('temporary', user_id)
    dbf.delete_content('quotes2017', user_id)
    bot.send_message(chat_id=update.message.chat_id,
                     text='%s, your bet has been canceled.' % first_name)


def content(bot, update, args):
    message = dbf.get_table_content(args[0])
    if not len(message):
        bot.send_message(chat_id=update.message.chat_id, text='Empty')
    else:
        for bet in message:
            count = 0
            for field in bet:
                count += 1
                if count % 11:
                    bot.send_message(chat_id=update.message.chat_id,
                                     text=field)
                else:
                    bot.send_message(chat_id=update.message.chat_id,
                                     text=field + '\n')


start_handler = CommandHandler('start', start)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
content_handler = CommandHandler('content', content, pass_args=True)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(content_handler)
updater.start_polling()
