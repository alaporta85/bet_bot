import time
import datetime
import selenium_lottomatica as sl
from telegram.ext import Updater
from telegram.ext import CommandHandler
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from Functions import bot_functions as bf

f = open('token.txt', 'r')
updater = Updater(token=f.readline())
f.close()

dispatcher = updater.dispatcher


def nickname(name):

    nicknames = {'Andrea': 'Testazza',
                 'Fabrizio': 'Nonno',
                 'Damiano': 'Pacco',
                 'Francesco': 'Zoppo',
                 'Gabriele': 'Nano',
                 'Ana Belen': 'Ana'}

    return nicknames[name]


def todays_date():

    date = str(datetime.date.today())
    date = '{}/{}/{}'.format(date.split('-')[2],
                             date.split('-')[1],
                             date.split('-')[0])

    return date


def handle_play_conn_err(browser, team1, team2):

    '''Quit browser and return the error message in case of ConnectionError.
       Used inside the play_bet function.'''

    browser.quit()
    message = ('Problems with the match {} - {}. '.format(team1, team2) +
               'Possible reason: bad internet connection. Please try again.')

    return message


def played_bets(summary):

    '''Return bets played until that moment.'''

    message = ''
    for bet in summary:
        user = bet[0]
        team1 = bet[1].title()
        team2 = bet[2].title()
        field = bet[3]
        result = bet[4]
        message += '{}: {}-{} / {} ---> {}\n'.format(user, team1, team2,
                                                     field, result)

    return message


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def ask_help(bot, update):

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
    elif '_' not in ''.join(args):
        return bot.send_message(chat_id=update.message.chat_id,
                                text='Bet not valid. "_" is missing.')
    # User sending the message
    first_name = nickname(update.message.from_user.first_name)

    # Today's date
    date = todays_date()

    db, c = dbf.start_db()

    # This a list of the users who have their bets in the status
    # 'Not Confirmed'
    users_list = list(c.execute('''SELECT user FROM matches WHERE
                                status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name in users_list:

        ref_list = list(c.execute('''SELECT team1, team2, field, bet, quote
                                  FROM matches WHERE status = "Not Confirmed"
                                  AND user = ?''', (first_name,)))
        db.close()
        print(ref_list)

        team1, team2, field, bet, bet_quote = ref_list[0]

        printed_bet = '{} - {} {} {} @{}'.format(team1, team2, field, bet,
                                                 bet_quote)

        return bot.send_message(chat_id=update.message.chat_id,
                                text='{}, you still have one bet to confirm.\n'
                                .format(first_name) +
                                ('{}\n' + 'Use /confirm or /cancel to ' +
                                 'finalize your bet.').format(printed_bet))

    guess = ' '.join(args).upper()
    if len(guess.split('_')) != 2:
        message = ('Wrong format. Input text must ' +
                   'have the structure "team_bet".')
        return bot.send_message(chat_id=update.message.chat_id, text=message)

    # This is used to decide whether to add or not the new bet as
    # 'Not Confirmed'. In the code below, this bet_id will be used to create
    # a list with all the matches belonging to that bet. If this list is empty
    # than the bet will be added always. On the other hand, in the case there
    # should be some matches already confirmed we first check if the bet has
    # been already chosen
    bet_id = dbf.get_value('bets_id', 'bets', 'status', 'Pending')

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')

    try:

        confirmed_matches = list(c.execute('''SELECT team1, team2, league
                                           FROM matches WHERE
                                           status = "Confirmed"
                                           AND bets_id = ?''', (bet_id,)))

        league, team1, team2, bet, bet_quote, field, url = (
                sf.look_for_quote(guess))

        if (not confirmed_matches
           or (team1, team2, league) not in confirmed_matches):

            # Update table
            c.execute('''INSERT INTO matches (url, user, ddmmyy, league, team1,
                                              team2, field, bet, quote, status)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (url, first_name, date, league, team1, team2,
                       field, bet, bet_quote, 'Not Confirmed'))

            db.commit()
            db.close()

            printed_bet = '{} - {} {} {} @{}'.format(team1, team2, field, bet,
                                                     bet_quote)

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
    date = todays_date()

    db, c = dbf.start_db()

    # This a list of the users who have their bets in the status
    # 'Not Confirmed'
    users_list = list(c.execute('''SELECT user FROM matches WHERE
                                status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name not in users_list:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='{}, you have no bet to confirm.'
                                .format(first_name))

    # Check if there is any bet with status 'Pending' in the 'bets' table
    bet_id = dbf.get_value('bets_id', 'bets', 'status', 'Pending')

    if not bet_id:

        # If not, we create it and update 'matches' table
        c.execute('''INSERT INTO bets (ddmmyy, status, result) VALUES (?, ?, ?)
                  ''', (date, 'Pending', 'Unknown'))

        last_id = c.lastrowid

        c.execute('''UPDATE matches SET bets_id = ?, status = "Confirmed"
                  WHERE user = ? AND status = "Not Confirmed"''',
                  (last_id, first_name))

        db.commit()

        # This is a list that we will take as reference. It contains a tuple
        # with the 2 teams and the league chosen by the person who is
        # confirming the bet. It will be used later to check whether there are
        # others Not Confirmed bets of the same match
        ref_list = list(c.execute('''SELECT team1, team2, league FROM bets
                                  INNER JOIN matches on
                                  matches.bets_id = bets.bets_id WHERE
                                  bets.bets_id = ? AND user = ?''',
                                  (last_id, first_name)))

    else:

        # If a Pending bet exists we just update the 'matches' table
        c.execute('''UPDATE matches SET bets_id = ?, status = "Confirmed"
                  WHERE user = ? AND status = "Not Confirmed"''',
                  (bet_id, first_name))

        db.commit()

        ref_list = list(c.execute('''SELECT team1, team2, league FROM bets
                                  INNER JOIN matches on
                                  matches.bets_id = bets.bets_id WHERE
                                  bets.bets_id = ? AND user = ?''',
                                  (bet_id, first_name)))

    # Now we delete all the bets of the same match which have not been
    # confirmed
    not_confirmed_matches = list(c.execute('''SELECT matches_id, user, team1,
                                           team2, league FROM matches WHERE
                                           status = "Not Confirmed"'''))

    for match in not_confirmed_matches:
        match_id = match[0]
        user = match[1]
        team1 = match[2]
        team2 = match[3]
        league = match[4]
        if (team1, team2, league) in ref_list:
            c.execute('''DELETE FROM matches WHERE matches_id = ?''',
                      (match_id,))
            bot.send_message(chat_id=update.message.chat_id,
                             text=('{}, your bet on the match '.format(user) +
                                   '{} - {} has '.format(team1, team2) +
                                   'been canceled because ' +
                                   '{} confirmed first.'.format(first_name)))

    db.commit()
    db.close()

    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been placed correctly.'
                     .format(first_name))


def cancel(bot, update):

    '''Delete the bet "matches" table.'''

    first_name = nickname(update.message.from_user.first_name)
    db, c = dbf.start_db()

    users_list = list(c.execute('''SELECT user FROM matches WHERE
                                status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name not in users_list:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='{}, you have no bet to cancel.'
                                .format(first_name))

    c.execute('''DELETE FROM matches WHERE user = ? AND
              status = "Not Confirmed"''', (first_name,))

    db.commit()
    db.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been canceled.'.format(first_name))


def play_bet(bot, update, args):

    '''Manage the login and play the bet. Args input is the amount of euros
       to bet.'''

    LIMIT_COUNTRY = 0

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

    # Group inside a list all the bets beloning to the bet with result
    # 'Unknown'
    bet_id = dbf.get_value('bets_id', 'bets', 'status', 'Pending')
    if not bet_id:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='No bets to play.')

    # This message will be updated during the process to keep track of all
    # the steps
    dynamic_message = 'Please wait while placing the bet.\nMatches added: {}'
    sent = bot.send_message(chat_id=update.message.chat_id,
                            text=dynamic_message.format(0))

    # Message_id will be used to update the message
    mess_id = sent.message_id

    db, c = dbf.start_db()
    matches_to_play = list(c.execute('''SELECT team1, team2, field, bet,
                                     url, league FROM bets INNER JOIN matches
                                     on matches.bets_id = bets.bets_id WHERE
                                     bets.bets_id = ?''', (bet_id,)))

    db.close()
    browser = webdriver.Firefox()
    last_league = ''
    count = 0
    for match in matches_to_play:

        team1 = match[0]
        team2 = match[1]
        field = match[2]
        bet = match[3]
        url = match[4]
        league = match[5]

        if not count:
            try:
                sf.add_first_bet(browser, url, field, bet)
                time.sleep(5)
                if not sf.check_single_bet(browser, count):
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)
                last_league = league
                count += 1
                bot.edit_message_text(chat_id=update.message.chat_id,
                                      message_id=mess_id,
                                      text=dynamic_message.format(count))

            except ConnectionError:
                message = handle_play_conn_err(browser, team1, team2)
                return bot.send_message(chat_id=update.message.chat_id,
                                        text=message)

        elif league == last_league:
            try:
                sf.find_league_button(browser, league)
                sf.add_following_bets(browser, team1, field, bet)
                time.sleep(5)
                if not sf.check_single_bet(browser, count):
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)
                last_league = league
                count += 1
                bot.edit_message_text(chat_id=update.message.chat_id,
                                      message_id=mess_id,
                                      text=dynamic_message.format(count))

            except ConnectionError:
                message = handle_play_conn_err(browser, team1, team2)
                return bot.send_message(chat_id=update.message.chat_id,
                                        text=message)
        else:
            try:
                sf.find_country_button(browser, league, LIMIT_COUNTRY)
                sf.find_league_button(browser, league)
                sf.add_following_bets(browser, team1, field, bet)
                time.sleep(5)
                if not sf.check_single_bet(browser, count):
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)
                last_league = league
                count += 1
                bot.edit_message_text(chat_id=update.message.chat_id,
                                      message_id=mess_id,
                                      text=dynamic_message.format(count))

            except ConnectionError:
                message = handle_play_conn_err(browser, team1, team2)
                return bot.send_message(chat_id=update.message.chat_id,
                                        text=message)

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

    # If this number is equal to the number of bets chosen to play
    if matches_played == len(matches_to_play):

        ticket = ('.//div[@id="toolbarContent"]/div[@id="basket"]' +
                  '//p[@class="arrow-label linkable"]')
        browser.find_element_by_xpath(ticket).click()

        input_euros = ('.//div[contains(@class,"text-right ' +
                       'amount-sign")]/input')
        euros_box = browser.find_element_by_xpath(input_euros)
        euros_box.send_keys(Keys.COMMAND, "a")
        euros_box.send_keys(euros)

        win_path = ('.//div[@class="row ticket-bet-infos"]//' +
                    'p[@class="amount"]/strong')
        win_container = browser.find_element_by_xpath(win_path)
        sf.scroll_to_element(browser, 'false', win_container)

        possible_win_default = win_container.text[2:].replace(',', '.')

        # Manipulate the possible win's format to avoid errors
        if len(possible_win_default.split('.')) == 2:
            possible_win_default = float(possible_win_default)
        else:
            possible_win_default = float(''.join(
                    possible_win_default.split('.')[:-1]))
        possible_win = round(possible_win_default * (euros/2), 2)

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
        bot.send_message(chat_id=update.message.chat_id, text=message)
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
    ref_list = list(c.execute('''SELECT bets_id, ddmmyy FROM bets WHERE
                              status = "Placed" AND result = "Unknown" '''))
    db.close()

    if not ref_list:
        return bot.send_message(chat_id=update.message.chat_id,
                                text='No bets to update.')

    bot.send_message(chat_id=update.message.chat_id,
                     text='Updating database...')

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')
    browser = webdriver.Firefox()
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
    summary = list(c.execute('''SELECT user, team1, team2, field, bet
                             FROM bets INNER JOIN matches on
                             matches.bets_id = bets.bets_id WHERE
                             bets.bets_id = ?''', (bet_id,)))

    db.close()
    if summary:
        message = played_bets(summary)
    else:
        message = 'No bets yet. Choose the first one.'

    bot.send_message(chat_id=update.message.chat_id, text=message)


start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', ask_help)
commands_handler = CommandHandler('commands', list_of_commands)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
play_bet_handler = CommandHandler('play', play_bet, pass_args=True)
update_handler = CommandHandler('update', update_results)
summary_handler = CommandHandler('summary', summary)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(commands_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(play_bet_handler)
dispatcher.add_handler(update_handler)
dispatcher.add_handler(summary_handler)
updater.start_polling()
#updater.idle()
