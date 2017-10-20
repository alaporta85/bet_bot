from telegram.ext import Updater
from telegram.ext import CommandHandler
import selenium_lottomatica3 as sl

f = open('/Users/andrea/Desktop/token.txt', 'r')
updater = Updater(token=f.readline())
f.close()
dispatcher = updater.dispatcher


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def quote(bot, update, args):

    first_name = update.message.from_user.first_name

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
    guess = ' '.join(args).upper()

    team1, team2, right_bet, bet_quote = sl.look_for_quote(guess)

    bet = '%s - %s %s @%.1f' % (team1, team2, right_bet, float(bet_quote))

    if type(bet_quote) == str:
        bot.send_message(chat_id=update.message.chat_id, text=bet_quote)
    else:
        sl.insert_temp(first_name, bet)
        bot.send_message(chat_id=update.message.chat_id,
                         text=('%s\n' +
                               'Use /confirm or /cancel to finalize your bet.')
                         % bet)


def confirm(bot, update):
    first_name = update.message.from_user.first_name
    sl.delete_temp(first_name)
    bot.send_message(chat_id=update.message.chat_id,
                     text='%s, your bet has been placed correctly.' % first_name)


def cancel(bot, update):
    first_name = update.message.from_user.first_name
    sl.delete_temp(first_name)
    bot.send_message(chat_id=update.message.chat_id,
                     text='%s, your bet has been canceled.' % first_name)


start_handler = CommandHandler('start', start)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
updater.start_polling()
