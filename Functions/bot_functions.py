import time
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.keys import Keys
from Functions import logging as log

logger = log.get_flogger()


def go_to_personal_area(browser, LIMIT_1):

    '''Used in update_results() function to navigate until the personal area
       after the login.'''

    current_url = browser.current_url

    try:
        area_pers_path1 = './/a[@title="Area Personale"]'
        sf.wait_clickable(browser, 20, area_pers_path1)
        area_pers_button1 = browser.find_element_by_xpath(area_pers_path1)
        area_pers_button1.click()

        area_pers_path2 = ('.//div[@id="profile-home"]/' +
                           'a[@href="/area-personale"]')
        sf.wait_clickable(browser, 20, area_pers_path2)
        area_pers_button2 = browser.find_element_by_xpath(area_pers_path2)
        area_pers_button2.click()

    except (TimeoutException, ElementNotInteractableException):

        if LIMIT_1 < 3:
            print('recursive personal area')
            browser.get(current_url)
            time.sleep(3)
            go_to_personal_area(browser, LIMIT_1 + 1)
        else:
            raise ConnectionError('Unable to go to the section: ' +
                                  'AREA PERSONALE. Please try again.')


def go_to_placed_bets(browser, LIMIT_2):

    '''Used in update_results() function to navigate until the page containing
       all the past bets.'''

    FILTER = 'Ultimi 5 Mesi'
    current_url = browser.current_url

    try:
        placed_bets_path = './/a[@id="pl-movimenti"]'
        sf.wait_clickable(browser, 20, placed_bets_path)
        placed_bets_button = browser.find_element_by_xpath(placed_bets_path)
        placed_bets_button.click()
        time.sleep(5)

        date_filters_path = ('.//div[@id="movement-filters"]/' +
                             'div[@id="games-filter"]//' +
                             'label[@class="radio-inline"]')
        sf.wait_visible(browser, 20, date_filters_path)
        date_filters_list = browser.find_elements_by_xpath(date_filters_path)
        for afilter in date_filters_list:
            new_filter = afilter.text
            if new_filter == FILTER:
                sf.scroll_to_element(browser, 'false', afilter)
                afilter.click()
                break

        mostra_path = ('.//div[@class="btn-group btn-group-justified"]' +
                       '/a[@class="btn button-submit"]')
        sf.wait_clickable(browser, 20, mostra_path)
        mostra_button = browser.find_element_by_xpath(mostra_path)
        sf.scroll_to_element(browser, 'false', mostra_button)
        mostra_button.click()

    except (TimeoutException, ElementNotInteractableException):

        if LIMIT_2 < 3:
            print('recursive movimenti e giocate')
            browser.get(current_url)
            time.sleep(3)
            go_to_placed_bets(browser, LIMIT_2 + 1)
        else:
            raise ConnectionError('Unable to go to the section: MOVIMENTI E' +
                                  ' GIOCATE. Please try again.')


