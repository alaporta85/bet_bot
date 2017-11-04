import time
import pickle
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver


conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')


def wait_clickable(browser, seconds, element):

    '''Forces the script to wait for the element to be clickable before doing
       any other action.'''

    WebDriverWait(
            browser, seconds).until(EC.element_to_be_clickable(
                    (By.XPATH, element)))


def wait_visible(browser, seconds, element):

    '''Forces the script to wait for the element to be visible before doing
       any other action.'''

    WebDriverWait(
            browser, seconds).until(EC.visibility_of_element_located(
                    (By.XPATH, element)))


def scroll_to_element(browser, true_false, element):

    '''If the argument of 'scrollIntoView' is 'true' the command scrolls
       the webpage positioning the element at the top of the window, if it
       is 'false' the element will be positioned at the bottom.'''

    browser.execute_script('return arguments[0].scrollIntoView({});'
                           .format(true_false), element)


def simulate_hover_and_click(browser, element):

    '''Handles the cases when hover is needed before clicking.'''

    try:
        webdriver.ActionChains(
                browser).move_to_element(element).click(element).perform()
    except MoveTargetOutOfBoundsException:
        raise ConnectionError(conn_err_message)


def go_to_lottomatica(LIMIT_1):

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    try:
        browser = webdriver.Firefox()
        time.sleep(3)
        browser.get(url)

        calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
        wait_clickable(browser, 20, calcio)
        calcio_button = browser.find_element_by_xpath(calcio)

        scroll_to_element(browser, 'true', calcio_button)
        scroll_to_element(browser, 'false', calcio_button)

        calcio_button.click()

        return browser

    except TimeoutException:

        LIMIT_1 += 1

        if LIMIT_1 < 3:
            print('recursive go_to_lottomatica')
            browser.quit()
            go_to_lottomatica(LIMIT_1)
        else:
            raise ConnectionError('Unable to reach Lottomatica webpage. ' +
                                  'Please try again.')


def text_short(browser, input_bet):

    # In case the input bet has the form team_bet we use the function
    # get_field to find the right field and then format the bet. In this
    # case the inputs do NOT need to be correct. Most of the cases are
    # handled by the code to return the correct element
    try:
        field = get_field(browser, input_bet)
    except SyntaxError as e:
        raise SyntaxError(str(e))
    right_bet = format_bet(field, input_bet)

    return field, right_bet


def click_oggi_domani_button(browser, scroll='no'):

    # Xpath of the button called 'OGGI E DOMANI'
    oggi_domani = ('.//div[@id="navigationContainer"]//' +
                   'a[contains(@class,"col-lg-6 col-md-6")]')
    try:
        wait_clickable(browser, 20, oggi_domani)
        oggi_domani_button = browser.find_element_by_xpath(oggi_domani)

        if scroll == 'yes':
            # This double-scroll is to make the cookies advice disappear
            scroll_to_element(browser, 'true', oggi_domani_button)
            scroll_to_element(browser, 'false', oggi_domani_button)
        oggi_domani_button.click()
    except TimeoutException:
        browser.quit()
        raise ConnectionError(conn_err_message)


def find_country_button(browser, league):

    countries = {'SERIE A': 'ITALIA',
                 'SERIE B': 'ITALIA',
                 'PREMIER LEAGUE': 'INGHILTERRA',
                 'PRIMERA DIVISION': 'SPAGNA',
                 'BUNDESLIGA': 'GERMANIA',
                 'LIGUE 1': 'FRANCIA',
                 'EUROPA LEAGUE': 'EUROPA',
                 'EREDIVISIE': 'OLANDA',
                 'CHAMPIONS LEAGUE': 'EUROPA'}

    countries_container = './/ul[@id="better-table-tennis"]'
    try:
        wait_clickable(browser, 20, countries_container)
        all_countries = browser.find_elements_by_xpath(
                countries_container + '/li')
    except TimeoutException:
        browser.quit()
        raise ConnectionError(conn_err_message)
    for country in all_countries:
        panel = country.find_element_by_xpath('.//a')
        if panel.text == countries[league]:
            scroll_to_element(browser, 'false', panel)
            panel.click()
            break


def find_league_button(browser, league):

    nat_leagues_container = './/ul[@id="better-table-tennis-ww"]'
    all_nat_leagues = browser.find_elements_by_xpath(
            nat_leagues_container + '/li')
    for nat_league in all_nat_leagues:
        panel = nat_league.find_element_by_xpath('.//a')
        if panel.text == league:
            scroll_to_element(browser, 'false', panel)
            panel.click()
            break


