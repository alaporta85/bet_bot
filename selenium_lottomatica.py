import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from Functions import selenium_functions as sf
from Functions import db_functions as dbf
import messina_bet_bot as mbb


def look_for_quote(text):

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')

    # Start the browser, go to Lottomatica webpage and wait
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(3)

    # 'OGGI E DOMANI' button
#    sf.click_oggi_domani_button(browser, scroll='yes')

    # 'CALCIO' button
    sf.click_calcio_button(browser, 'yes')

    # In case the input bet has the form team_bet we use the function
    # get_field to find the right field and then format the bet. In this
    # case the inputs do NOT need to be correct. Most of the cases are
    # handled by the code to return the correct element
    if len(text.split('_')) == 2:
        try:
            input_team, bet = text.split('_')
            input_team, bet = input_team.upper(), bet.upper()
            field = sf.get_field(browser, bet)
        except SyntaxError as e:
            raise SyntaxError(str(e))
        right_bet = sf.format_bet(field, bet)

    # On the other hand, if the input has the form league_team_field_bet we
    # directly use all of them to format the bet. In this case ALL the
    # inputs need to be EXACTLY as in the webpage
#    else:
#        try:
#            league, input_team, field, bet = text.split('_')
#            league, input_team, field, bet = (league.upper(),
#                                              input_team.upper(),
#                                              field.upper(), bet.upper())
#        except SyntaxError:
#            browser.quit()
#            raise SyntaxError(bet + ': Bet not valid.')
#        right_bet = sf.format_bet(field, bet)

    # Navigate to page containing the bet of the match we have chosen
    try:
        team1, team2, league = sf.go_to_all_bets(browser, input_team)
    except SyntaxError as e:
        raise SyntaxError(str(e))
    except ConnectionError as e:
        raise ConnectionError(str(e))

    # Store the quote
    try:
        bet_quote = sf.get_quote(browser, field, right_bet)
    except ConnectionError as e:
        raise ConnectionError(str(e))
    current_url = browser.current_url
    browser.quit()
    return league, team1, team2, right_bet, bet_quote, field, current_url


