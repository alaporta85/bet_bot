import time
import datetime
import pickle
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
#from Functions import logging as log
#from Functions import db_functions as dbf
import db_functions as dbf
import pandas as pd


countries = {'SERIE A': 'ITALIA',
             'SERIE B': 'ITALIA',
             'PREMIER LEAGUE': 'INGHILTERRA',
             'PRIMERA DIVISION': 'SPAGNA',
             'BUNDESLIGA': 'GERMANIA',
             'LIGUE 1': 'FRANCIA',
             'EREDIVISIE': 'OLANDA',
             'CHAMPIONS LEAGUE': 'EUROPA'
             }

conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')

chrome_path = '/Users/andrea/Desktop/bet_bot/chromedriver'


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
        browser = webdriver.Chrome(chrome_path)
        time.sleep(3)
        browser.set_window_size(1400, 800)
        browser.get(url)

        click_calcio_button(browser)

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


def click_calcio_button(browser):

    calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
    wait_clickable(browser, 20, calcio)
    calcio_button = browser.find_element_by_xpath(calcio)

    scroll_to_element(browser, 'true', calcio_button)
    scroll_to_element(browser, 'false', calcio_button)

    calcio_button.click()


def click_oggi_domani_button(browser, scroll='no'):

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


def find_country_button(browser, league, LIMIT_COUNTRY_BUTTON):

    current_url = browser.current_url

    countries_container = './/ul[@id="better-table-tennis"]'
    try:
        wait_clickable(browser, 20, countries_container)
        all_countries = browser.find_elements_by_xpath(
                countries_container + '/li')

    except TimeoutException:
        if LIMIT_COUNTRY_BUTTON < 2:
            print('recursive country button')
            browser.get(current_url)
            time.sleep(3)
            click_calcio_button(browser)
            find_country_button(browser, league, LIMIT_COUNTRY_BUTTON + 1)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)

    for country in all_countries:
        panel = country.find_element_by_xpath('.//a')
        if panel.text == countries[league]:
            scroll_to_element(browser, 'false', panel)
            panel.click()
            time.sleep(2)
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


def click_match_button(browser, count, LIMIT_MATCH_BUTTON):

    '''Find the match realtive to the team and select it.'''

    current_url = browser.current_url

    try:
        all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
        wait_visible(browser, 20, all_days)
        all_tables = browser.find_elements_by_xpath(all_days)

        for table in all_tables:

            all_matches = table.find_elements_by_xpath(
                    './/tbody/tr[contains(@class,"ng-scope")]')

            for match in all_matches:
                
                date_time = match.find_element_by_xpath(
                        './/td[@class="ng-binding"]').text
                date_match = date_time.split(' ')[0]
                time_match = date_time.split(' ')[1]

                match_text = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a/strong').text
                team1 = match_text.split(' - ')[0]
                team2 = match_text.split(' - ')[1]

                match_box = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a')

                scroll_to_element(browser, 'false', match_box)

                simulate_hover_and_click(browser, match_box)
                LIMIT_MATCH_BUTTON = 0
                time.sleep(5)
                browser.get(current_url)
                time.sleep(5)

    except TimeoutException:

        LIMIT_MATCH_BUTTON += 1

        if LIMIT_MATCH_BUTTON < 3:
            print('recursive match button')
            browser.get(current_url)
            time.sleep(3)
            click_match_button(browser, LIMIT_MATCH_BUTTON)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)

    return team1, team2, date_match, time_match, current_url


