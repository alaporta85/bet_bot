import matplotlib.pyplot as plt
import sqlite3

partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']


def perc_success():

    total = {name: 0 for name in partecipants}

    wins = {name: 0 for name in partecipants}

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

    plt.savefig('score.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def aver_quote():

    total = {name: 0 for name in partecipants}

    quotes = {name: 0 for name in partecipants}

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

    plt.savefig('aver_quote.png', dpi=120, bbox_inches='tight')
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


def euros_lost_for_one_bet():

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    amount = {name: 0 for name in partecipants}

    all_bets_list = list(c.execute('''SELECT bets_id, prize FROM bets
                                   WHERE result = "Non Vincente" '''))

    for x in range(len(all_bets_list)):
        temp_id = all_bets_list[x][0]
        temp_prize = all_bets_list[x][1]

        single_bets = list(c.execute('''SELECT user, label FROM bets INNER JOIN
                                     matches ON matches.bets_id = bets.bets_id
                                     WHERE matches.bets_id = ?''', (temp_id,)))

        losing_list = [element[0] for element in single_bets
                       if element[1] == 'LOSING']
        if len(losing_list) == 1:
            amount[losing_list[0]] += temp_prize

    data = [(name, amount[name]) for name in amount]
    data.sort(key=lambda x: x[1], reverse=True)

    euros = []
    names = []
    for element in data:
        if element[1]:
            names.append(element[0])
            euros.append(element[1])

    n_values = len(euros)

    colors = ['#cc0000', 'orange', 'green', '#1ac6ff', 'b']
    plt.axes(aspect=1)
    plt.title('Euros lost for 1 person', fontsize=25, position=(0.5, 1.3))
    explode = [0 for x in range(len(euros))]
    explode[0] = 0.07

    def real_value(val):
        return round(val/100*sum(euros), 1)

    patches, text, autotext = plt.pie(euros, labels=names, explode=explode,
                                      colors=colors[:n_values],
                                      startangle=90, radius=1.5,
                                      autopct=real_value)

    for patch in patches:
        patch.set_linewidth(1.5)
        patch.set_edgecolor('black')
    for x in range(n_values):
        if x == 0:
            text[x].set_fontsize(30)
        else:
            text[x].set_fontsize(18)
    for y in range(n_values):
        if y == 0:
            autotext[y].set_fontsize(30)
        else:
            autotext[y].set_fontsize(18)

    plt.savefig('euros_lost.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()    
    
    
    
    
