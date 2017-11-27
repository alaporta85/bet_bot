import os
import time
from telegram.ext import Updater
from telegram.ext import CommandHandler
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
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

    '''Return bets played until that moment.'''

    message = ''
    for bet in summary:
        user = bet[0]
        team1 = bet[1].title()
        team2 = bet[2].title()
        raw_bet = bet[3]
        quote = bet[4]
        message += '{}:     {}-{}    {}      @<b>{}</b>\n'.format(user, team1,
                                                                  team2,
                                                                  raw_bet,
                                                                  quote)

    return message


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def help_quote(bot, update):

    '''Instructions to insert the correct input.'''

    f = open('Messages/help_quote.txt', 'r')
    content = f.readlines()
    f.close()

    message = ''
    for row in content:
        message += row

    bot.send_message(chat_id=update.message.chat_id, text=message)


def list_of_commands(bot, update):

    f = open('Messages/list_of_commands.txt', 'r')
    content = f.readlines()
    f.close()

    message = ''
    for row in content:
        message += row

    bot.send_message(chat_id=update.message.chat_id, text=message)


def quote(bot, update, args):

    '''Try to find all the parameters from look_for_quote function. If found,
       they will be inserted in the database's table called "matches" and the
       user will be ask either to confirm or cancel the bet. It also manages
       the cases when some error occurred.'''

    if not args:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='Please insert the bet.')

    guess = ' '.join(args).upper()

    if len(guess.split('_')) != 2:
        return bot.send_message(chat_id=update.message.chat_id,
                                text=('Wrong format. Input text must ' +
                                      'have the structure "team_bet".'))
    elif '_' not in guess:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='Bet not valid. "_" is missing.')
    elif guess[0] == '_' or guess[-1] == '_':
        return bot.send_message(chat_id=update.message.chat_id,
                                text='Wrong format.')

    # User sending the message
    first_name = nickname(update.message.from_user.first_name)

    db, c = dbf.start_db()

    warning_message = bf.check_still_to_confirm(db, c, first_name)
    if warning_message:
        return bot.send_message(chat_id=update.message.chat_id,
                                text=warning_message)

    # Used to create the list confirmed_matches. This list will be used to
    # check whether a match has already been chosen
    bet_id = dbf.get_value('bet_id', 'bets', 'bet_status', 'Pending')
    confirmed_matches = list(c.execute('''SELECT pred_team1, pred_team2
                                       FROM predictions WHERE
                                       pred_status = "Confirmed"
                                       AND pred_bet = ?''', (bet_id,)))

    raw_bet = guess.split('_')[1]

    try:

        team1, team2, field_id, league_id, quote = sf.look_for_quote(guess)

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
                       league_id, field_id, raw_bet, quote, 'Not Confirmed'))

            db.commit()
            db.close()

            printed_bet = '{} - {} {} @{}'.format(team1, team2, raw_bet,
                                                  quote)

            bot.send_message(chat_id=update.message.chat_id,
                             text=('{}\n' + 'Use /confirm or /cancel to ' +
                                   'finalize your bet.').format(printed_bet))
        else:
            message = 'Match already chosen. Please change your bet.'
            bot.send_message(chat_id=update.message.chat_id, text=message)

    except SyntaxError as e:
        message = str(e)
        bot.send_message(chat_id=update.message.chat_id, text=message)

    except ConnectionError as e:
        message = str(e)
        bot.send_message(chat_id=update.message.chat_id, text=message)


def confirm(bot, update):

    '''Update the status of the bet in the "matches" table from "Not Confirmed
       to "Confirmed". If it is the first bet of the day it creates a new
       entry in the "bets" table and update the bet_id in the "matches" table.
       Else, it just uses the bet_id. It also checks whether there are others
       Not Confirmed bets of the same match. If yes, they will be deleted from
       the "matches" table.'''

    first_name = nickname(update.message.from_user.first_name)

    db, c = dbf.start_db()

    # This a list of the users who have their bets in the status
    # 'Not Confirmed'
    users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
                                pred_status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name not in users_list:
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
        dupl_message = bf.check_if_duplicate(c, first_name, ref_list,
                                             not_confirmed_matches)
        if dupl_message:
            bot.send_message(chat_id=update.message.chat_id, text=dupl_message)

    db.commit()
    db.close()

    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been placed correctly.'
                     .format(first_name))


