import time
from Functions import db_functions as dbf
from Functions import selenium_functions as sf
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementNotInteractableException


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

        LIMIT_1 += 1

        if LIMIT_1 < 3:
            print('recursive personal area')
            browser.get(current_url)
            time.sleep(3)
            go_to_personal_area(browser, LIMIT_1)
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

        LIMIT_2 += 1

        if LIMIT_2 < 3:
            print('recursive movimenti e giocate')
            browser.get(current_url)
            time.sleep(3)
            go_to_placed_bets(browser, LIMIT_2)
        else:
            raise ConnectionError('Unable to go to the section: MOVIMENTI E' +
                                  ' GIOCATE. Please try again.')


def analyze_details_table(browser, ref_id, c, LIMIT_4):

    '''Used in analyze_main_table function to update the column 'result' in the
       table 'matches' of the database.'''

    current_url = browser.current_url

    try:
        new_table_path = './/table[@class="bet-detail"]'
        sf.wait_visible(browser, 20, new_table_path)
        new_bets_list = browser.find_elements_by_xpath(
                new_table_path + '//tr[@class="ng-scope"]')
        for new_bet in new_bets_list:

            match = new_bet.find_element_by_xpath('.//td[6]').text
            team1 = match.split(' - ')[0]
            team2 = match.split(' - ')[1]
            result_element = new_bet.find_element_by_xpath(
                    './/div[contains(@class,"ng-scope")]')
            result = result_element.get_attribute('ng-switch-when')

            c.execute('''SELECT matches_id FROM bets INNER JOIN matches on
                      matches.bets_id = bets.bets_id WHERE bets.bets_id = ? AND
                      team1 = ? AND team2 = ?''', (ref_id, team1, team2))

            match_id = c.fetchone()[0]

            c.execute('''UPDATE matches SET result = ? WHERE matches_id = ?''',
                      (result, match_id))

    except (TimeoutException, ElementNotInteractableException):

        LIMIT_4 += 1

        if LIMIT_4 < 3:
            print('recursive details table')
            browser.get(current_url)
            time.sleep(3)
            analyze_details_table(browser, ref_id, c, LIMIT_4)
        else:
            raise ConnectionError('Unable to find past bets. ' +
                                  'Please try again.')


def analyze_main_table(browser, ref_list, LIMIT_3, LIMIT_4):

    '''Used in update_results() function to update the column 'result' in the
       table 'bets' of the database. It also calls the function
       analyze_details_table for each row of the table.'''

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

            for bet in bets_list:

                color = bet.find_element_by_xpath(
                        './/td[contains(@class,"state state")]')\
                        .get_attribute('class')

                if 'blue' not in color:

                    date = bet.find_element_by_xpath(
                            './/td[@class="ng-binding"]').text[:10]

                    if date == ref_date:

                        bets_updated += 1

                        new_status = bet.find_element_by_xpath(
                                './/translate-label[@key-default=' +
                                '"statement.state"]').text
                        c.execute('''UPDATE bets SET result = ? WHERE
                                  bets_id = ?''', (new_status, ref_id))
                        db.commit()

                        main_window = browser.current_window_handle
                        bet.find_element_by_xpath('.//a').click()
                        time.sleep(3)

                        new_window = browser.window_handles[-1]
                        browser.switch_to_window(new_window)

                        analyze_details_table(browser, ref_id, c, LIMIT_4)

                        browser.close()

                        browser.switch_to_window(main_window)
                        break
        db.commit()
        db.close()

        return bets_updated

    except (TimeoutException, ElementNotInteractableException):

        LIMIT_3 += 1

        if LIMIT_3 < 3:
            print('recursive main table')
            browser.get(current_url)
            time.sleep(3)
            analyze_main_table(browser, ref_list, LIMIT_3, LIMIT_4)
        else:
            raise ConnectionError('Unable to find past bets. ' +
                                  'Please try again.')
