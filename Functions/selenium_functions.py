import os
import time
import datetime
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from Functions import logging as log
from Functions import db_functions as dbf


countries = {
             # 'SERIE A': 'ITALIA',
             # 'PREMIER LEAGUE': 'INGHILTERRA',
             # 'PRIMERA DIVISION': 'SPAGNA',
             # 'BUNDESLIGA': 'GERMANIA',
             # 'LIGUE 1': 'FRANCIA',
             # 'EREDIVISIE': 'OLANDA',
             # 'CHAMPIONS LEAGUE': 'EUROPA',
             'MONDIALI': 'MONDO'
             }

conn_err_message = ('An error occurred. This might be due to some problems ' +
                    'with the internet connection. Please try again.')

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.binary_location = ('/Applications/Google Chrome.app/' +
                                  'Contents/MacOS/Google Chrome')

absolute_path = os.getcwd()
chrome_path = absolute_path + '/chromedriver'
logger = log.get_flogger()

WAIT = 60


def wait_clickable(browser, seconds, element):

    """
    Forces the script to wait for the element to be clickable before doing
    any other action.
    """

    WebDriverWait(
            browser, seconds).until(EC.element_to_be_clickable(
                    (By.XPATH, element)))


def wait_visible(browser, seconds, element):

    """
    Forces the script to wait for the element to be visible before doing
    any other action.
    """

    WebDriverWait(
            browser, seconds).until(EC.visibility_of_element_located(
                    (By.XPATH, element)))


def scroll_to_element(browser, true_false, element):

    """
    If the argument of 'scrollIntoView' is 'true' the command scrolls
    the webpage positioning the element at the top of the window, if it
    is 'false' the element will be positioned at the bottom.
    """

    browser.execute_script('return arguments[0].scrollIntoView({});'
                           .format(true_false), element)


def simulate_hover_and_click(browser, element):

    """Handles the cases when hover is needed before clicking."""

    try:
        webdriver.ActionChains(
                browser).move_to_element(element).click(element).perform()
    except MoveTargetOutOfBoundsException:
        raise ConnectionError(conn_err_message)


def click_calcio_button(browser):

    calcio = './/div/div[@class="item-sport ng-scope"]//a'
    wait_clickable(browser, WAIT, calcio)
    calcio_button = browser.find_element_by_xpath(calcio)

    scroll_to_element(browser, 'true', calcio_button)
    scroll_to_element(browser, 'false', calcio_button)

    calcio_button.click()


def go_to_lottomatica(LIMIT_1):

    """Connect to Lottomatica webpage and click "CALCIO" button."""

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # browser = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
    browser = webdriver.Chrome(chrome_path)
    time.sleep(3)
    browser.set_window_size(1400, 800)

    try:
        browser.get(url)
        click_calcio_button(browser)

        return browser

    except TimeoutException:

        if LIMIT_1 < 3:
            logger.info('Recursive go_to_lottomatica')
            browser.quit()
            return go_to_lottomatica(LIMIT_1 + 1)
        else:
            raise ConnectionError('Unable to reach Lottomatica webpage. ' +
                                  'Please try again.')


def click_country_button(browser, league, LIMIT_COUNTRY_BUTTON):

    """
    Find the button relative to the country we are interested in and click it.
    """

    current_url = browser.current_url

    countries_container = './/div[@class="country-name"]'
    try:
        wait_clickable(browser, WAIT, countries_container)
        all_countries = browser.find_elements_by_xpath(countries_container)

    except TimeoutException:
        if LIMIT_COUNTRY_BUTTON < 3:
            logger.info('Recursive click_country_button')
            browser.get(current_url)
            time.sleep(3)
            click_calcio_button(browser)
            return click_country_button(browser, league,
                                        LIMIT_COUNTRY_BUTTON + 1)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)

    for country in all_countries:
        panel = country.find_element_by_xpath('.//a')
        scroll_to_element(browser, 'false', panel)
        if panel.text.upper() == countries[league]:
            panel.click()
            time.sleep(2)
            break