def cancel(bot, update):

    '''Delete the "Not Confirmed" bet from "matches" table.'''

    first_name = nickname(update.message.from_user.first_name)
    db, c = dbf.start_db()

    users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
                                pred_status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name not in users_list:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='{}, you have no bet to cancel.'
                                .format(first_name))

    c.execute('''DELETE FROM predictions WHERE pred_user = ? AND
              pred_status = "Not Confirmed"''', (first_name,))

    db.commit()
    db.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been canceled.'.format(first_name))


def play_bet(bot, update, args):

    '''Manage the login and play the bet. Args input is the amount of euros
       to bet.'''

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

    matches_to_play = list(c.execute('''SELECT pred_team1, pred_team2, pred_field, bet,
                                     url, league FROM bets INNER JOIN matches
                                     on matches.bets_id = bets.bets_id WHERE
                                     bets.bets_id = ?''', (bet_id,)))

    db.close()
    browser = sf.go_to_lottomatica(0)
    count = 0
    for match in matches_to_play:
        try:
            basket_message = bf.add_bet_to_basket(browser, match, count,
                                                  mess_id, dynamic_message,
                                                  matches_to_play)

            bot.edit_message_text(chat_id=update.message.chat_id,
                                  message_id=mess_id, text=basket_message)
            count += 1
        except ConnectionError as e:
            return bot.send_message(chat_id=update.message.chat_id,
                                    text=str(e))

    time.sleep(5)
    bot.edit_message_text(chat_id=update.message.chat_id, message_id=mess_id,
                          text='Checking everything is fine...')

    # Find the basket with all the bets
    try:
        basket = ('.//nav[@id="toolbarForHidden"]/ul/' +
                  'li[@class="toolbar-nav-item ng-scope"]/a')
        sf.wait_clickable(browser, 20, basket)

        browser.find_element_by_xpath(basket).click()
    except TimeoutException:
        browser.quit()
        bot.send_message(chat_id=update.message.chat_id,
                         text=('Problem during placing the bet. ' +
                               'Please check your internet ' +
                               'connection and try again.'))

    summary_path = ('.//div[@id="toolbarContent"]/div[@id="basket"]' +
                    '//ul//span[contains(@class,"col-sm-12")]')

    summary_element = browser.find_element_by_xpath(summary_path)

    # and extract the actual number of bets present in the basket
    matches_played = int(summary_element.text.split(' ')[2][1:-1])
    browser.find_element_by_xpath(basket).click()

    # If this number is equal to the number of bets chosen to play
    if matches_played == len(matches_to_play):

        possible_win = bf.insert_euros(browser, matches_to_play,
                                       matches_played, euros)
        print(possible_win)

        # Make the login
        sf.login(browser)
        bot.edit_message_text(chat_id=update.message.chat_id,
                              message_id=mess_id,
                              text='Login...')

        button_location = './/div[@class="change-bet ng-scope"]'

        try:
            sf.wait_visible(browser, 20, button_location)
        except TimeoutException:
            browser.quit()
            bot.send_message(chat_id=update.message.chat_id,
                             text=('Problem during placing the bet. ' +
                                   'Please check if the bet is valid or ' +
                                   'the connection and try again.'))

        sf.scroll_to_element(browser, 'true',
                             browser.find_element_by_xpath(
                                     button_location))

        try:
            button_path = ('.//button[@class="button-default no-margin-' +
                           'bottom ng-scope"]')

            button_list = browser.find_elements_by_xpath(button_path)
        except NoSuchElementException:
            print('aggiorna')
            button_path = ('.//button[@class="button-default"]')
            button_list = browser.find_elements_by_xpath(button_path)
            print(len(button_list))
            for element in button_list:
                if element.is_displayed():
                    print(element.text)
###                    element.click()
                    break

        for element in button_list:
            if element.is_displayed():
                print(element.text)
###                    element.click()
                db, c = dbf.start_db()
                c.execute('''UPDATE bets SET euros = ?, prize = ?,
                          status = ? WHERE status = ?''',
                          (euros, possible_win, 'Placed', 'Pending'))
                db.commit()
                db.close()

                bot.edit_message_text(chat_id=update.message.chat_id,
                                      message_id=mess_id, text='Done!')
                break

        # Print the summary
        message = 'Bet placed correctly.\n\n'
        bet_id = dbf.get_value('bets_id', 'bets', 'result', 'Unknown')
        db, c = dbf.start_db()
        summary = list(c.execute('''SELECT user, team1, team2, field, bet
                             FROM bets INNER JOIN matches on
                             matches.bets_id = bets.bets_id WHERE
                             bets.bets_id = ?''', (bet_id,)))

        db.close()
        message += (played_bets(summary) + '\nPossible win: {}'.format(
                possible_win))
        bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
                         text=message)
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text=('Something went wrong, try again the' +
                               ' command /play.'))

    browser.quit()


