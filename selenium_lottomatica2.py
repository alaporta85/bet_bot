from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlite3
import pickle


def insert_quote(user, quote):

    '''Update user,s data with the new quote.'''

    db = sqlite3.connect('bet_bot_db')
    cursor = db.cursor()

    cursor.execute('''INSERT INTO quotes2017 (user, quote)
    VALUES (?, ?)''', (user, quote))

    db.commit()
    db.close()


def insert_temp(user, bet):

    '''Insert the bet in the temporary folder.'''

    db = sqlite3.connect('bet_bot_db')
    cursor = db.cursor()

    cursor.execute('''INSERT INTO temporary (user, bet)
    VALUES (?, ?)''', (user, bet))

    db.commit()
    db.close()


def delete_temp(user):

    '''Delete the bet from the temporary folder.'''

    db = sqlite3.connect('bet_bot_db')
    cursor = db.cursor()

    cursor.execute('''DELETE FROM temporary WHERE user = ?''', (user,))

    db.commit()
    db.close()


def wait(browser, seconds, element):

        '''Forces the script to wait before doing any other action.'''

        WebDriverWait(
                browser, seconds).until(EC.element_to_be_clickable(
                        (By.XPATH, element)))


def scroll_to_element(browser, true_false, element):

        '''If the argument of 'scrollIntoView' is 'true' the command scrolls
           the webpage positioning the element at the top of the window, if it
           is 'false' the element will be positioned at the bottom.'''

        browser.execute_script('return arguments[0].scrollIntoView(%s);'
                               % true_false, element)


def get_quote(browser, field, right_bet, click='no'):

    '''Returns the HTML element representing the chosen bet and its
       quote.'''

    # This is the xpath of the box containing all the bets' panels grouped
    # by type (PIU' GIOCATE, CHANCE MIX, TRICOMBO, ...)
    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')

    all_panels = browser.find_elements_by_xpath(all_panels_path)

    # In each panel look for the chosen field
    for panel in all_panels:
        panel.click()

        # These are the fields of the panel (ESITO FINALE 1X2, DOPPIA
        # CHANCE, GOAL/NOGOAL, ...)
        all_fields_path = '//div[@class="panel-collapse collapse in"]/div'

        all_fields = browser.find_elements_by_xpath(all_fields_path)

        for new_field in all_fields:
            field_name = new_field.find_element_by_xpath(
                    './/div[@class="text-left col ng-binding"]').text

            # If field is found look for the chosen bet
            if field_name == field:

                # These are all the bets of the field
                all_bets_path = ('.//div[@class="block-selections-' +
                                 'single-event"]/div')

                all_bets = new_field.find_elements_by_xpath(
                        all_bets_path)

                # For each bet of the field we look for the right one
                for new_bet in all_bets:
                    bet_name = new_bet.find_element_by_xpath(
                            './/div[@class="sel-ls"]').text

                    # When it is found, the HTML element and the bet quote
                    # are returned
                    if bet_name == right_bet:

                        bet_element_path = ('.//a[@class="bet-value-' +
                                            'quote ng-binding ng-scope"]')

                        bet_element = new_bet.find_element_by_xpath(
                                bet_element_path)

                        if click == 'yes':
                            wait(browser, 60, bet_element)
                            scroll_to_element(browser, 'true', bet_element)
                            scroll_to_element(browser, 'false', bet_element)
                            bet_element.click()
                        else:
                            bet_quote = float(bet_element.text)

                            return bet_quote


