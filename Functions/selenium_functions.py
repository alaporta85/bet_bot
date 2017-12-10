import os
import time
import datetime
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from Functions import logging as log
from Functions import db_functions as dbf
#import db_functions as dbf


countries = {
             'SERIE A': 'ITALIA',
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

absolute_path = os.getcwd()
#chrome_path = absolute_path[:-9] + '/chromedriver'
chrome_path = absolute_path + '/chromedriver'
logger = log.get_flogger()

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


def click_calcio_button(browser):

    calcio = './/ul[contains(@class,"sports-nav")]/li[1]/a'
    wait_clickable(browser, 20, calcio)
    calcio_button = browser.find_element_by_xpath(calcio)

    scroll_to_element(browser, 'true', calcio_button)
    scroll_to_element(browser, 'false', calcio_button)

    calcio_button.click()


def go_to_lottomatica(LIMIT_1):

    '''Connect to Lottomatica webpage and click "CALCIO" button.'''

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

        if LIMIT_1 < 3:
            print('recursive go_to_lottomatica')
            browser.quit()
            go_to_lottomatica(LIMIT_1 + 1)
        else:
            raise ConnectionError('Unable to reach Lottomatica webpage. ' +
                                  'Please try again.')


def click_country_button(browser, league, LIMIT_COUNTRY_BUTTON):

    '''Find the button relative to the country we are interested in and click
       it.'''

    current_url = browser.current_url

    countries_container = './/ul[@id="better-table-tennis"]'
    try:
        wait_clickable(browser, 20, countries_container)
        all_countries = browser.find_elements_by_xpath(
                countries_container + '/li')

    except TimeoutException:
        if LIMIT_COUNTRY_BUTTON < 3:
            print('recursive country button')
            browser.get(current_url)
            time.sleep(3)
            click_calcio_button(browser)
            click_country_button(browser, league, LIMIT_COUNTRY_BUTTON + 1)
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


def click_league_button(browser, league):

    '''Find the button relative to the league we are interested in and click
       it.'''

    nat_leagues_container = './/ul[@id="better-table-tennis-ww"]'
    all_nat_leagues = browser.find_elements_by_xpath(
            nat_leagues_container + '/li')
    for nat_league in all_nat_leagues:
        panel = nat_league.find_element_by_xpath('.//a')
        if panel.text == league:
            scroll_to_element(browser, 'false', panel)
            panel.click()
            break


def find_all_panels(browser, LIMIT_ALL_PANELS):

    '''Return the HTML container of the panels (PIU' GIOCATE, CHANCE MIX,
       TRICOMBO, ...).'''

    all_panels_path = ('//div[@new-component=""]//div[@class="row"]/div')
    current_url = browser.current_url

    try:
        wait_visible(browser, 20, all_panels_path)
        all_panels = browser.find_elements_by_xpath(all_panels_path)
    except TimeoutException:
        if LIMIT_ALL_PANELS < 3:
            print('recursive all_panels button')
            browser.get(current_url)
            time.sleep(3)
            return find_all_panels(browser, LIMIT_ALL_PANELS + 1)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)

    return all_panels


def find_all_fields(browser):

    '''Return the HTML container of the fields (ESITO FINALE 1X2, DOPPIA
       CHANCE, GOAL/NOGOAL, ...).'''

    all_fields_path = '//div[@class="panel-collapse collapse in"]/div'

    all_fields = browser.find_elements_by_xpath(all_fields_path)

    return all_fields


def find_all_bets(browser, field, new_field):

    '''Return the HTML container of the bets of a specific field. For example,
       if field is GOAL/NOGOAL the element will contain two bets: GOAL and
       NOGOAL.'''

    if field == 'ESITO FINALE 1X2 HANDICAP':
        all_bets_path = ('.//div[@class="block-selections-single-event ' +
                         'handicap-markets-single"]/div')
    else:
        all_bets_path = ('.//div[@class="block-selections-single-event"]/div')

    all_bets = new_field.find_elements_by_xpath(all_bets_path)

    return all_bets