def add_first_bet(browser, current_url, field, right_bet):

    '''Add the quote to the basket by taking directly the url of the bet.
       This is used inside the play_bet function to play the first match.'''

    browser.get(current_url)
    time.sleep(3)

    try:
        sf.get_quote(browser, field, right_bet, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def add_following_bets(browser, team, field, right_bet):

    '''Add all the other quotes after the first one. It does NOT use the url
       but look for each button instead.'''

    # Navigate to the right page
    all_days = ('.//div[contains(@class,"margin-bottom ng-scope")]')
    try:
        sf.wait_clickable(browser, 20, all_days)
        all_tables = browser.find_elements_by_xpath(all_days)
    except TimeoutException:
        browser.quit()
        raise ConnectionError
    sf.click_match_button(browser, all_tables, team)

    # Store the quote
    try:
        sf.get_quote(browser, field, right_bet, 'yes')
    except ConnectionError as e:
        raise ConnectionError(str(e))


def check_single_bet(browser, anumber):

    '''Check whether the bet is inserted correctly.'''

    basket = ('.//ul[@class="toolbar-nav-list"]/li[contains(@class,' +
              '"ng-scope")]/a/span[contains(@class,"pill pill")]')

    try:
        current_number = int(browser.find_element_by_xpath(basket).text)

        if current_number == anumber + 1:
            return True
        else:
            browser.quit()
            return False
    except NoSuchElementException:
        browser.quit()
        return False


def go_to_personal_area(browser):

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
        print('recursive personal area')
        browser.get(current_url)
        time.sleep(3)
        go_to_personal_area(browser)
#        browser.quit()
#        raise ConnectionError('Unable to go to the section: AREA PERSONALE.' +
#                              'Please try again.')


def go_to_placed_bets(browser):

    FILTER = 'Ultimi 30 giorni'
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

    except TimeoutException:
        print('recursive movimenti e giocate')
        browser.get(current_url)
        time.sleep(3)
        go_to_placed_bets(browser)
#        browser.quit()
#        raise ConnectionError('Unable to go to the section: MOVIMENTI E ' +
#                              'GIOCATE. Please try again.')


def analyze_details_table(browser, ref_id):

    current_url = browser.current_url

    try:
        new_table_path = './/table[@class="bet-detail"]'
        sf.wait_visible(browser, 20, new_table_path)
        new_bets_list = browser.find_elements_by_xpath(
                new_table_path + '//tr[@class="ng-scope"]')
        for i in new_bets_list:

            match = i.find_element_by_xpath('.//td[6]').text
            team1 = match.split(' - ')[0]
            team2 = match.split(' - ')[1]
            result_element = i.find_element_by_xpath(
                    './/div[contains(@class,"ng-scope")]')
            result = result_element.get_attribute('ng-switch-when')

#            match_id = c.execute('''SELECT matches_id FROM bets INNER JOIN
#                                 matches on matches.bets_id = bets.bets_id
#                                 WHERE bets.bets_id = ? AND team1 = ? AND
#                                 team2 = ?''', (ref_id, team1, team2))
            print(team1, team2)
            print(result)

    except TimeoutException:
        print('recursive details table')
        browser.get(current_url)
        time.sleep(3)
        analyze_details_table(browser, ref_id)


def analyze_main_table(browser, ref_list):

    current_url = browser.current_url

    try:
        table_path = ('.//table[@id="tabellaRisultatiTransazioni"]')
        sf.wait_visible(browser, 20, table_path)
        bets_list = browser.find_elements_by_xpath(table_path +
                                                   '//tr[@class="ng-scope"]')

        db, c = dbf.start_db()

        for ref_bet in ref_list[:1]:
            ref_id = ref_bet[0]
            ref_date = ref_bet[1]

            for bet in bets_list:
                date = (bet.find_element_by_xpath(
                        './/td[@class="ng-binding"]').text)[:10]
                if date == ref_date:
                    new_status = bet.find_element_by_xpath(
                            './/translate-label[@key-default=' +
                            '"statement.state"]').text
                    c.execute('''UPDATE bets SET result = ? WHERE
                              bets_id = ?''', (new_status, ref_id))

                    main_window = browser.current_window_handle
                    bet.find_element_by_xpath('.//a').click()
                    time.sleep(3)

                    new_window = browser.window_handles[-1]
                    browser.switch_to_window(new_window)

                    analyze_details_table(browser, ref_id)

                    browser.close()

                    browser.switch_to_window(main_window)
                    break
        db.commit()
        db.close()

    except TimeoutException:
        print('recursive main table')
        browser.get(current_url)
        time.sleep(3)
        analyze_main_table(browser, ref_list)
#        browser.quit()
#        raise ConnectionError('Unable to find past bets. Please try again.')


def update_results():

    db, c = dbf.start_db()
#    ref_list = list(c.execute('''SELECT bets_id, ddmmyy FROM bets WHERE
#                              status = "Placed" AND result = "Unknown" '''))
    db.close()
    ref_list = [(1, '22/10/2017'), (2, '25/10/2017')]
#    print(ref_list)

    if not ref_list:
        print('No bets to update.')
        return 'No bets to update.'

    url = ('https://www.lottomatica.it/scommesse/avvenimenti/' +
           'scommesse-sportive.html')
    browser = webdriver.Firefox()
    browser.get(url)
    time.sleep(3)

    mbb.login(browser)
    time.sleep(5)

    try:
        go_to_personal_area(browser)

        go_to_placed_bets(browser)

        analyze_main_table(browser, ref_list)

    except ConnectionError as e:
        browser.quit()
        print(str(e))
        return str(e)

#    browser.quit()


#league, team1, team2, right_bet, bet_quote, field, current_url = (
#        look_for_quote('juve_gg'))

#update_results()