def analyze_details_table(browser, ref_id, c, new_status, LIMIT_4):

    '''Used in analyze_main_table function. It first checks if all the matches
       inside the bet are concluded. If yes, update the column bet_result in
       the table 'bet' and the columns 'pred_result' and pred_label in the
       table 'predictions' of the database.'''

    current_url = browser.current_url

    try:
        new_table_path = './/table[@class="bet-detail"]'
        sf.wait_visible(browser, 20, new_table_path)
        new_bets_list = browser.find_elements_by_xpath(
                new_table_path + '//tr[@class="ng-scope"]')

        matches_completed = 0
        for new_bet in new_bets_list:
            label_element = new_bet.find_element_by_xpath(
                './/div[contains(@class,"ng-scope")]')
            label = label_element.get_attribute('ng-switch-when')
            if label == 'WINNING' or label == 'LOSING':
                matches_completed += 1

        if matches_completed != len(new_bets_list):
            return 0

        for new_bet in new_bets_list:
            match = new_bet.find_element_by_xpath('.//td[6]').text
            team1 = match.split(' - ')[0]
            team2 = match.split(' - ')[1]
            label_element = new_bet.find_element_by_xpath(
                    './/div[contains(@class,"ng-scope")]')
            label = label_element.get_attribute('ng-switch-when')
            result = new_bet.find_element_by_xpath('.//td[11]').text

            c.execute('''SELECT pred_id FROM bets INNER JOIN predictions on
                      pred_bet = bet_id WHERE bet_id = ? AND
                      pred_team1 = ? AND pred_team2 = ?''', (ref_id, team1,
                                                             team2))

            match_id = c.fetchone()[0]

            c.execute('''UPDATE bets SET bet_result = ? WHERE
                      bet_id = ?''', (new_status, ref_id))

            c.execute('''UPDATE predictions SET pred_result = ?, pred_label = ?
                      WHERE pred_id = ?''', (result, label, match_id))

        return 1

    except (TimeoutException, ElementNotInteractableException):

        if LIMIT_4 < 3:
            print('recursive details table')
            browser.get(current_url)
            time.sleep(3)
            analyze_details_table(browser, ref_id, c, LIMIT_4 + 1)
        else:
            raise ConnectionError('Unable to find past bets. ' +
                                  'Please try again.')


def analyze_main_table(browser, ref_list, LIMIT_3):

    '''Used in update_results() function to drive the browser to the personal
       area in the 'MOVIMENTI E GIOCATE' section and call the function
       analyze_details_table for each bet not updated yet.'''

    current_url = browser.current_url
    bets_updated = 0

    try:
        table_path = ('.//table[@id="tabellaRisultatiTransazioni"]')
        sf.wait_visible(browser, 20, table_path)
        bets_list = browser.find_elements_by_xpath(table_path +
                                                   '//tr[@class="ng-scope"]')

        db, c = dbf.start_db()

        for ref_bet in ref_list:
            ref_id = ref_bet[0]
            ref_date = ref_bet[1]
            year = str(ref_date)[:4]
            month = str(ref_date)[4:6]
            day = str(ref_date)[6:]
            ref_date = day + '/' + month + '/' + year

            for bet in bets_list:

                logger.info('Updating bet with id: {}'.format(ref_id))

                color = bet.find_element_by_xpath(
                        './/td[contains(@class,"state state")]')\
                    .get_attribute('class')

                if 'blue' not in color:

                    date = bet.find_element_by_xpath(
                            './/td[@class="ng-binding"]').text[:10]

                    if date == ref_date:

                        new_status = bet.find_element_by_xpath(
                                './/translate-label[@key-default=' +
                                '"statement.state"]').text

                        if new_status == 'Vincente':
                            new_status = 'WINNING'
                        elif new_status == 'Non Vincente':
                            new_status = 'LOSING'

                        main_window = browser.current_window_handle
                        bet.find_element_by_xpath('.//a').click()
                        time.sleep(3)

                        new_window = browser.window_handles[-1]
                        browser.switch_to_window(new_window)

                        bets_updated += analyze_details_table(browser, ref_id,
                                                              c, new_status, 0)

                        browser.close()

                        browser.switch_to_window(main_window)
                        break
        db.commit()
        db.close()

        return bets_updated

    except (TimeoutException, ElementNotInteractableException):

        if LIMIT_3 < 3:
            print('recursive main table')
            browser.get(current_url)
            time.sleep(3)
            analyze_main_table(browser, ref_list, LIMIT_3 + 1)
        else:
            raise ConnectionError('Unable to find past bets. ' +
                                  'Please try again.')