def go_to_all_bets(browser, input_team):

    '''Drives the browser to the webpage containing all the bets relative
       to the match which the input team is playing.'''

    team = ''
    LIMIT_COUNTRY_BUTTON = 0
    LIMIT_MATCH_BUTTON = 0

    # Load the dict with leagues (keys) and countries (values)
    f = open('main_leagues_teams_lotto.pckl',
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

        find_country_button(browser, league, LIMIT_COUNTRY_BUTTON)

        find_league_button(browser, league)

        team1, team2, date_match, time_match = click_match_button(
                browser, team, LIMIT_MATCH_BUTTON)

    else:
        browser.quit()
        raise SyntaxError('{}: Team not valid or competition '
                          .format(input_team) + 'not allowed.')

    return team1, team2, league, date_match, time_match


def find_all_panels(browser):

    # This is the xpath of the box containing all the bets' panels grouped
    # by type (PIU' GIOCATE, CHANCE MIX, TRICOMBO, ...)
    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')

    wait_visible(browser, 20, all_panels_path)
    all_panels = browser.find_elements_by_xpath(all_panels_path)

    return all_panels


def find_all_fields(browser):

    # These are the fields of the panel (ESITO FINALE 1X2, DOPPIA
    # CHANCE, GOAL/NOGOAL, ...)
    all_fields_path = '//div[@class="panel-collapse collapse in"]/div'

    all_fields = browser.find_elements_by_xpath(all_fields_path)

    return all_fields


def find_all_bets(browser, field, new_field):

    if field == 'ESITO FINALE 1X2 HANDICAP':
        all_bets_path = ('.//div[@class="block-selections-single-event ' +
                         'handicap-markets-single"]/div')
    else:
        all_bets_path = ('.//div[@class="block-selections-single-event"]/div')

    all_bets = new_field.find_elements_by_xpath(all_bets_path)

    return all_bets


def get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, click='no'):

    '''When 'click=no' return the quote, when 'click=yes' click the bet.'''

    current_url = browser.current_url
    CLICK_CHECK = False

    try:
        all_panels = find_all_panels(browser)

        for panel in all_panels:
            panel.click()
            all_fields = find_all_fields(browser)

            for new_field in all_fields:
                field_name = new_field.find_element_by_xpath(
                        './/div[@class="text-left col ng-binding"]').text

                if field_name == field:
                    all_bets = find_all_bets(browser, field, new_field)

                    for new_bet in all_bets:
                        bet_name = new_bet.find_element_by_xpath(
                                './/div[@class="sel-ls"]/a').text

                        if bet_name == right_bet:

                            bet_element_path = ('.//a[@ng-click="remCrt.' +
                                                'selectionClick(selection)"]')

                            wait_clickable(browser, 20, bet_element_path)
                            bet_element = new_bet.find_element_by_xpath(
                                    bet_element_path)

                            if click == 'yes':
                                CLICK_CHECK = True
                                scroll_to_element(browser, 'true', bet_element)
                                scroll_to_element(browser, 'false',
                                                  bet_element)
                                simulate_hover_and_click(browser, bet_element)
                                break

                            else:
                                bet_quote = float(bet_element.text)
                                return bet_quote

                    if CLICK_CHECK:
                        break

            if CLICK_CHECK:
                break

    except TimeoutException:

        LIMIT_GET_QUOTE += 1

        if LIMIT_GET_QUOTE < 3:
            print('recursive get quote')
            browser.get(current_url)
            time.sleep(3)
            get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, click='no')
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)


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


def look_for_quote(text):

    LIMIT_1 = 0
    LIMIT_GET_QUOTE = 0

    input_team = text.split('_')[0].upper()
    input_bet = text.split('_')[1].upper()

#    if len(text.split('_')) != 2:
#        raise SyntaxError('Wrong format. Input text must have the ' +
#                          'structure "team_bet".')

    try:
        browser = go_to_lottomatica(LIMIT_1)

        field, bet = text_short(browser, input_bet)

        team1, team2, league, date_match, time_match = go_to_all_bets(
                browser, input_team)

        quote = get_quote(browser, field, bet, LIMIT_GET_QUOTE)

        current_url = browser.current_url
        browser.quit()

        return (league, team1, team2, bet, quote, field, current_url,
                date_match, time_match)

    except ConnectionError as e:
        raise ConnectionError(str(e))
    except SyntaxError as e:
        raise SyntaxError(str(e))