def get_field(browser, bet):

    '''It takes the input from the user and return the corresponding field
       found on the webpage. Example:

           - The input is 'ng + over2.5'. This bet will NOT be recognized
           by the webpage as belonging to any field.

           - This function take the input and return the one which will be
           recognized by the webpage, in our case 'GOAL/NOGOAL + U/O 2,5'.'''

    if ('+' in bet and ('UNDER' in bet or 'OVER' in bet) and
       ('NG' in bet or 'GG' in bet)):
        value = bet.split(' ')[3].replace('.', ',')
        if ',' not in value:
            value = bet.split(' ')[1].replace('.', ',')
        if value != '2,5':
            browser.quit()
            raise SyntaxError(bet + ': Bet not valid.')
        else:
            return 'GOAL/NOGOAL + U/O 2,5'

    elif ('+' in bet and ('UNDER' in bet or 'OVER' in bet) and
          ('1X' in bet or 'X2' in bet or '12' in bet)):
        value = bet.split(' ')[3].replace(',', '.')
        return 'DOPPIA CHANCE + UNDER/OVER {}'.format(value)

    elif '+' in bet and ('UNDER' in bet or 'OVER' in bet):
        value = bet.split(' ')[3].replace('.', ',')
        if value in '1X2':
            value = bet.split(' ')[1].replace('.', ',')
        return 'ESITO FINALE 1X2 + U/O {}'.format(value)

    elif '+' in bet and ('NG' in bet or 'GG' in bet):
        return 'ESITO FINALE 1X2 + GOAL/NOGOAL'

    elif bet in '1X2':
        return 'ESITO FINALE 1X2'

    elif 'H' in bet:
        return 'ESITO FINALE 1X2 HANDICAP'

    elif 'NG' in bet or 'GG' in bet:
        return 'GOAL/NO GOAL'

    elif ('UNDER' in bet or 'OVER' in bet) and 'PT' in bet:
        value = bet.split(' ')[1].replace('.', ',')
        return 'UNDER/OVER {} PRIMO TEMPO'.format(value)

    elif ('UNDER' in bet or 'OVER' in bet) and 'ST' in bet:
        value = bet.split(' ')[1].replace('.', ',')
        return 'UNDER/OVER {} SECONDO TEMPO'.format(value)

    elif 'UNDER' in bet or 'OVER' in bet:
        value = bet.split(' ')[1].replace('.', ',')
        return 'UNDER / OVER {}'.format(value)

    elif 'PT' in bet:
        return 'ESITO 1 TEMPO 1X2'

    else:
        browser.quit()
        raise SyntaxError(bet + ': Bet not valid.')


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

    elif 'DOPPIA CHANCE + UNDER/OVER' in field:
        return ' '.join(bet.split(' ')[:3])

    elif 'ESITO FINALE 1X2 + U/O' in field:
        new_bet = ' '.join(bet.split(' ')[:3])
        if bet[0] not in '1X2':
            new_bet = bet.split(' ')[3] + ' + ' + bet.split(' ')[0]
        return new_bet

    elif field == 'ESITO FINALE 1X2 + GOAL/NOGOAL':
        if 'NG' in bet:
            return bet.split(' ')[0] + ' + NOGOAL'
        else:
            return bet.split(' ')[0] + ' + GOAL'

    elif field == 'ESITO 1 TEMPO 1X2':
        return bet[0]

    elif field == 'ESITO FINALE 1X2':
        return bet

    elif field == 'ESITO FINALE 1X2 HANDICAP':
        return bet[0]

    elif field == 'GOAL/NO GOAL':
        if 'NG' in bet:
            return 'NOGOAL'
        else:
            return 'GOAL'

    elif 'UNDER/OVER' in field and 'PRIMO TEMPO' in field:
        return bet.split(' ')[0]

    elif 'UNDER / OVER' in field:
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


def click_match_button(browser, all_tables, team):

    '''Drives the browser to the webpage containing all the bets relative
       to the match which the input team is playing.'''

    result = False

    for table in all_tables:

        all_matches = table.find_elements_by_xpath(
                './/tbody/tr[contains(@class,"ng-scope")]')

        for match in all_matches:

            match_text = match.find_element_by_xpath(
                    './/td[contains(@colspan,"1")]/a/strong').text

            team1 = match_text.split(' - ')[0]
            team2 = match_text.split(' - ')[1]

            if (team == team1 or team == team2
               or team in team1 or team in team2
               or team1 in team or team2 in team):

                match_box = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a')

                scroll_to_element(browser, 'false', match_box)

                simulate_hover_and_click(browser, match_box)
                result = True
                break
        if result:
            break

    return team1, team2