def check_still_to_confirm(db, c, first_name):

    # This a list of the users who have their bets in the status
    # 'Not Confirmed'
    users_list = list(c.execute('''SELECT pred_user FROM predictions WHERE
                                pred_status = "Not Confirmed"'''))
    users_list = [element[0] for element in users_list]

    if first_name in users_list:

        ref_list = list(c.execute('''SELECT pred_team1, pred_team2,
                                  pred_rawbet, pred_quote FROM predictions
                                  WHERE pred_status = "Not Confirmed" AND
                                  pred_user = ?''', (first_name,)))
        db.close()

        team1, team2, bet, bet_quote = ref_list[0]

        printed_bet = '{} - {} {} @{}'.format(team1, team2, bet, bet_quote)

        message = ('{}, you still have one bet to confirm.\n'.format(
                   first_name) + ('{}\n' + 'Use /confirm or /cancel to ' +
                   'finalize your bet.').format(printed_bet))

        return message

    else:
        return False


def update_tables_and_ref_list(db, c, first_name, bet_id):

    '''Called inside the command /confirm.
       Insert a new row in the 'bets' table if needed and update the columns
       pred_bet and pred_status of the table 'predictions'. Return a list
       containing the tuple (team1, team2, league_id) of the match which is
       beign confirmed. It will be used inside the function check_if_duplicate
       to delete all the Not Confirmed bets relative to same match, if present,
       from the 'predictions' table.'''

    if not bet_id:

        # If not, we create it and update 'matches' table
        c.execute('''INSERT INTO bets (bet_status, bet_result)
        VALUES (?, ?)''', ('Pending', 'Unknown'))

        bet_id = c.lastrowid

    c.execute('''UPDATE predictions SET pred_bet = ?, pred_status = "Confirmed"
              WHERE pred_user = ? AND pred_status = "Not Confirmed"''',
              (bet_id, first_name))

    ref_list = list(c.execute('''SELECT pred_team1, pred_team2, pred_league
                              FROM bets INNER JOIN predictions on
                              pred_bet = bet_id WHERE bet_id = ? AND
                              pred_user = ?''', (bet_id, first_name)))

    db.commit()

    return ref_list


def check_if_duplicate(c, first_name, match, ref_list):

    message = ''

    pred_id = match[0]
    user = match[1]
    team1 = match[2]
    team2 = match[3]
    league = match[4]

    if (team1, team2, league) in ref_list:
        c.execute('''DELETE FROM predictions WHERE pred_id = ?''',
                  (pred_id,))
        message = ('{}, your bet on the match '.format(user) +
                   '{} - {} has '.format(team1, team2) +
                   'been canceled because ' +
                   '{} confirmed first.'.format(first_name))

    return message


def create_matches_to_play(db, c, bet_id):

    '''Called inside the command /play_bet.
       Return a list of tuples representing the matches to be added in the
       basket.'''

    some_data = list(c.execute('''SELECT pred_team1, pred_team2, pred_league,
                               pred_field FROM bets INNER JOIN predictions on
                               pred_bet = bet_id WHERE bet_id = ?''',
                               (bet_id,)))
    matches_to_play = []

    for match in some_data:
        team1 = match[0]
        team2 = match[1]
        league = match[2]
        field_id = match[3]

        if league == 8:
            team1 = '*' + team1
            team2 = '*' + team2

        field_name, field_value = list(c.execute('''SELECT field_name,
                                                 field_value FROM fields WHERE
                                                 field_id = ?''',
                                                 (field_id,)))[0]

        url = list(c.execute('''SELECT match_url FROM matches WHERE
                             match_team1 = ? AND match_team2 = ? AND
                             match_league = ?''', (team1, team2,
                                                   league)))[0][0]

        matches_to_play.append((team1, team2, field_name, field_value, url))

    return matches_to_play


def add_bet_to_basket(browser, match, count, mess_id, dynamic_message,
                      matches_to_play):

    team1 = match[0]
    team2 = match[1]
    field = match[2]
    bet = match[3]
    url = match[4]

    try:
        sf.add_bet(browser, url, field, bet)
        time.sleep(5)
        sf.check_single_bet(browser, count, team1, team2)
        return dynamic_message.format(count + 1)

    except ConnectionError as e:
        raise ConnectionError(str(e))