def add_first_bet(browser, current_url, field, right_bet):

    '''Add the quote to the basket by taking directly the url of the bet.
       This is used inside the play_bet function to play the first match.'''

    browser.get(current_url)
    time.sleep(3)

    LIMIT_GET_QUOTE = 0

    try:
        get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def add_following_bets(browser, team, field, right_bet):

    '''Add all the other quotes after the first one. It does NOT use the url
       but look for each button instead.'''

    LIMIT_MATCH_BUTTON = 0
    LIMIT_GET_QUOTE = 0

    try:
        click_match_button(browser, team, LIMIT_MATCH_BUTTON)

        get_quote(browser, field, right_bet, LIMIT_GET_QUOTE, 'yes')

    except ConnectionError as e:
        raise ConnectionError(str(e))


def check_single_bet(browser, anumber, team1, team2):

    '''Check whether the bet is inserted correctly.'''

    message = ('Problems with the match {} - {}. '.format(team1, team2) +
               'Possible reason: bad internet connection. Please try again.')

    basket = ('.//ul[@class="toolbar-nav-list"]/li[contains(@class,' +
              '"ng-scope")]/a/span[contains(@class,"pill pill")]')

    try:
        current_number = int(browser.find_element_by_xpath(basket).text)

        if current_number != anumber + 1:
            browser.quit()
            raise ConnectionError(message)

    except NoSuchElementException:
        browser.quit()
        raise ConnectionError(message)


def format_day(input_day):

    '''Take the input_day in the form 'lun', 'mar', 'mer'..... and return
       the corresponding date in the format dd/mm.'''

    weekdays = {'lun': 0,
                'mar': 1,
                'mer': 2,
                'gio': 3,
                'ven': 4,
                'sab': 5,
                'dom': 6}

    if input_day not in weekdays:
        raise SyntaxError('Not a valid day. Options are: lun, mar, mer, ' +
                          'gio, ven, sab, dom.')

    today_date = datetime.date.today()
    today_weekday = datetime.date.today().weekday()

    days_shift = weekdays[input_day] - today_weekday
    if days_shift < 0:
        days_shift += 7
    new_date = today_date + datetime.timedelta(days=days_shift)
    new_day = str(new_date).split('-')[2]
    new_month = str(new_date).split('-')[1]

    return '{}/{}'.format(new_day, new_month)


