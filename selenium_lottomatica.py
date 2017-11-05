import time
from selenium.common.exceptions import NoSuchElementException
from Functions import selenium_functions as sf


def add_first_bet(browser, current_url, field, right_bet):

    '''Add the quote to the basket by taking directly the url of the bet.
       This is used inside the play_bet function to play the first match.'''

    browser.get(current_url)
    time.sleep(3)

    LIMIT_GET_QUOTE = 0

    try:
        sf.get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def add_following_bets(browser, team, field, right_bet):

    '''Add all the other quotes after the first one. It does NOT use the url
       but look for each button instead.'''

    LIMIT_MATCH_BUTTON = 0
    LIMIT_GET_QUOTE = 0

    try:
        sf.click_match_button(browser, team, LIMIT_MATCH_BUTTON)

        sf.get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, 'yes')

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
