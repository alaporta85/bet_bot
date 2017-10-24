from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle


def wait(browser, seconds, element):

        '''Forces the script to wait before doing any other action.'''

        WebDriverWait(
                browser, seconds).until(EC.element_to_be_clickable(
                        (By.XPATH, element)))


def scroll_to_element(browser, true_false, element):

        '''If the argument of 'scrollIntoView' is 'true' the command scrolls
           the webpage positioning the element at the top of the window, if it
           is 'false' the element will be positioned at the bottom.'''

        browser.execute_script('return arguments[0].scrollIntoView({});'
                               .format(true_false), element)


def get_quote(browser, field, right_bet, click='no'):

    '''When 'click=no' return the quote, when 'click=yes' click the bet.'''

    CLICK_CHECK = 0

    # This is the xpath of the box containing all the bets' panels grouped
    # by type (PIU' GIOCATE, CHANCE MIX, TRICOMBO, ...)
    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')

    # Wait for the panels to be visible
    WebDriverWait(browser, 60).until(EC.visibility_of_element_located(
                        (By.XPATH, all_panels_path)))

    all_panels = browser.find_elements_by_xpath(all_panels_path)

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

                        wait(browser, 60, bet_element_path)

                        bet_element = new_bet.find_element_by_xpath(
                                bet_element_path)

                        if click == 'yes':
                            CLICK_CHECK = 1
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


def simulate_hover_and_click(browser, element):

        '''Handles the cases when hover is needed before clicking.'''

        webdriver.ActionChains(
                browser).move_to_element(element).click(element).perform()


def look_for_quote(text):

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
            if ',' not in value:
                value = bet.split(' ')[1].replace('.', ',')
            if value != '2,5':
                BET_CHECK = 0
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

                match_text = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a/strong').text

                team1 = match_text.split(' - ')[0]
                team2 = match_text.split(' - ')[1]

                if team == team1 or team == team2:

                    match_box = match.find_element_by_xpath(
                            './/td[contains(@colspan,"1")]/a')

                    scroll_to_element(browser, 'false', match_box)

                    simulate_hover_and_click(browser, match_box)

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
            return 'Wrong: {}'.format(bet)
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
            return 'Wrong: {}'.format(bet)

    # Navigate to page containing the matches of our league
    go_to_league_bets(team)
    if not TEAM_CHECK:
        browser.quit()
        return 'Wrong: {}'.format(team)

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
    return league, team1, team2, right_bet, bet_quote, field, current_url


def add_quote(current_url, field, right_bet):

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    browser.get(current_url)
    get_quote(browser, field, right_bet, 'yes')
    browser.quit()


#league, team1, team2, right_bet, bet_quote, field, current_url = (
#        look_for_quote('inter_x'))
#add_quote(current_url, field, right_bet)
