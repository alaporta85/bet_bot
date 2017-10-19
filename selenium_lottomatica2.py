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


def look_for_quote(text):

    def scroll_to_element(true_false, element):

        '''If the argument of 'scrollIntoView' is 'true' the command scrolls
           the webpage positioning the element at the top of the window, if it
           is 'false' the element will be positioned at the bottom.'''

        browser.execute_script('return arguments[0].scrollIntoView(%s);'
                               % true_false, element)

    def simulate_hover_and_click(element):

        '''Handles the cases when hover is needed before clicking.'''

        webdriver.ActionChains(
                browser).move_to_element(element).click(element).perform()

    def wait(seconds, element):

        '''Forces the script to wait before doing any other action.'''

        WebDriverWait(
                browser, seconds).until(EC.element_to_be_clickable(
                        (By.XPATH, element)))

    def get_field(bet):
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

    def format_bet(field, bet):
        if 'GOAL/NOGOAL + U/O' in field:
            if 'NG' and 'UNDER' in bet:
                return 'NOGOAL + UNDER'
            elif 'NG' and 'OVER' in bet:
                return 'NOGOAL + OVER'
            elif 'GG' and 'UNDER' in bet:
                return 'GOAL + UNDER'
            elif 'GG' and 'OVER' in bet:
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

    def go_to_league_bets(team):

        '''Drives the browser at the webpage containing all the matches
           relative to the chosen league.'''

        countries = {'SERIE A': 'ITALIA',
                     'SERIE B': 'ITALIA',
                     'PREMIER LEAGUE': 'INGHILTERRA',
                     'PRIMERA DIVISION': 'SPAGNA',
                     'BUNDESLIGA': 'GERMANIA',
                     'LIGUE 1': 'FRANCIA',
                     'CHAMPIONS LEAGUE': 'EUROPA',
                     'EUROPA LEAGUE': 'EUROPA',
                     'EREDIVISIE': 'OLANDA',
                     'MONDIALI': 'MONDO'}

        f = open('main_leagues_teams.pckl', 'rb')
        all_teams = pickle.load(f)
        f.close()

        leagues = [element for element in all_teams if
                   team in all_teams[element]]
        league = 0

        for element in leagues:
            # Find the country button and click it
            countries_container = '//*[@id="better-table-tennis"]'
            all_countries = browser.find_elements_by_xpath(
                    countries_container + '/li')
            for country in all_countries:
                panel = country.find_element_by_xpath('.//a')
                if panel.text == countries[element]:
                    scroll_to_element('false', panel)
                    panel.click()
                    break

            # Find the national league button and click it
            nat_leagues_container = '//*[@id="better-table-tennis-ww"]'
            all_nat_leagues = browser.find_elements_by_xpath(
                    nat_leagues_container + '/li')
            for nat_league in all_nat_leagues:
                panel = nat_league.find_element_by_xpath('.//a')
                if panel.text == element:
                    league = element
                    scroll_to_element('false', panel)
                    panel.click()
                    break
            if league:
                break

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

                    scroll_to_element('false', match_box)

                    simulate_hover_and_click(match_box)

                    done = True
                    break
            if done:
                break

        return team1, team2

    def get_quote(field, bet):

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
            all_fields = browser.find_elements_by_xpath(
                    '//div[@class="panel-collapse collapse in"]/div')

            for new_field in all_fields:
                field_name = new_field.find_element_by_xpath(
                        './/div[@class="text-left col ng-binding"]').text

                # If field is found look for the chosen bet
                if field_name == field:

                    # There are all the bets of the field
                    all_bets = new_field.find_elements_by_xpath(
                            './/div[@class="block-selections-single-event"]' +
                            '/div')

                    # For each bet of the field we look for the right one
                    for new_bet in all_bets:
                        bet_name = new_bet.find_element_by_xpath(
                                './/div[@class="sel-ls"]').text

                        # When it is found, the HTML element and the bet quote
                        # are returned
                        if bet_name == bet:

                            bet_element = new_bet.find_element_by_xpath(
                                    './/a[@class="bet-value-quote ' +
                                    'ng-binding ng-scope"]')

                            bet_quote = float(bet_element.text)

        return bet_element, bet_quote

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser and go to Lottomatica webpage
    browser = webdriver.Firefox()
    browser.get(url)

    oggi_domani = ('.//div[@id="navigationContainer"]//' +
                   'a[contains(@class,"col-lg-6 col-md-6")]')
    wait(60, oggi_domani)
    oggi_domani_button = browser.find_element_by_xpath(oggi_domani)
    # This double-scroll is to make the cookies advice disappear
    scroll_to_element('true', oggi_domani_button)
    scroll_to_element('false', oggi_domani_button)
    oggi_domani_button.click()

    # Xpath of the button to select country and national league
    calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
    wait(60, calcio)
    calcio_button = browser.find_element_by_xpath(calcio)
    calcio_button.click()

    if len(text.split('_')) == 2:
        team, bet = text.split('_')
        team, bet = team.upper(), bet.upper()
        field = get_field(bet)
        bet = format_bet(field, bet)
    else:
        team, field, bet = text.split('_')
        team, field, bet = team.upper(), field.upper(), bet.upper()
        bet = format_bet(field, bet)

    # Navigate to page containing the matches of our league
    go_to_league_bets(team)

    # Xpath of the box containing the matches grouped by day
    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
    wait(60, all_days)
    all_tables = browser.find_elements_by_xpath(all_days)

    # Navigate to the webpage containing all the bets of the match
    go_to_match_bets(all_tables, team)

    browser.implicitly_wait(5)

    # Store HTML element and quote
    bet_element, bet_quote = get_quote(field, bet)
    bet_element.click()

#    browser.quit()
#    return bet_quote


#text = 'serie a_milan_esito finale 1x2_2'.upper()
look_for_quote('milan_2')