def click_bet(browser, field, bet, LIMIT_GET_QUOTE):

    '''Find the button relative to the bet we are interested in and click
       it.'''

    current_url = browser.current_url
    CLICK_CHECK = False

    try:
        all_panels = find_all_panels(browser, 0)

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

                        if bet_name == bet:

                            bet_element_path = ('.//a[@ng-click="remCrt.' +
                                                'selectionClick(selection)"]')

                            wait_clickable(browser, 20, bet_element_path)
                            bet_element = new_bet.find_element_by_xpath(
                                    bet_element_path)

                            CLICK_CHECK = True
                            scroll_to_element(browser, 'true', bet_element)
                            scroll_to_element(browser, 'false',
                                              bet_element)
                            simulate_hover_and_click(browser, bet_element)
                            break

                    if CLICK_CHECK:
                        break

            if CLICK_CHECK:
                break

    except TimeoutException:

        if LIMIT_GET_QUOTE < 3:
            print('recursive get quote')
            browser.get(current_url)
            time.sleep(3)
            click_bet(browser, field, bet, LIMIT_GET_QUOTE + 1)
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
    logger.info('PLAY - Login in progress... ')

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

    '''Take the input from the user and look into the db for the requested
       quote. Return five variables which will be used later to update the
       "predictions" table in the db.'''

    input_team = text.split('_')[0]
    input_bet = text.split('_')[1]

    db, c = dbf.start_db()

    try:
        field_id = list(c.execute('''SELECT field_alias_field FROM fields_alias
                                  WHERE field_alias_name = ? ''',
                                  (input_bet,)))[0][0]
        nice_bet = list(c.execute('''SELECT field_nice_value FROM fields
                                  WHERE field_id = ? ''', (field_id,)))[0][0]
    except IndexError:
        raise SyntaxError('Bet not valid.')

    try:
        team_id = list(c.execute('''SELECT team_alias_team FROM teams_alias
                                 WHERE team_alias_name = ? ''',
                                 (input_team,)))[0][0]
    except IndexError:
        raise SyntaxError('Team not valid.')

    team_name = list(c.execute('''SELECT team_name FROM teams INNER JOIN
                               teams_alias on team_alias_team = team_id WHERE
                               team_id = ? ''', (team_id,)))[0][0]

    if '*' in input_team:
        league_id = 8
    else:
        league_id = list(c.execute('''SELECT team_league FROM teams
                                   WHERE team_name = ? AND team_league != 8''',
                                   (team_name,)))[0][0]

    team1, team2 = list(c.execute('''SELECT match_team1, match_team2 FROM
                                  matches WHERE match_team1 = ? OR
                                  match_team2 = ?''', (team_name,
                                  team_name)))[0]

    match_id = list(c.execute('''SELECT match_id FROM matches
                              WHERE match_team1 = ? AND match_team2 = ?''',
                              (team1, team2)))[0][0]

    quote = list(c.execute('''SELECT quote_value FROM quotes
                           WHERE quote_match = ? AND quote_field = ?''',
                           (match_id, field_id)))[0][0]

    db.close()

    return team1, team2, field_id, league_id, nice_bet, quote


def add_bet(browser, current_url, field, bet):

    '''Add the quote to the basket by taking directly the url of the bet.
       It is used inside the play_bet function.'''

    browser.get(current_url)
    time.sleep(3)

    try:
        click_bet(browser, field, bet, 0)
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
    new_date = str(today_date + datetime.timedelta(days=days_shift))
    new_date = int(new_date.replace('-', ''))

    return new_date