def scan_league(browser, db, c, league, league_id, table_count, match_count,
                all_fields, LIMIT_MATCH_BUTTON):

    '''Insert the quotes of the singles matches into the td.'''
    
    find_country_button(browser, league, 0)
    find_league_button(browser, league)
    time.sleep(3)
    count = 1
    
    current_url = browser.current_url

    try:
        all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
        wait_visible(browser, 20, all_days)
        all_tables = browser.find_elements_by_xpath(all_days)
        
        for table in all_tables:
            if all_tables.index(table) == table_count:

                all_matches = table.find_elements_by_xpath(
                        './/tbody/tr[contains(@class,"ng-scope")]')
    
                try:
                    match = all_matches[match_count]
                except IndexError:
                    table_count += 1
                    match_count = 0
                    continue
                        
                date_time = match.find_element_by_xpath(
                        './/td[@class="ng-binding"]').text
                match_date = date_time.split(' ')[0]
                current_month = str(datetime.date.today()).split('-')[1]
                year = str(datetime.date.today()).split('-')[0]
                match_month = match_date.split('/')[1]
                if current_month == '12' and match_month == '01':
                    match_date = int(str(int(year) + 1) +
                                     match_date.split('/')[1] +
                                     match_date.split('/')[0])
                else:
                    match_date = int(year +
                                     match_date.split('/')[1] +
                                     match_date.split('/')[0])
                    
                match_time = int(date_time.split(' ')[1].replace(':', ''))
    
                match_text = match.find_element_by_xpath(
                        './/td[contains(@colspan,"1")]/a/strong').text
                
                if all_matches.index(match) == match_count:
                    team1 = match_text.split(' - ')[0]
                    team2 = match_text.split(' - ')[1]
    
                    match_box = match.find_element_by_xpath(
                            './/td[contains(@colspan,"1")]/a')
    
                    scroll_to_element(browser, 'false', match_box)
    
                    simulate_hover_and_click(browser, match_box)
                    time.sleep(5)
                    match_url = browser.current_url
                    c.execute('''INSERT INTO matches (match_league,
                                                      match_team1,
                                                      match_team2,
                                                      match_date,
                                                      match_time,
                                                      match_url)
                    VALUES (?, ?, ?, ?, ?, ?)''', (league_id, team1, team2,
                                                   match_date, match_time,
                                                   match_url))
                    
                    last_id = c.lastrowid
                    
                    all_panels = find_all_panels(browser)

                    for panel in all_panels:
                        panel.click()
                        field_elements = find_all_fields(browser)
            
                        for new_field in field_elements:
                            field_name = new_field.find_element_by_xpath(
                                    './/div[@class="text-left col ng-binding"]').text
            
                            if field_name in all_fields:
                                all_bets = find_all_bets(browser, field_name, new_field)
                                for new_bet in all_bets:
                                    try:
                                        bet_name = new_bet.find_element_by_xpath(
                                                './/div[@class="sel-ls"]/a').text
                                    except NoSuchElementException:
                                        continue
                                    
                                    field_id = list(c.execute('''SELECT field_id from fields
                                                         WHERE field_name = ? AND
                                                         field_value = ? ''',
                                                         (field_name, bet_name)))[0][0]
                        
                                    try:
                                        bet_element_path = ('.//a[@ng-click="remCrt.' +
                                                            'selectionClick(selection)"]')
                
                                        wait_clickable(browser, 20, bet_element_path)
                                        bet_element = new_bet.find_element_by_xpath(
                                                bet_element_path)
                
                                        bet_quote = float(bet_element.text)
                                        
                                        c.execute('''INSERT INTO quotes (quote_match,
                                                                          quote_field,
                                                                          quote_value)
                                        VALUES (?, ?, ?)''', (last_id, field_id, bet_quote))
                                        db.commit()
                                        count += 1
                                    except NoSuchElementException:
                                        c.execute('''INSERT INTO quotes (quote_match,
                                                                         quote_field,
                                                                         quote_value) VALUES
                                                            (?, ?, ?)''', (last_id, field_id,
                                                                           'LOCKED'))
                                        db.commit()
                    
                    find_country_button(browser, league, 0)
                    return scan_league(browser, db, c, league, league_id, table_count,
                                match_count + 1, all_fields,
                                LIMIT_MATCH_BUTTON)

    except TimeoutException:

        if LIMIT_MATCH_BUTTON < 3:
            print('recursive match button')
            browser.get(current_url)
            time.sleep(3)
            scan_league(browser, db, c, league, league_id, table_count, match_count,
                        all_fields, LIMIT_MATCH_BUTTON + 1)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)


def fill_db_with_quotes():

    '''Call the function "quotes_by_league" for all the leagues present in the
       dict "countries" to fully update the db.'''

    browser = go_to_lottomatica(0)
    dbf.empty_table('quotes')
    dbf.empty_table('matches')
    db, c = dbf.start_db()
    
    all_leagues = [league for league in countries]

    all_fields = list(c.execute('''SELECT field_name FROM fields'''))
    all_fields = [element[0] for element in all_fields]

    for league in all_leagues:

        if all_leagues.index(league) > 0:
            last_league = all_leagues[all_leagues.index(league) - 1]
            find_country_button(browser, last_league, 0)
            
        table_count = 0
        match_count = 0
        league_id = c.execute('''SELECT league_id FROM leagues WHERE
                              league_name = ? ''', (league,))
        league_id = c.fetchone()[0]
        scan_league(browser, db, c, league, league_id, table_count,
                    match_count, all_fields, 0)
    db.close()
    browser.quit()


fill_db_with_quotes()
