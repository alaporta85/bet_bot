import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from Functions import selenium_functions as sf
from selenium.webdriver.common.keys import Keys
from Functions import db_functions as dbf

conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')


def look_for_quote(text):

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    browser.get(url)

    # 'OGGI E DOMANI' button
#    sf.click_oggi_domani_button(browser, scroll='yes')

    # 'CALCIO' button
    sf.click_calcio_button(browser, 'yes')

    # In case the input bet has the form team_bet we use the function
    # get_field to find the right field and then format the bet. In this
    # case the inputs do NOT need to be correct. Most of the cases are
    # handled by the code to return the correct element
    if len(text.split('_')) == 2:
        try:
            input_team, bet = text.split('_')
            input_team, bet = input_team.upper(), bet.upper()
            field = sf.get_field(browser, bet)
        except SyntaxError as e:
            raise SyntaxError(str(e))
        right_bet = sf.format_bet(field, bet)

    # On the other hand, if the input has the form league_team_field_bet we
    # directly use all of them to format the bet. In this case ALL the
    # inputs need to be EXACTLY as in the webpage
#    else:
#        try:
#            league, input_team, field, bet = text.split('_')
#            league, input_team, field, bet = (league.upper(),
#                                              input_team.upper(),
#                                              field.upper(), bet.upper())
#        except SyntaxError:
#            browser.quit()
#            raise SyntaxError(bet + ': Bet not valid.')
#        right_bet = sf.format_bet(field, bet)

    # Navigate to page containing the matches of our league
    try:
        team1, team2, league = sf.go_to_league_bets(browser, input_team)
    except SyntaxError as e:
        raise SyntaxError(str(e))
    except ConnectionError as e:
        raise ConnectionError(str(e))

    # Store the quote
    try:
        bet_quote = sf.get_quote(browser, field, right_bet)
    except ConnectionError as e:
        raise ConnectionError(str(e))
    current_url = browser.current_url
    browser.quit()
    return league, team1, team2, right_bet, bet_quote, field, current_url


def add_first_bet(browser, current_url, field, right_bet):

    '''Add the quote to the basket by taking directly the url of the bet.
       This is used inside the play_bet function to play the first match.'''

    # Go to Lottomatica webpage
    browser.get(current_url)
    if sf.check_connection(browser, current_url):
        try:
            sf.get_quote(browser, field, right_bet, 'yes')
        except ConnectionError as e:
            raise ConnectionError(str(e))
    else:
        raise ConnectionError


def add_following_bets(browser, team, field, right_bet):

    '''Add all the other quotes after the first one. It does NOT use the url
       but look for each button instead.'''

    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
    try:
        sf.wait_clickable(browser, 20, all_days)
        all_tables = browser.find_elements_by_xpath(all_days)
    except TimeoutException:
        browser.quit()
        raise ConnectionError
    sf.go_to_match_bets(browser, all_tables, team)

    # Store the quote
    try:
        sf.get_quote(browser, field, right_bet, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


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


def played_bets(summary):

    '''Return a string with the matches chosen until that moment.'''

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


def play_bet(args):

    '''Manage the login and play the bet. Args input is the amount of euros
       to bet.'''

    if args:
        try:
            euros = int(args)
            if euros < 2:
                message = 'Minimum amount is 2 Euros.'
                return message
        except ValueError:
            message = 'Amount has to be integer.'
            return message
        print('Please wait...')

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

            message = ('Problems with the match {} - {}. '.format(team1,
                       team2) + 'Possible reason: bad internet ' +
                       'connection. Please try again.')

            if not count:
                try:
                    add_first_bet(browser, url, field, bet)
                    last_league = league
                    count += 1
                    time.sleep(5)
                except ConnectionError:
                    print(message)
                    return message

            elif count and league == last_league:
                try:
                    sf.find_league_button(browser, league)
                    add_following_bets(browser, team1, field, bet)
                    last_league = league
                    time.sleep(5)
                except ConnectionError:
                    print(message)
                    return message
            else:
                try:
                    sf.find_country_button(browser, league)
                    sf.find_league_button(browser, league)
                    add_following_bets(browser, team1, field, bet)
                    last_league = league
                    time.sleep(5)
                except ConnectionError:
                    print(message)
                    return message

        time.sleep(5)

        # Find the basket with all the bets
        try:
            basket = ('.//nav[@id="toolbarForHidden"]/ul/' +
                      'li[@class="toolbar-nav-item ng-scope"]/a')
            sf.wait_clickable(browser, 20, basket)

            browser.find_element_by_xpath(basket).click()
        except TimeoutException:
            browser.quit()
            print('Problem during placing the bet. ' +
                  'Please check your internet ' +
                  'connection and try again.')

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
                print('adios')

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
            message += (played_bets(summary) + ('\nPossible win: {} euros.'
                                                .format(possible_win)))
            print(message)
        else:
            print('Something went wrong, try tagain the command /play.')

#        browser.quit()

    else:
        print('Please insert the amount to bet. Ex: /play 5')


#league, team1, team2, right_bet, bet_quote, field, current_url = (
#        look_for_quote('juve_gg'))
#add_quote(current_url, field, right_bet)
#play_bet(10)