def click_league_button(browser, league):

    """
    Find the button relative to the league we are interested in and click it.
    """

    nat_leagues_container = ('.//div[@class="item-competition competition ' +
                             'slide-menu ng-scope"]')
    all_nat_leagues = browser.find_elements_by_xpath(nat_leagues_container)
    for nat_league in all_nat_leagues:
        panel = nat_league.find_element_by_xpath('.//a')
        scroll_to_element(browser, 'false', panel)
        if panel.text.upper() == league:
            panel.click()
            break


def find_all_panels(browser, LIMIT_ALL_PANELS):

    """
    Return the HTML container of the panels (PIU' GIOCATE, CHANCE MIX,
    TRICOMBO, ...).
    """

    all_panels_path = ('//div[@class="item-group ng-scope"]/' +
                       'div[contains(@class, "group-name")]')
    current_url = browser.current_url

    try:
        wait_visible(browser, WAIT, all_panels_path)
        all_panels = browser.find_elements_by_xpath(all_panels_path)

    except TimeoutException:
        if LIMIT_ALL_PANELS < 3:
            logger.info('Recursive find_all_panels')
            browser.get(current_url)
            time.sleep(3)
            return find_all_panels(browser, LIMIT_ALL_PANELS + 1)
        else:
            browser.quit()
            raise ConnectionError(conn_err_message)

    return all_panels


def find_all_fields_and_bets(browser):

    """
    Return the HTML container of the fields (ESITO FINALE 1X2, DOPPIA
    CHANCE, GOAL/NOGOAL, ...).
    """

    all_fields_path = '//div[@class="market-info"]/div'
    all_bets_path = '//div[@class="market-selections"]'

    fields = browser.find_elements_by_xpath(all_fields_path)
    bets = browser.find_elements_by_xpath(all_bets_path)

    return fields, bets


def find_all_bets(field, new_field):

    """
    Return the HTML container of the bets of a specific field. For example,
    if field is GOAL/NOGOAL the element will contain two bets: GOAL and
    NOGOAL.
    """

    if field == 'ESITO FINALE 1X2 HANDICAP':
        all_bets_path = ('.//div[@class="block-selections-single-event ' +
                         'handicap-markets-single"]/div')
    else:
        all_bets_path = './/div[@class="block-selections-single-event"]/div'

    all_bets = new_field.find_elements_by_xpath(all_bets_path)

    return all_bets


def click_bet(browser, field, bet, LIMIT_GET_QUOTE):

    """
    Find the button relative to the bet we are interested in and click
    it.
    """

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
                    all_bets = find_all_bets(field, new_field)

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
            logger.info('Recursive click_bet')
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

    """
    Take the input from the user and look into the db for the requested
    quote. Return five variables which will be used later to update the
    "predictions" table in the db.
    """

    input_team, input_bet = text.split('_')

    db, c = dbf.start_db()

    try:
        field_id = list(c.execute('''SELECT field_alias_field FROM fields_alias
                                     WHERE field_alias_name = ? ''',
                                  (input_bet,)))[0][0]
        nice_bet = list(c.execute('''SELECT field_nice_value FROM fields
                                     WHERE field_id = ? ''',
                                  (field_id,)))[0][0]
    except IndexError:
        db.close()
        raise SyntaxError('Bet not valid.')

    try:
        team_id = list(c.execute('''SELECT team_alias_team FROM teams_alias
                                    WHERE team_alias_name = ? ''',
                                 (input_team,)))[0][0]
    except IndexError:
        db.close()
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

    try:
        team1, team2 = list(c.execute('''SELECT match_team1, match_team2 FROM
                                      matches WHERE match_team1 = ? OR
                                      match_team2 = ?''', (team_name,
                                      team_name)))[0]
    except IndexError:
        db.close()
        raise ValueError('Quotes not available')

    match_id = list(c.execute('''SELECT match_id FROM matches
                              WHERE match_team1 = ? AND match_team2 = ?''',
                              (team1, team2)))[0][0]


    try:
        quote = list(c.execute('''SELECT quote_value FROM quotes
                               WHERE quote_match = ? AND quote_field = ?''',
                               (match_id, field_id)))[0][0]
    except IndexError:
        raise ValueError('Quote not available for this match')

    db.close()

    return team1, team2, field_id, league_id, nice_bet, quote