def update_matches_table(browser, c, table_count, match_count, league_id):

    '''Extract all the data relative to a match and insert a new row in the
       'matches' table.'''

    current_url = browser.current_url
    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')

    try:
        wait_visible(browser, 20, all_days)
    except TimeoutException:
        print('recursive update_matches')
        browser.get(current_url)
        league = list(c.execute('''SELECT league_name FROM leagues where
                                league_id = ? ''', (league_id,)))[0][0]
        click_league_button(browser, league)
        return update_matches_table(browser, c, table_count, match_count,
                                    league_id)

    all_tables = browser.find_elements_by_xpath(all_days)

    for table in all_tables:
        if all_tables.index(table) == table_count:

            all_matches = table.find_elements_by_xpath(
                    './/tbody/tr[contains(@class,"ng-scope")]')

            # To check whether there is any match left in the current table.
            # If not, an IndexError will be returned and it will switch to the
            # following table
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

            # Handle the case when match is scheduled at beginning of January
            # and command is executed at the end of December
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

                if league_id == 8:
                    team1 = '*' + team1
                    team2 = '*' + team2

                match_box_path = './/td[contains(@colspan,"1")]/a'
                wait_clickable(browser, 20, match_box_path)
                match_box = match.find_element_by_xpath(match_box_path)

                scroll_to_element(browser, 'false', match_box)

                simulate_hover_and_click(browser, match_box)
                match_header_path = (
                        './/div[@class="col-sm-12 col-md-12 col-lg-12"]')
                wait_visible(browser, 20, match_header_path)
                match_url = browser.current_url
                c.execute('''INSERT INTO matches (match_league, match_team1,
                                                  match_team2, match_date,
                                                  match_time, match_url)
                VALUES (?, ?, ?, ?, ?, ?)''', (league_id, team1, team2,
                                               match_date, match_time,
                                               match_url))

                last_id = c.lastrowid
                break

    return last_id, match_count, table_count


def update_quotes_table(browser, db, c, field_elements, all_fields, last_id):

    '''Extract all the quotes relative to a match and insert a new row in the
       'quotes' table.'''

    for new_field in field_elements:
        field_name = new_field.find_element_by_xpath(
                './/div[@class="text-left col ng-binding"]').text

        if field_name in all_fields:
            all_bets = find_all_bets(browser, field_name, new_field)

            for new_bet in all_bets:
                # Handle the case when the field space in the website has empty
                # elements
                try:
                    bet_name = new_bet.find_element_by_xpath(
                            './/div[@class="sel-ls"]/a').text
                except NoSuchElementException:
                    continue

                field_id = list(c.execute('''SELECT field_id from fields WHERE
                                          field_name = ? AND field_value = ?
                                          ''', (field_name, bet_name)))[0][0]

                # Handle the case when the bet is locked in the website
                try:
                    bet_element_path = ('.//a[@ng-click="remCrt.' +
                                        'selectionClick(selection)"]')

                    wait_clickable(browser, 20, bet_element_path)
                    bet_element = new_bet.find_element_by_xpath(
                            bet_element_path)

                    bet_quote = float(bet_element.text)

                    c.execute('''INSERT INTO quotes (quote_match, quote_field,
                                                     quote_value)
                    VALUES (?, ?, ?)''', (last_id, field_id, bet_quote))
                    db.commit()

                except NoSuchElementException:
                    c.execute('''INSERT INTO quotes (quote_match, quote_field,
                                                     quote_value)
                    VALUES (?, ?, ?)''', (last_id, field_id, 'LOCKED'))
                    db.commit()


def scan_league(browser, db, c, league, league_id, table_count, match_count,
                all_fields):

    '''Update the tables 'matches' and 'quotes' of the db.'''

    click_country_button(browser, league, 0)
    click_league_button(browser, league)
    time.sleep(2)

    last_id, match_count, table_count = update_matches_table(browser, c,
                                                             table_count,
                                                             match_count,
                                                             league_id)

    all_panels = find_all_panels(browser, 0)

    for panel in all_panels:

        panel.click()
        field_elements = find_all_fields(browser)
        update_quotes_table(browser, db, c, field_elements, all_fields,
                            last_id)

    click_country_button(browser, league, 0)

    return scan_league(browser, db, c, league, league_id, table_count,
                       match_count + 1, all_fields)


