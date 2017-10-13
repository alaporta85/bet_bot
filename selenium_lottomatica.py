from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scroll_to_element(true_false, element):

    '''If the argument of 'scrollIntoView' is 'true' the command scrolls the
       webpage positioning the element at the top of the window, if it is
       'false' the element will be positioned at the bottom.'''

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


def go_to_league_bets(league):

    '''Drives the browser at the webpage containing all the matches relative
       to the chosen league.'''

    countries = {'SERIE A': 'ITALIA',
                 'SERIE B': 'ITALIA',
                 'PREMIER LEAGUE': 'INGHILTERRA',
                 'PRIMERA DIVISION': 'SPAGNA',
                 'BUNDESLIGA': 'GERMANIA',
                 'LIGUE 1': 'FRANCIA',
                 'CHAMPIONS LEAGUE': 'EUROPA',
                 'EUROPA LEAGUE': 'EUROPA'}

    # Find the country button and click it
    countries_container = '//*[@id="better-table-tennis"]'
    all_countries = browser.find_elements_by_xpath(countries_container + '/li')
    for country in all_countries:
        panel = country.find_element_by_xpath('.//a')
        if panel.text == countries[league]:
            scroll_to_element('false', panel)
            panel.click()
            break

    # Find the national league button and click it
    nat_leagues_container = '//*[@id="better-table-tennis-ww"]'
    all_nat_leagues = browser.find_elements_by_xpath(
            nat_leagues_container + '/li')
    for nat_league in all_nat_leagues:
        panel = nat_league.find_element_by_xpath('.//a')
        if panel.text == league:
            scroll_to_element('false', panel)
            panel.click()
            break


def go_to_match_bets(all_tables, team):

    '''Drives the browser to the webpage containing all the bets relative to
       the match which the input team is playing.'''

    done = False

    for table in all_tables:
        all_matches = table.find_elements_by_xpath(
                './/tbody/tr[contains(@class,"ng-scope")]')
        for match in all_matches:

            # For each match extract the 2 teams
            match_text = match.find_element_by_xpath(
                    './/td[contains(@colspan,"1")]/a/strong').text

            # If it is the right match than click
            if team in match_text:
                match_box = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a')

                scroll_to_element('false', match_box)

                simulate_hover_and_click(match_box)

                done = True
                break
        if done:
            break


def get_quote(field, bet):

    '''Returns the HTML element representing the chosen bet and its quote.'''

    # This is the xpath of the box containing all the bets' panels grouped by
    # type (PIU' GIOCATE, CHANCE MIX, TRICOMBO, ...)
    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')

    all_panels = browser.find_elements_by_xpath(all_panels_path)

    # In each panel look for the chosen field
    for panel in all_panels:
        panel.click()

        # These are the fields of the panel (ESITO FINALE 1X2, DOPPIA CHANCE,
        # GOAL/NOGOAL, ...)
        all_fields = browser.find_elements_by_xpath(
                '//div[@class="panel-collapse collapse in"]/div')

        for new_field in all_fields:
            field_name = new_field.find_element_by_xpath(
                    './/div[@class="text-left col ng-binding"]').text

            # If field is found look for the chosen bet
            if field_name == field:

                # There are all the bets of the field
                all_bets = new_field.find_elements_by_xpath(
                        './/div[@class="block-selections-single-event"]/div')

                # For each bet of the field we look for the right one
                for new_bet in all_bets:
                    bet_name = new_bet.find_element_by_xpath(
                            './/div[@class="sel-ls"]').text

                    # When it is found, the HTML element and the bet quote are
                    # returned
                    if bet_name == bet:
                        bet_element = new_bet.find_element_by_xpath(
                                './/a[@class="bet-value-quote ' +
                                'ng-binding ng-scope"]')

                        bet_quote = float(bet_element.text)

                        return bet_element, bet_quote


#text = 'SERIE A_JUVENTUS_ESITO FINALE 1X2_2'
#text = 'SERIE A_JUVENTUS_ESITO 1 TEMPO/FINALE_1-2'
#text = 'SERIE A_JUVENTUS_SEGNA GOAL SQUADRA OSPITE_SI'
#text = 'SERIE A_INTER_U/O 1,5 1 TEMPO+U/O 1,5 2TEMPO_OVER + OVER'
#text = 'LIGUE 1_LILLA_MULTI GOAL 1-4_ALTRO'
text = ('PREMIER LEAGUE_ARSENAL_MARGINE VITTORIA 10 ESITI_TEAM 1 CON 3 GOAL ' +
        'DI SCARTO')
#text = 'PRIMERA DIVISION_CELTA VIGO_ESITO FINALE 1X2_2'

url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
       'scommesse-sportive.html')

# Start the browser and go to Lottomatica webpage
browser = webdriver.Firefox()
browser.get(url)

# Xpath of the button to select country and national league
calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
wait(60, calcio)
calcio_button = browser.find_element_by_xpath(calcio)
# This double-scroll is to make the cookies advice disappear
scroll_to_element('true', calcio_button)
scroll_to_element('false', calcio_button)
calcio_button.click()

# Extract the four variable from the input text
league, team, field, bet = text.split('_')

# Navigate to page containing the matches of our league
go_to_league_bets(league)

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

browser.quit()