def add_bet(browser, current_url, field, bet):

    """
    Add the quote to the basket by taking directly the url of the bet.
    It is used inside the play_bet function.
    """

    browser.get(current_url)
    time.sleep(3)

    try:
        click_bet(browser, field, bet, 0)
    except ConnectionError as e:
        raise ConnectionError(str(e))


def check_single_bet(browser, anumber, team1, team2):

    """Check whether the bet is inserted correctly."""

    message = ('Problems with the match {} - {}. '.format(team1, team2) +
               'Possible reason: bad internet connection. Please try again.')

    avv = './/div[@class="col-lg-4 col-md-4 col-sm-4 col-xs-4 text-right"]'

    try:
        current_number = int(browser.find_element_by_xpath(avv).text)

        if current_number != anumber + 1:
            browser.quit()
            raise ConnectionError(message)

    except NoSuchElementException:
        browser.quit()
        raise ConnectionError(message)


def format_day(input_day):

    """
    Take the input_day in the form 'lun', 'mar', 'mer'..... and return
    the corresponding date as an integer. If on May 16th 1985 (Thursday)
    command format_day('sab') is sent, output will be:

        19850518
    """

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


def update_matches_table(browser, c, league_id, d_m_y, h_m):

    back = './/a[@class="back-competition ng-scope"]'
    wait_clickable(browser, 30, back)
    back = browser.find_element_by_xpath(back)
    time.sleep(1)

    main = './/div[@class="event-name ng-binding"]'
    teams = browser.find_element_by_xpath(main).text.upper()

    team1, team2 = teams.split(' - ')
    if league_id == 8:
        team1 = '*' + team1
        team2 = '*' + team2

    dd, mm, yy = d_m_y.split('/')
    match_date = datetime.datetime.strptime(yy + mm + dd, '%Y%m%d')
    match_date = match_date.replace(hour=int(h_m.split(':')[0]),
                                    minute=int(h_m.split(':')[1]))
    time.sleep(4)
    c.execute('''INSERT INTO matches (match_league, match_team1, match_team2,
                 match_date, match_url) VALUES (?, ?, ?, ?, ?)
              ''', (league_id, team1, team2, match_date, browser.current_url))

    last_id = c.lastrowid

    return last_id, back


def update_quotes_table(browser, db, c, all_fields, last_id):

    all_panels = find_all_panels(browser, 0)

    for panel in all_panels:
        scroll_to_element(browser, 'false', panel)
        if 'active' not in panel.get_attribute('class'):
            panel.click()
            time.sleep(2)

    fields_bets = find_all_fields_and_bets(browser)

    for field, bets in zip(fields_bets[0], fields_bets[1]):
        scroll_to_element(browser, 'false', field)
        field_name = field.text.upper()

        if field_name in all_fields:
            all_bets = bets.find_elements_by_xpath(
                './/div[@class="selection-name ng-binding"]')

            for i, new_bet in enumerate(all_bets):
                scroll_to_element(browser, 'false', new_bet)
                if field_name == 'ESITO FINALE 1X2 HANDICAP':
                    bet_name = new_bet.text.upper().split()[0]
                else:
                    bet_name = new_bet.text.upper()

                bet_quote = bets.find_elements_by_xpath(
                                 './/div[@class="selection-price"]')[i]
                scroll_to_element(browser, 'false', bet_quote)
                bet_quote = bet_quote.text

                if len(bet_quote) == 1:
                    bet_quote = '@LOCKED'
                else:
                    bet_quote = float(bet_quote)

                field_id = list(c.execute(
                        '''SELECT field_id from fields WHERE field_name = ? AND
                           field_value = ?''', (field_name, bet_name)))[0][0]

                c.execute(
                        '''INSERT INTO quotes (quote_match, quote_field,
                           quote_value) VALUES (?, ?, ?)''',
                        (last_id, field_id, bet_quote))
                db.commit()


