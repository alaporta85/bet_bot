from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
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


#def add_bet(browser, team, field, bet):
#    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
#    sl.wait(browser, 60, all_days)
#    all_tables = browser.find_elements_by_xpath(all_days)
#    sl.go_to_match_bets(browser, all_tables, team)
#    browser.implicitly_wait(5)
#    # Store the quote
#    sl.get_quote(browser, field, bet, 'yes')


def handle_play_conn_err(browser, team1, team2):

    '''Quit browser and return the error message in case of ConnectionError.
       Used inside the play_bet function.'''

    browser.quit()
    message = ('Problems with the match {} - {}. '.format(team1, team2) +
               'Possible reason: bad internet connection. Please try again.')

    return message


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Iannelli suca")


def ask_help(bot, update):

    '''Instructions to insert the correct input.'''

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

    '''Try to find all the parameters from look_for_quote function. If found,
       they will be inserted in the database's table called "matches" and the
       user will be ask either to confirm or cancel the bet. It also manages
       the cases when some error occurred.'''

    # User sending the message
    first_name = update.message.from_user.first_name

    # Today's date
    date = todays_date()

    bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
    guess = ' '.join(args).upper()

    try:
        league, team1, team2, bet, bet_quote, field, url = (
                sl.look_for_quote(guess))

        # Update table
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

    '''Delete the bet "matches" table.'''

    first_name = update.message.from_user.first_name
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
        bot.send_message(chat_id=update.message.chat_id, text='Please wait...')
        euros = int(args[0])
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
#        last_league = 0
        for match in matches_to_play:
            team1 = match[0]
            team2 = match[1]
            field = match[2]
            bet = match[3]
            url = match[4]
#            league = match[5]
            try:
                sl.add_quote(browser, url, field, bet)
            except ConnectionError:
                browser.quit()
                message = handle_play_conn_err(browser, team1, team2)
                bot.send_message(chat_id=update.message.chat_id,
                                 text=message)
                break
#            if not count:
#                try:
#                    sl.add_quote(browser, url, field, bet)
#                    last_league = league
#                    count += 1
#                except ConnectionError:
#                    message = handle_play_conn_err(browser, team1, team2)
#                    bot.send_message(chat_id=update.message.chat_id,
#                                     text=message)
#                    break
#
#            elif count and league == last_league:
#                try:
#                    sl.find_league_button(browser, league)
#                    add_bet(browser, team1, field, bet)
#                    count += 1
#                except ConnectionError:
#                    message = handle_play_conn_err(browser, team1, team2)
#                    bot.send_message(chat_id=update.message.chat_id,
#                                     text=message)
#                    break
#            else:
#                try:
#                    sl.find_country_button(browser, league)
#                    sl.find_league_button(browser, league)
#                    add_bet(browser, team1, field, bet)
#                    count += 1
#                except ConnectionError:
#                    message = handle_play_conn_err(browser, team1, team2)
#                    bot.send_message(chat_id=update.message.chat_id,
#                                     text=message)
#                    break

        browser.implicitly_wait(10)
        # Find the basket with all the bets
        try:
            n = ('.//nav[@id="toolbarForHidden"]/ul/' +
                 'li[@class="toolbar-nav-item ng-scope"]/a')
            sl.wait(browser, 20, n)

            browser.find_element_by_xpath(n).click()
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
            bot.send_message(chat_id=update.message.chat_id,
                             text='All matches added correctly')
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             text=('Something went wrong, try tagain the' +
                                   ' command /play.'))

        browser.quit()

    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text=('Please insert the amount to bet. ' +
                               'Ex: /play 5'))


start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', ask_help)
quote_handler = CommandHandler('getquote', quote, pass_args=True)
confirm_handler = CommandHandler('confirm', confirm)
cancel_handler = CommandHandler('cancel', cancel)
play_bet_handler = CommandHandler('play', play_bet, pass_args=True)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(quote_handler)
dispatcher.add_handler(confirm_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(play_bet_handler)
updater.start_polling()
