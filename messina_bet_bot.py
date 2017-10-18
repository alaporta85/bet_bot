from telegram.ext import Updater
from telegram.ext import CommandHandler
import selenium_lottomatica as sl

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

    bet_quote = sl.look_for_quote(guess)

    if type(bet_quote) == str:
        bot.send_message(chat_id=update.message.chat_id, text=bet_quote)
    else:
        sl.insert_quote(first_name, float(bet_quote))
        bot.send_message(chat_id=update.message.chat_id,
                         text='Quote played by %s is %.2f, added to db.' % (
                                 first_name, float(bet_quote)))


start_handler = CommandHandler('start', start)
quote_handler = CommandHandler('quote', quote, pass_args=True)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(quote_handler)
updater.start_polling()