def look_for_quote(text):

    def simulate_hover_and_click(element):

        '''Handles the cases when hover is needed before clicking.'''

        webdriver.ActionChains(
                browser).move_to_element(element).click(element).perform()

    def get_field(bet):

        '''It takes the input from the user and return the corresponding field
           found on the webpage. Example:

               - The input is 'ng + over2.5'. This bet will NOT be recognized
               by the webpage as belonging to any field.

               - This function take the input and return the one which will be
               recognized by the webpage, in our case 'GOAL/NOGOAL + U/O 2,5'.
        '''

        nonlocal BET_CHECK

        if ('+' in bet and ('UNDER' in bet or 'OVER' in bet) and
           ('NG' in bet or 'GG' in bet)):
            value = bet.split(' ')[3].replace('.', ',')
            return 'GOAL/NOGOAL + U/O %s' % value
        elif '+' in bet and ('UNDER' in bet or 'OVER' in bet):
            value = bet.split(' ')[3].replace('.', ',')
            return 'ESITO FINALE 1X2 + U/O %s' % value
        elif '+' in bet and ('NG' in bet or 'GG' in bet):
            return 'ESITO FINALE 1X2 + GOAL/NOGOAL'
        elif 'PT' in bet and bet.split(' ')[0] in '1X2':
            return 'ESITO 1 TEMPO 1X2'
        elif bet in '1X2':
            return 'ESITO FINALE 1X2'
        elif 'H' in bet:
            return 'ESITO FINALE 1X2 HANDICAP'
        elif 'NG' in bet or 'GG' in bet:
            return 'GOAL/NO GOAL'
        elif ('UNDER' in bet or 'OVER' in bet) and 'PT' in bet:
            value = bet.split(' ')[1].replace('.', ',')
            return 'UNDER/OVER %s PRIMO TEMPO' % value
        elif ('UNDER' in bet or 'OVER' in bet) and 'ST' in bet:
            value = bet.split(' ')[1].replace('.', ',')
            return 'UNDER/OVER %s SECONDO TEMPO' % value
        elif 'UNDER' in bet or 'OVER' in bet:
            value = bet.split(' ')[1].replace('.', ',')
            return 'UNDER / OVER %s' % value
        else:
            BET_CHECK = 0

    def format_bet(field, bet):

        '''It takes the field and the user bet and return the corresponding
           bet found on the webpage.'''

        if 'GOAL/NOGOAL + U/O' in field:
            if 'NG' in bet and 'UNDER' in bet:
                return 'NOGOAL + UNDER'
            elif 'NG' in bet and 'OVER' in bet:
                return 'NOGOAL + OVER'
            elif 'GG' in bet and 'UNDER' in bet:
                return 'GOAL + UNDER'
            elif 'GG' in bet and 'OVER' in bet:
                return 'GOAL + OVER'
        elif 'ESITO FINALE 1X2 + U/O' in field:
            return ' '.join(bet.split(' ')[:3])
        elif field == 'ESITO FINALE 1X2 + GOAL/NOGOAL':
            if 'NG' in bet:
                return bet.split(' ')[0] + ' + NOGOAL'
            else:
                return bet.split(' ')[0] + ' + GOAL'
        elif field == 'ESITO 1 TEMPO 1X2':
            return bet.split(' ')[0]
        elif field == 'ESITO FINALE 1X2':
            return bet
        elif field == 'ESITO FINALE 1X2 HANDICAP':
            return bet.split(' ')[0]
        elif field == 'GOAL/NO GOAL':
            if 'NG' in bet:
                return 'NOGOAL'
            else:
                return 'GOAL'
        elif 'UNDER/OVER' in field:
            return bet.split(' ')[0]

    def right_team(team_input, team_lottom):

        '''Compare the input and the team name in the webpage. If input is
           recognized, Return team name as in the webpage.'''

        if team_input == team_lottom:
            return True
        elif team_input in team_lottom:
            return True
        else:
            return False

    def go_to_league_bets(a_team):

        '''Drives the browser at the webpage containing all the matches
           relative to the chosen league.'''

        nonlocal TEAM_CHECK
        nonlocal team
        nonlocal league

        countries = {'SERIE A': 'ITALIA',
                     'SERIE B': 'ITALIA',
                     'PREMIER LEAGUE': 'INGHILTERRA',
                     'PRIMERA DIVISION': 'SPAGNA',
                     'BUNDESLIGA': 'GERMANIA',
                     'LIGUE 1': 'FRANCIA',
                     'EUROPA LEAGUE': 'EUROPA',
                     'EREDIVISIE': 'OLANDA'}

        f = open('main_leagues_teams_lotto.pckl', 'rb')
        all_teams = pickle.load(f)
        f.close()

        for new_league in all_teams:
            for new_team in all_teams[new_league]:
                if right_team(a_team, new_team):
                    team = new_team
                    if not league:
                        league = new_league
                    TEAM_CHECK = 1
                    break
            if TEAM_CHECK:
                break

        if TEAM_CHECK:
            # Find the country button and click it
            countries_container = '//*[@id="better-table-tennis"]'
            all_countries = browser.find_elements_by_xpath(
                    countries_container + '/li')
            for country in all_countries:
                panel = country.find_element_by_xpath('.//a')
                if panel.text == countries[league]:
                    scroll_to_element(browser, 'false', panel)
                    panel.click()
                    break

            # Find the national league button and click it
            nat_leagues_container = '//*[@id="better-table-tennis-ww"]'
            all_nat_leagues = browser.find_elements_by_xpath(
                    nat_leagues_container + '/li')
            for nat_league in all_nat_leagues:
                panel = nat_league.find_element_by_xpath('.//a')
                if panel.text == league:
                    scroll_to_element(browser, 'false', panel)
                    panel.click()
                    break

        else:
            pass

    def go_to_match_bets(all_tables, team):

        '''Drives the browser to the webpage containing all the bets relative
           to the match which the input team is playing.'''

        done = False

        for table in all_tables:
            all_matches = table.find_elements_by_xpath(
                    './/tbody/tr[contains(@class,"ng-scope")]')
            for match in all_matches:

                # For each match extract the 2 teams
                match_text = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a/strong').text

                team1 = match_text.split(' - ')[0]
                team2 = match_text.split(' - ')[1]

                # If it is the right match than click
                if team == team1 or team == team2:
                    match_box = match.find_element_by_xpath(
                            './/td[contains(@colspan,"1")]/a')

                    scroll_to_element(browser, 'false', match_box)

                    simulate_hover_and_click(match_box)

                    done = True
                    break
            if done:
                break

        return team1, team2

    # Conditions to check whether the input from the user are correct
    TEAM_CHECK = 0
    BET_CHECK = 1

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    browser.get(url)

    oggi_domani = ('.//div[@id="navigationContainer"]//' +
                   'a[contains(@class,"col-lg-6 col-md-6")]')
    wait(browser, 60, oggi_domani)
    oggi_domani_button = browser.find_element_by_xpath(oggi_domani)
    # This double-scroll is to make the cookies advice disappear
    scroll_to_element(browser, 'true', oggi_domani_button)
    scroll_to_element(browser, 'false', oggi_domani_button)
    oggi_domani_button.click()

    # Xpath of the button to select country and national league
    calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
    wait(browser, 60, calcio)
    calcio_button = browser.find_element_by_xpath(calcio)
    calcio_button.click()

    # In case the input bet has the form team_bet we use the function get_field
    # to find the right field and then format the bet. In this case the inputs
    # do NOT need to be correct. Most of the cases are handled by the code to
    # return the correct element
    if len(text.split('_')) == 2:
        league = 0
        team, bet = text.split('_')
        team, bet = team.upper(), bet.upper()
        field = get_field(bet)
        if not BET_CHECK:
            browser.quit()
            return 'Wrong: %s' % bet
        right_bet = format_bet(field, bet)

    # On the other hand, if the input has the form league_team_field_bet we
    # directly use all of them to format the bet. In this case ALL the inputs
    # need to be EXACTLY as in the webpage
    else:
        league, team, field, bet = text.split('_')
        league, team, field, bet = (league.upper(), team.upper(),
                                    field.upper(), bet.upper())
        right_bet = format_bet(field, bet)
        if not BET_CHECK:
            browser.quit()
            return 'Wrong: %s' % bet

    # Navigate to page containing the matches of our league
    go_to_league_bets(team)
    if not TEAM_CHECK:
        browser.quit()
        return 'Wrong: %s' % team

    # Xpath of the box containing the matches grouped by day
    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
    wait(browser, 60, all_days)
    all_tables = browser.find_elements_by_xpath(all_days)

    # Navigate to the webpage containing all the bets of the match and store
    # the two teams
    team1, team2 = go_to_match_bets(all_tables, team)
    browser.implicitly_wait(5)

    # Store the quote
    bet_quote = get_quote(browser, field, right_bet)
    current_url = browser.current_url
    browser.quit()
    return team1, team2, right_bet, bet_quote, field, current_url


def add_quote(current_url, field, right_bet):

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    browser.get(current_url)
#    browser.implicitly_wait(20)
    get_quote(browser, field, right_bet, 'yes')
#    browser.quit()


team1, team2, right_bet, bet_quote, field, current_url= look_for_quote('chelsea_2')
add_quote(current_url, field, right_bet)