def insert_euros(browser, matches_to_play, matches_played, euros):

    input_euros = ('.//div[contains(@class,"text-right ' +
                   'amount-sign")]/input')
    euros_box = browser.find_element_by_xpath(input_euros)
    euros_box.send_keys(Keys.COMMAND, "a")
    euros_box.send_keys(Keys.LEFT)
    euros_box.send_keys(euros)
    euros_box.send_keys(Keys.DELETE)

    win_path = ('.//div[@class="row ticket-bet-infos"]//' +
                'p[@class="amount"]/strong')
    win_container = browser.find_element_by_xpath(win_path)
    sf.scroll_to_element(browser, 'false', win_container)

    possible_win_default = win_container.text[2:].replace(',', '.')

    # Manipulate the possible win's format to avoid errors
    if len(possible_win_default.split('.')) == 2:
        possible_win_default = float(possible_win_default)
    else:
        possible_win_default = float(''.join(
                possible_win_default.split('.')[:-1]))
    possible_win = round(possible_win_default * (euros/2), 2)

    return possible_win


def matches_per_day(day):

    '''Return a message containing all the matches scheduled for the day "day".
       Input "day" needs to have the correct form in order to be handled by
       the function format_day.'''

    message = ''
    date, time = dbf.todays_date()
    requested_day = sf.format_day(day)

    db, c = dbf.start_db()
    try:
        bet_id = list(c.execute('''SELECT bet_id FROM bets WHERE
                                bet_status = "Pending" '''))[0][0]
    except IndexError:
        bet_id = 0

    confirmed_matches = list(c.execute('''SELECT pred_league, pred_team1,
                                       pred_team2, pred_time FROM bets INNER
                                       JOIN predictions on pred_bet = bet_id
                                       WHERE bet_id = ?''', (bet_id,)))

    for league in sf.countries:

        league_id = list(c.execute('''SELECT league_id FROM leagues WHERE
                                   league_name = ?''', (league,)))[0][0]

        matches_to_print = list(c.execute('''SELECT match_id, match_team1,
                                          match_team2, match_time FROM matches
                                          WHERE match_date = ? AND
                                          match_league = ?''', (requested_day,
                                                                league_id)))
        for match in confirmed_matches:
            try:
                match_id = list(c.execute('''SELECT match_id FROM matches WHERE
                                          match_league = ? AND match_team1 = ?
                                          AND match_team2 = ?''',
                                          (league_id, match[1],
                                           match[2])))[0][0]
            except IndexError:
                continue

            new_tuple = (match_id, match[1], match[2], match[3])

            if new_tuple in matches_to_print:
                matches_to_print.remove(new_tuple)

        if matches_to_print:
            message += '\n\n<b>{}</b>'.format(league)
            for match in matches_to_print:
                match_id = match[0]
                team1 = match[1].replace('*', '')
                team2 = match[2].replace('*', '')
                match_time = str(match[3]).zfill(4)
                match_time = match_time[:2] + ':' + match_time[2:]

                short_team1 = list(c.execute('''SELECT team_short_value FROM
                                             teams_short WHERE
                                             team_short_name = ?''',
                                             (team1,)))[0][0]
                short_team2 = list(c.execute('''SELECT team_short_value FROM
                                             teams_short WHERE
                                             team_short_name = ?''',
                                             (team2,)))[0][0]

                quote1 = list(c.execute('''SELECT quote_value FROM quotes WHERE
                                        quote_match = ? AND quote_field = 1''',
                                        (match_id,)))[0][0]
                quoteX = list(c.execute('''SELECT quote_value FROM quotes WHERE
                                        quote_match = ? AND quote_field = 2''',
                                        (match_id,)))[0][0]
                quote2 = list(c.execute('''SELECT quote_value FROM quotes WHERE
                                        quote_match = ? AND quote_field = 3''',
                                        (match_id,)))[0][0]

                message += '\n{}   <i>{} - {}</i>   {} / {} / {}'.format(
                                                                match_time,
                                                                short_team1,
                                                                short_team2,
                                                                quote1,
                                                                quoteX,
                                                                quote2)

    db.close()

    if message:
        return message
    else:
        return 'No matches on the selected day.'
