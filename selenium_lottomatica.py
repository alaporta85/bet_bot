from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def go_to_league_bets(league):
    
    if league=='SERIE A':
        temp = calcio[:-1] + 'ul/li[4]'
        browser.find_element_by_xpath(temp).click()
        temp2 = temp + '/ul/li[1]'
        browser.find_element_by_xpath(temp2).click()
        
def get_quote(team,bet):
    quote = 0
    all_tables = browser.find_elements_by_xpath(container + '/div')
    for table in all_tables:
        all_matches = table.find_elements_by_xpath('.//tbody/tr[contains'+
                                                        '(@class,"ng-scope")]')
        for match in all_matches:
            match_text = match.find_element_by_xpath('.//td[contains'+
                                            '(@colspan,"1")]/a/strong').text
            if team in match_text:
                match_box = match.find_element_by_xpath('.//td[contains'+
                                                        '(@colspan,"1")]/a')
                browser.execute_script('return arguments[0]'+
                                       '.scrollIntoView(false);', match_box)
                webdriver.ActionChains(browser).move_to_element(match_box)\
                .click(match_box).perform()
                print(match_text)
                quote=1
                break
        if quote:
            break


text = 'SERIE A-JUVENTUS-2'


browser = webdriver.Firefox()
url = ('https://www.lottomatica.it/scommesse/avvenimenti/'+
       'scommesse-sportive.html')
browser.get(url)

calcio = ('/html/body/div[4]/section/div[1]/div/div/div[1]/'+
          'div/div/div/ul/li[1]/a')

WebDriverWait(browser,20).until(EC.element_to_be_clickable((By.XPATH, calcio)))

browser.find_element_by_xpath(calcio).click()

league,team,bet = text.split('-')

go_to_league_bets(league)

container = ('/html/body/div[4]/section/div[1]/div/div/div[2]/'+
             'div/div[3]/div[1]/div/div/div[2]')

WebDriverWait(browser,20).until(EC.element_to_be_clickable(
                                                        (By.XPATH, container)))

get_quote(team,bet)

browser.quit()
