def update_results(bot, update):

    '''Updates the 'result' columns in both 'bets' and 'matches' tables in the
       database.'''

    LIMIT_1 = 0
    LIMIT_2 = 0
    LIMIT_3 = 0
    LIMIT_4 = 0

    db, c = dbf.start_db()
    ref_list = list(c.execute('''SELECT bets_id, yymmdd FROM bets WHERE
                              status = "Placed" AND result = "Unknown" '''))
    db.close()

    if not ref_list:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='No bets to update.')

    bot.send_message(chat_id=update.message.chat_id,
                     text='Updating database...')

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')
    browser = webdriver.Chrome(sf.chrome_path)
    time.sleep(3)
    browser.get(url)
    time.sleep(3)

    sf.login(browser)
    time.sleep(5)

    try:
        bf.go_to_personal_area(browser, LIMIT_1)

        bf.go_to_placed_bets(browser, LIMIT_2)

        bets_updated = bf.analyze_main_table(browser, ref_list, LIMIT_3,
                                             LIMIT_4)

    except ConnectionError as e:
        browser.quit()
        return bot.send_message(chat_id=update.message.chat_id, text=str(e))

    browser.quit()

    if bets_updated:
        bot.send_message(chat_id=update.message.chat_id, text=(
                'Database updated correctly.'))
    else:
        bot.send_message(chat_id=update.message.chat_id, text=(
                "No completed bets were found. Wait for your bet's status " +
                "to be updated by Lottomatica and then try again."))


def summary(bot, update):

    bet_id = dbf.get_value('bets_id', 'bets', 'status', 'Pending')
    db, c = dbf.start_db()
    summary = list(c.execute('''SELECT user, team1, team2, raw_bet, quote
                             FROM bets INNER JOIN matches on
                             matches.bets_id = bets.bets_id WHERE
                             bets.bets_id = ?''', (bet_id,)))

    db.close()
    if summary:
        final_quote = 1
        all_quotes = [element[4] for element in summary]
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
    stf.perc_success()
    bot.send_photo(chat_id=update.message.chat_id, photo=open('score.png',
                                                              'rb'))
    os.remove('score.png')


def aver_quote(bot, update):
    stf.aver_quote()
    bot.send_photo(chat_id=update.message.chat_id, photo=open('aver_quote.png',
                                                              'rb'))
    os.remove('aver_quote.png')


def records(bot, update):
    h_message, l_message = stf.records()
    bot.send_message(chat_id=update.message.chat_id, text=h_message)
    bot.send_message(chat_id=update.message.chat_id, text=l_message)


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


def match(bot, update, args):

    if not args:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='Insert the day. Ex. /match sab')
    try:
        message = sf.fill_db_with_quotes(args[0])
        bot.send_message(chat_id=update.message.chat_id, text=message)
    except ConnectionError as e:
        return bot.send_message(chat_id=update.message.chat_id, text=str(e))
    except SyntaxError as e:
        return bot.send_message(chat_id=update.message.chat_id, text=str(e))


start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help_quote', help_quote)
commands_handler = CommandHandler('commands', list_of_commands)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
play_bet_handler = CommandHandler('play', play_bet, pass_args=True)
update_handler = CommandHandler('update', update_results)
summary_handler = CommandHandler('summary', summary)
score_handler = CommandHandler('score', score)
aver_quote_handler = CommandHandler('aver_quote', aver_quote)
records_handler = CommandHandler('records', records)
euros_lost_handler = CommandHandler('euros_lost', euros_lost)
series_handler = CommandHandler('series', series)
match_handler = CommandHandler('match', match, pass_args=True)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(commands_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(play_bet_handler)
dispatcher.add_handler(update_handler)
dispatcher.add_handler(summary_handler)
dispatcher.add_handler(score_handler)
dispatcher.add_handler(aver_quote_handler)
dispatcher.add_handler(records_handler)
dispatcher.add_handler(euros_lost_handler)
dispatcher.add_handler(series_handler)
dispatcher.add_handler(match_handler)
logger = log.set_logging()
updater.start_polling()
logger.info('Bet_Bot started.')
#updater.idle()