def go_to_all_bets(browser, input_team):

    '''Find all the competitions of input_team. There are 2 options:

        - Bets in different competitions are allowed for the team: return
          the closest in time.

        - Only the bet of one competition is allowed: return it.

       Example: JUVENTUS plays in CHAMPIONS LEAGUE next Tuesday and then in
       SERIE A the following Sunday.

        - If you look for the quote on Monday or Tuesday you will get the one
          relative to the CHAMPIONS LEAGUE because is closest in time.

        - Starting from Wednesday you will get the quote relative to SERIE A.
    '''

    team = ''

    # Load the dict with leagues (keys) and countries (values)
    f = open('/Users/andrea/Desktop/bet_bot/main_leagues_teams_lotto.pckl',
             'rb')
    all_teams = pickle.load(f)
    f.close()

    if '*' in input_team:
        league = 'CHAMPIONS LEAGUE'
        input_team = input_team.replace('*', '')
        for new_team in all_teams[league]:
            if right_team(input_team, new_team):
                team = new_team
                break

    else:
        for new_league in all_teams:
            if new_league != 'CHAMPIONS LEAGUE':
                for new_team in all_teams[new_league]:
                    if right_team(input_team, new_team):
                        team = new_team
                        league = new_league
                        break
                if team:
                    break

    if team:

        # Find the country button and click it
        find_country_button(browser, league)

        # Find the national league button and click it
        find_league_button(browser, league)

        # Xpath of the box containing the matches grouped by day
        all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
        try:
            wait_visible(browser, 20, all_days)
            all_tables = browser.find_elements_by_xpath(all_days)
        except TimeoutException:
            browser.quit()
            raise ConnectionError(conn_err_message)

        team1, team2 = click_match_button(browser, all_tables, team)

    else:
        browser.quit()
        raise SyntaxError('{}: Team not valid or competition '
                          .format(input_team) + 'not allowed.')

    return team1, team2, league


def get_quote(browser, field, right_bet, click='no'):

    '''When 'click=no' return the quote, when 'click=yes' click the bet.'''

    CLICK_CHECK = False

    # This is the xpath of the box containing all the bets' panels grouped
    # by type (PIU' GIOCATE, CHANCE MIX, TRICOMBO, ...)
    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')

    # Wait for the panels to be visible
    try:
        wait_visible(browser, 20, all_panels_path)
        all_panels = browser.find_elements_by_xpath(all_panels_path)
    except TimeoutException:
        browser.quit()
        raise ConnectionError(conn_err_message)

    for panel in all_panels:
        panel.click()

        # These are the fields of the panel (ESITO FINALE 1X2, DOPPIA
        # CHANCE, GOAL/NOGOAL, ...)
        all_fields_path = '//div[@class="panel-collapse collapse in"]/div'

        all_fields = browser.find_elements_by_xpath(all_fields_path)

        for new_field in all_fields:
            field_name = new_field.find_element_by_xpath(
                    './/div[@class="text-left col ng-binding"]').text

            if field_name == field:

                if field == 'ESITO FINALE 1X2 HANDICAP':
                    all_bets_path = ('.//div[@class="block-selections-' +
                                     'single-event handicap-markets-' +
                                     'single"]/div')
                else:
                    all_bets_path = ('.//div[@class="block-selections-' +
                                     'single-event"]/div')

                all_bets = new_field.find_elements_by_xpath(all_bets_path)

                for new_bet in all_bets:
                    bet_name = new_bet.find_element_by_xpath(
                            './/div[@class="sel-ls"]/a').text

                    if bet_name == right_bet:

                        bet_element_path = ('.//a[@ng-click="remCrt.' +
                                            'selectionClick(selection)"]')

                        try:
                            wait_clickable(browser, 20, bet_element_path)
                            bet_element = new_bet.find_element_by_xpath(
                                    bet_element_path)
                        except TimeoutException:
                            browser.quit()
                            raise ConnectionError(conn_err_message)

                        if click == 'yes':
                            CLICK_CHECK = True
                            scroll_to_element(browser, 'true', bet_element)
                            scroll_to_element(browser, 'false', bet_element)
                            simulate_hover_and_click(browser, bet_element)
                            break

                        else:
                            bet_quote = float(bet_element.text)
                            return bet_quote

                if CLICK_CHECK:
                    break

        if CLICK_CHECK:
            break


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
            scroll_to_element(browser, 'false', element)
            element.click()
            break
