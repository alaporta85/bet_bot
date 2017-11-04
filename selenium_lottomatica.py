import time
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from Functions import selenium_functions as sf


def look_for_quote(text):

    LIMIT_1 = 0

    input_team = text.split('_')[0].upper()
    input_bet = text.split('_')[1].upper()

    if len(text.split('_')) != 2:
        raise SyntaxError('Wrong format. Input text must have the ' +
                          'structure "team_bet".')

    try:
        browser = sf.go_to_lottomatica(LIMIT_1)

        field, bet = sf.text_short(browser, input_bet)

        team1, team2, league = sf.go_to_all_bets(browser, input_team)

        quote = sf.get_quote(browser, field, bet)

        current_url = browser.current_url
        browser.quit()

        return league, team1, team2, bet, quote, field, current_url

    except ConnectionError as e:
        raise ConnectionError(str(e))
    except SyntaxError as e:
        raise SyntaxError(str(e))


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
#        look_for_quote('*juve_1'))