def fill_db_with_quotes():

    '''Call the function 'scan_league()' for all the leagues present in the
       dict "countries" to fully update the db.'''

    browser = go_to_lottomatica(0)
    dbf.empty_table('quotes')
    dbf.empty_table('matches')
    db, c = dbf.start_db()

    all_leagues = [league for league in countries]

    all_fields = list(c.execute('''SELECT field_name FROM fields'''))
    all_fields = [element[0] for element in all_fields]

    for league in all_leagues:
        start = time.time()

        if all_leagues.index(league) > 0:
            last_league = all_leagues[all_leagues.index(league) - 1]
            click_country_button(browser, last_league, 0)

        table_count = 0
        match_count = 0
        league_id = c.execute('''SELECT league_id FROM leagues WHERE
                              league_name = ? ''', (league,))
        league_id = c.fetchone()[0]
        try:
            scan_league(browser, db, c, league, league_id, table_count,
                        match_count, all_fields)
        except UnboundLocalError:
            end = time.time() - start
            minutes = int(end//60)
            seconds = round(end % 60)
            logger.info('Updating '+ league +' took '
                        + minutes +':'+ seconds+'!')
            # print('Updating {} took {}:{} minutes.'.format(league,
            #       minutes, seconds))
            continue
    db.close()
    browser.quit()


def alias():
    db, c = dbf.start_db()
    all_teams = list(c.execute('''SELECT team_name FROM teams'''))
    all_teams = [element[0] for element in all_teams if '*' not in element[0]]

    message = ''
    for team in all_teams:
        team_id = list(c.execute('''SELECT team_id FROM teams WHERE
                                 team_name = ?''', (team,)))[0][0]

        alias_list = list(c.execute('''SELECT team_alias_name FROM teams_alias
                                    WHERE team_alias_team = ?''',
                                    (team_id,)))
        alias_list = ['<' + element[0] + '>' for element in alias_list]
        alias_string = (' ').join(alias_list)

        message += team + ': ' + '{}'.format(alias_string) + '\n'

    db.close()

    return message


def all_bets_per_team(db, c, team_name, league_id):

    '''Return two text messages: one showing all the standard bets and the
       other one the combo. Both of them are relative to the match of the
       league whose id is "league_id" and team "team_name" is playing.'''

    match_id, team1, team2 = list(c.execute('''SELECT match_id, match_team1,
                                            match_team2 FROM matches WHERE
                                            match_league = ? AND
                                            (match_team1 = ? OR
                                            match_team2 = ?)''', (league_id,
                                            team_name, team_name,)))[0]
    team1 = team1.replace('*', '')
    team2 = team2.replace('*', '')

    message_standard = '<b>{} - {}: STANDARD</b>\n'.format(team1, team2)
    message_combo = '<b>{} - {}: COMBO</b>\n'.format(team1, team2)
    fields = list(c.execute('''SELECT field_id, field_value
                            FROM fields'''))

    fields_added = []
    for field in fields:
        field_id = field[0]
        field_value = field[1]
        field_name = list(c.execute('''SELECT field_name FROM fields WHERE
                                   field_id = ?''', (field_id,)))[0][0]
        if field_name not in fields_added:
            fields_added.append(field_name)
            if '+' not in field_name:
                COMBO = False
                message_standard += '\n\n<i>{}</i>'.format(field_name)
            else:
                COMBO = True
                message_combo += '\n\n<i>{}</i>'.format(field_name)
        try:
            quote = list(c.execute('''SELECT quote_value FROM quotes WHERE
                                   quote_match = ? AND quote_field = ?''',
                                   (match_id, field_id)))[0][0]
        except IndexError:
            if not COMBO:
                message_standard += '\n<b>{}</b>: NOT FOUND'.format(
                                                                   field_value)
            else:
                message_combo += '\n<b>{}</b>: NOT FOUND'.format(field_value)
            continue

        if not COMBO:
            message_standard += '\n<b>{}</b>:    @{}'.format(field_value,
                                                             quote)
        else:
            message_combo += '\n<b>{}</b>:    @{}'.format(field_value, quote)

    return message_standard, message_combo
