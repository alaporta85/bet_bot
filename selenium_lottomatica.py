from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from Functions import selenium_functions as sf

conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')


def look_for_quote(text):

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    print('browser started')            # For debug
    browser.get(url)
    print('start url ' + url)           # For debug

    if sf.check_connection(browser, url):

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
                field = sf.get_field(bet)
            except SyntaxError:
                browser.quit()
                raise SyntaxError(bet + ': Bet not valid.')
            right_bet = sf.format_bet(field, bet)

        # On the other hand, if the input has the form league_team_field_bet we
        # directly use all of them to format the bet. In this case ALL the
        # inputs need to be EXACTLY as in the webpage
        else:
            try:
                league, input_team, field, bet = text.split('_')
                league, input_team, field, bet = (league.upper(),
                                                  input_team.upper(),
                                                  field.upper(), bet.upper())
            except SyntaxError:
                browser.quit()
                raise SyntaxError(bet + ': Bet not valid.')
            right_bet = sf.format_bet(field, bet)

        # Navigate to page containing the matches of our league
        try:
            team, league = sf.go_to_league_bets(browser, input_team)
        except SyntaxError:
            browser.quit()
            raise SyntaxError('{}: Team not valid or competition '
                              .format(input_team) + 'not allowed.')

        # Xpath of the box containing the matches grouped by day
        all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
        try:
            sf.wait(browser, 20, all_days)
            all_tables = browser.find_elements_by_xpath(all_days)
        except TimeoutException:
            browser.quit()
            raise ConnectionError(conn_err_message)

        # Navigate to the webpage containing all the bets of the match and
        # store the two teams
        team1, team2 = sf.go_to_match_bets(browser, all_tables, team)
        browser.implicitly_wait(5)

        # Store the quote
        bet_quote = sf.get_quote(browser, field, right_bet)
        current_url = browser.current_url
        browser.quit()
        return league, team1, team2, right_bet, bet_quote, field, current_url

    else:
        browser.quit()
        raise ConnectionError('Lottomatica webpage not found. ' +
                              'Please try again.')


def add_quote(browser, current_url, field, right_bet):

    # Go to Lottomatica webpage
    print('uno')
    browser.get(current_url)
    print('due')
    if sf.check_connection(browser, current_url):
        sf.get_quote(browser, field, right_bet, 'yes')
    else:
        raise ConnectionError


#league, team1, team2, right_bet, bet_quote, field, current_url = (
#        look_for_quote('watford_over 3,5'))
#add_quote(current_url, field, right_bet)