def fill_db_with_quotes():

    """
    Call the function 'scan_league()' for all the leagues present in the
    dict "countries" to fully update the db.
    """

    def three_buttons(browser, league):

        click_country_button(browser, league, 0)
        click_league_button(browser, league)
        # click_country_button(browser, league, 0)
        filters = './/div[@class="markets-favourites"]'

        return filters

    browser = go_to_lottomatica(0)
    dbf.empty_table('quotes')
    dbf.empty_table('matches')
    db, c = dbf.start_db()

    all_fields = list(c.execute('''SELECT field_name FROM fields'''))
    all_fields = [element[0] for element in all_fields]

    for league in countries:
        start = time.time()
        filters = three_buttons(browser, league)
        league_url = browser.current_url
        time.sleep(3)
        skip_league = False

        for i in range(3):
            try:
                wait_visible(browser, WAIT, filters)
                break
            except TimeoutException:
                if i < 2:
                    logger.info('Recursive {}'.format(league))
                    browser.get(league_url)
                    time.sleep(3)
                    continue
                else:
                    logger.info('Failing to update quotes from {}'.format(
                                                                       league))
                    skip_league = True

        if skip_league:
            continue

        c.execute('''SELECT league_id FROM leagues WHERE league_name = ? ''',
                  (league,))
        league_id = c.fetchone()[0]

        for i in range(1):
            try:
                buttons = './/div[@class="block-event event-description"]'

                WebDriverWait(
                        browser, 30).until(EC.element_to_be_clickable(
                                                   (By.XPATH, buttons)))
                match = browser.find_elements_by_xpath(buttons)[i]
                scroll_to_element(browser, 'true', match)
                scroll_to_element(browser, 'false', match)
                ddmmyy, hhmm = match.find_element_by_xpath(
                        './/div[@class="event-date ng-binding"]').\
                    text.split(' - ')
                match.click()
                last_id, back = update_matches_table(browser, c, league_id,
                                               ddmmyy, hhmm)
                update_quotes_table(browser, db, c, all_fields, last_id)
                scroll_to_element(browser, 'false', back)
                back.click()
            except IndexError:
                end = time.time() - start
                minutes = int(end // 60)
                seconds = round(end % 60)
                logger.info('Updating {} took {}:{}'.format(league, minutes,
                                                            seconds))
                break

    db.close()
    browser.quit()


def all_bets_per_team(db, c, team_name, league_id):

    """
    Return two text messages: one showing all the standard bets and the
    other one the combo. Both of them are relative to the match of the
    league whose id is "league_id" and team "team_name" is playing.
    """

    fields2avoid = [i for i in range(17, 31)]

    try:
        match_id, team1, team2 = list(
                c.execute('''SELECT match_id, match_team1, match_team2 FROM
                             matches WHERE match_league = ? AND
                             (match_team1 = ? OR match_team2 = ?)''',
                         (league_id, team_name, team_name,)))[0]
    except IndexError:
        db.close()
        raise ValueError('Quotes not available')

    team1 = team1.replace('*', '')
    team2 = team2.replace('*', '')

    message_standard = '<b>{} - {}: STANDARD</b>\n'.format(team1, team2)
    message_combo = '<b>{} - {}: COMBO</b>\n'.format(team1, team2)

    fields = list(c.execute('''SELECT field_id, field_value FROM fields'''))
    fields = [el for el in fields if el[0] not in fields2avoid]

    fields_added = []
    for field_id, field_value in fields:
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
