import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from Functions import selenium_functions as sf

conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')


def look_for_quote(text):

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser, go to Lottomatica webpage and wait
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(3)

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

    # Navigate to page containing the bet of the match we have chosen
    try:
        team1, team2, league = sf.go_to_all_bets(browser, input_team)
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

    browser.get(current_url)
    time.sleep(3)

    try:
        sf.get_quote(browser, field, right_bet, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def add_following_bets(browser, team, field, right_bet):

    '''Add all the other quotes after the first one. It does NOT use the url
       but look for each button instead.'''

    # Navigate to the right page
    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
    try:
        sf.wait_clickable(browser, 20, all_days)
        all_tables = browser.find_elements_by_xpath(all_days)
    except TimeoutException:
        browser.quit()
        raise ConnectionError
    sf.click_match_button(browser, all_tables, team)

    # Store the quote
    try:
        sf.get_quote(browser, field, right_bet, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def check_single_bet(browser, anumber):

    '''Check whether the bet is inserted correctly.'''

    basket = ('.//ul[@class="toolbar-nav-list"]/li[contains(@class,' +
              '"ng-scope")]/a/span[contains(@class,"pill pill")]')

    try:
        current_number = int(browser.find_element_by_xpath(basket).text)

        if current_number == anumber + 1:
            return True
        else:
            browser.quit()
            return False
    except NoSuchElementException:
        browser.quit()
        return False


#league, team1, team2, right_bet, bet_quote, field, current_url = (
#        look_for_quote('juve_gg'))
#add_quote(current_url, field, right_bet)
#play_bet(4)