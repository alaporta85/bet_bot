from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from telegram.ext import Updater
from telegram.ext import CommandHandler
import selenium_lottomatica as sl
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
import datetime
import time
from selenium.webdriver.common.keys import Keys

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


def login(browser):

    f = open('login.txt', 'r')
    credentials = f.readlines()
    f.close()

    username = credentials[0][10:-1]
    password = credentials[1][10:]

    user_path = './/input[@placeholder="Username"]'
    pass_path = './/input[@placeholder="Password"]'
    button_path = './/button[@class="button-submit"]'

    user_list = browser.find_elements_by_xpath(user_path)
    pass_list = browser.find_elements_by_xpath(pass_path)
    button_list = browser.find_elements_by_xpath(button_path)

    for element in user_list:
        if element.is_displayed():
            element.send_keys(username)
            break

    for element in pass_list:
        if element.is_displayed():
            element.send_keys(password)
            break

    for element in button_list:
        if element.is_displayed():
            element.click()
            break


def todays_date():

    date = str(datetime.date.today())
    date = '{}-{}-{}'.format(date.split('-')[2],
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

    # User sending the message
    first_name = nickname(update.message.from_user.first_name)

    # Today's date
    date = todays_date()

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
    guess = ' '.join(args).upper()

    try:
        db, c = dbf.start_db()

        confirmed_matches = list(c.execute('''SELECT team1, team2, league
                                           FROM matches WHERE
                                           status = "Confirmed"'''))

        league, team1, team2, bet, bet_quote, field, url = (
                sl.look_for_quote(guess))

        if (team1, team2, league) not in confirmed_matches:
            # Update table
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
                             text=('{}\n' + 'Use /confirm or /cancel to ' +
                                   'finalize your bet.').format(printed_bet))
        else:
            message = 'Match already chosen. Please change your bet.'
            bot.send_message(chat_id=update.message.chat_id, text=message)

    except SyntaxError as e:
        # If input is wrong
        message = str(e)
        bot.send_message(chat_id=update.message.chat_id, text=message)

    except ConnectionError as e:
        message = str(e)
        bot.send_message(chat_id=update.message.chat_id, text=message)


def confirm(bot, update):

    '''Update the status of the bet in the "matches" table from "Not confirmed
       to "Confirmed". If it is the first bet of the day it creates a new
       entry in the "bets" table and update the bet_id in the "matches" table.
       Else, it just uses the bet_id.'''

    first_name = nickname(update.message.from_user.first_name)
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

    '''Delete the bet "matches" table.'''

    first_name = nickname(update.message.from_user.first_name)
    db, c = dbf.start_db()
    c.execute('''DELETE FROM matches WHERE user = ? and status = ?''',
              (first_name, 'Not Confirmed'))
    db.commit()
    db.close()
    bot.send_message(chat_id=update.message.chat_id,
                     text='{}, your bet has been canceled.'.format(first_name))


def play_bet(bot, update, args):

    '''Manage the login and play the bet. Args input is the amount of euros
       to bet.'''

    if args:
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
        bot.send_message(chat_id=update.message.chat_id, text='Please wait...')

        # Group inside a list all the bets beloning to the bet with result
        # 'Unknown'
        bet_id = dbf.get_value('bets_id', 'bets', 'result', 'Unknown')
        db, c = dbf.start_db()
        matches_to_play = list(c.execute('''SELECT team1, team2, field, bet,
                                         url, league FROM bets INNER JOIN
                                         matches on matches.bets_id = ?''',
                                         (bet_id,)))

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
#            try:
#                sl.add_quote(browser, url, field, bet)
#            except ConnectionError:
#                browser.quit()
#                message = handle_play_conn_err(browser, team1, team2)
#                bot.send_message(chat_id=update.message.chat_id,
#                                 text=message)
#                break

            if not count:
                try:
                    sl.add_first_bet(browser, url, field, bet)
                    last_league = league
                    count += 1
                    time.sleep(5)
                except ConnectionError:
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)

            elif count and league == last_league:
                try:
                    sf.find_league_button(browser, league)
                    sl.add_following_bets(browser, team1, field, bet)
                    last_league = league
                    time.sleep(5)
                except ConnectionError:
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)
            else:
                try:
                    sf.find_country_button(browser, league)
                    sf.find_league_button(browser, league)
                    sl.add_following_bets(browser, team1, field, bet)
                    last_league = league
                    time.sleep(5)
                except ConnectionError:
                    message = handle_play_conn_err(browser, team1, team2)
                    return bot.send_message(chat_id=update.message.chat_id,
                                            text=message)

        time.sleep(5)

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
            if len(possible_win_default.split('.')) == 2:
                possible_win_default = float(possible_win_default)
            else:
                possible_win_default = int(''.join(
                        possible_win_default.split('.')[:-1]))
            possible_win = round(possible_win_default * (euros/2), 2)

            login(browser)

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
                    break
            message = 'Bet placed correctly.\n\n'
            bet_id = dbf.get_value('bets_id', 'bets', 'result', 'Unknown')
            db, c = dbf.start_db()
            summary = list(c.execute('''SELECT user, team1, team2, field, bet
                                     FROM bets INNER JOIN matches on
                                     matches.bets_id = ?''', (bet_id,)))

            db.close()
            message += (played_bets(summary) + '\nPossible win: {}'.format(
                    possible_win))
            bot.send_message(chat_id=update.message.chat_id, text=message)
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             text=('Something went wrong, try again the' +
                                   ' command /play.'))

        browser.quit()

    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text=('Please insert the amount to bet. ' +
                               'Ex: /play 5'))


def summary(bot, update):
    bet_id = dbf.get_value('bets_id', 'bets', 'result', 'Unknown')
    db, c = dbf.start_db()
    summary = list(c.execute('''SELECT user, team1, team2, field, bet
                             FROM bets INNER JOIN matches on
                             matches.bets_id = ?''', (bet_id,)))

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
summary_handler = CommandHandler('summary', summary)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(commands_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(play_bet_handler)
dispatcher.add_handler(summary_handler)
updater.start_polling()
updater.idle()
