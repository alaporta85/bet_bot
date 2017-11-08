import matplotlib.pyplot as plt
import sqlite3


def perc_success():

    total = {'Testazza': 0,
             'Nonno': 0,
             'Pacco': 0,
             'Zoppo': 0,
             'Nano': 0}

    wins = {'Testazza': 0,
            'Nonno': 0,
            'Pacco': 0,
            'Zoppo': 0,
            'Nano': 0}

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    n_bets = len(list(c.execute('''SELECT ddmmyy FROM bets WHERE
                                status = "Placed" ''')))
    all_bets_list = list(c.execute('''SELECT user, label FROM matches'''))
    db.close()

    for bet in all_bets_list:
        user = bet[0]
        label = bet[1]
        total[user] += 1
        if label == 'WINNING':
            wins[user] += 1

    final_data = [(user, total[user], round(((wins[user]/total[user])*100), 1))
                  for user in total]
    final_data.sort(key=lambda x: x[2], reverse=True)

    names = [element[0] for element in final_data]
    perc = [element[2] for element in final_data]
    printed_perc = []
    for x in range(len(names)):
        user = names[x]
        single_perc = str(perc[x])
        personal_bets = str(total[user])
        printed_perc.append(single_perc + '({})'.format(personal_bets))

    colors = ['#cc0000', 'orange', 'green', '#1ac6ff', 'b']

    fig = plt.bar(range(5), perc, 0.5,  color=colors)
    plt.xticks(range(5), names, fontsize=13)
    plt.ylabel('% of success', fontsize=13)
    plt.ylim(0, 100)
    plt.title('Total number of bets: {}'.format(n_bets), fontsize=18)

    count = 0
    for rect in fig:
        height = rect.get_height()
        plt.text(rect.get_x() + rect.get_width()/2.0, height+2,
                 '{}'.format(printed_perc[count]), ha='center', va='bottom',
                 fontsize=14)
        count += 1

    plt.savefig('score.png')
    plt.gcf().clear()


def aver_quote():

    total = {'Testazza': 0,
             'Nonno': 0,
             'Pacco': 0,
             'Zoppo': 0,
             'Nano': 0}

    quotes = {'Testazza': 0,
              'Nonno': 0,
              'Pacco': 0,
              'Zoppo': 0,
              'Nano': 0}

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT user, quote FROM matches'''))
    db.close()

    for bet in all_bets_list:
        user = bet[0]
        quote = bet[1]
        total[user] += 1
        quotes[user] += quote

    final_data = [(user, round(quotes[user]/total[user], 2)) for user in total]
    final_data.sort(key=lambda x: x[1], reverse=True)

    names = [element[0] for element in final_data]
    values = [element[1] for element in final_data]

    colors = ['#cc0000', 'orange', 'green', '#1ac6ff', 'b']

    fig = plt.bar(range(5), values, 0.5,  color=colors)
    plt.xticks(range(5), names, fontsize=13)
    plt.ylim(0, 4)
    plt.title('Average quote', fontsize=18)

    for rect in fig:
        height = rect.get_height()
        plt.text(rect.get_x() + rect.get_width()/2.0, height+0.1,
                 '{:.2f}'.format(height), ha='center', va='bottom',
                 fontsize=14)

    plt.savefig('aver_quote.png')
    plt.gcf().clear()


def highest():

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT user, team1, team2, field, bet,
                                   quote, label FROM matches'''))
    db.close()

    fin_name = ''
    fin_team1 = ''
    fin_team2 = ''
    fin_field = ''
    fin_bet = ''
    fin_quote = 0

    for element in all_bets_list:
        temp_name = element[0]
        temp_team1 = element[1]
        temp_team2 = element[2]
        temp_field = element[3]
        temp_bet = element[4]
        temp_quote = element[5]
        temp_label = element[6]

        if temp_label == 'WINNING':
            if temp_quote > fin_quote:
                fin_name = temp_name
                fin_team1 = temp_team1
                fin_team2 = temp_team2
                fin_field = temp_field
                fin_bet = temp_bet
                fin_quote = temp_quote

    message = ('Highest WINNING quote is ' +
               '{} from:\n\n{}\n{} - {}\n{}\n{}'.format(fin_quote, fin_name,
                                                        fin_team1, fin_team2,
                                                        fin_field, fin_bet))

    return message


def lowest():

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT user, team1, team2, field, bet,
                                   quote, label FROM matches'''))
    db.close()

    fin_name = ''
    fin_team1 = ''
    fin_team2 = ''
    fin_field = ''
    fin_bet = ''
    fin_quote = 5000

    for element in all_bets_list:
        temp_name = element[0]
        temp_team1 = element[1]
        temp_team2 = element[2]
        temp_field = element[3]
        temp_bet = element[4]
        temp_quote = element[5]
        temp_label = element[6]

        if temp_label == 'LOSING':
            if temp_quote < fin_quote:
                fin_name = temp_name
                fin_team1 = temp_team1
                fin_team2 = temp_team2
                fin_field = temp_field
                fin_bet = temp_bet
                fin_quote = temp_quote

    message = ('Lowest LOSING quote is ' +
               '{} from:\n\n{}\n{} - {}\n{}\n{}'.format(fin_quote, fin_name,
                                                        fin_team1, fin_team2,
                                                        fin_field, fin_bet))

    return message
