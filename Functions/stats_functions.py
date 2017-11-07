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
    
    colors = ['#cc0000', 'orange', 'green', '#1ac6ff', 'b']

    fig = plt.bar(range(5), perc, 0.5,  color=colors)
    plt.xticks(range(5), names, fontsize=13)
    plt.ylabel('% of success', fontsize=13)
    plt.ylim(0, 100)
    plt.title('Total number of bets: {}'.format(n_bets), fontsize=18)

    for rect in fig:
        height = rect.get_height()
        plt.text(rect.get_x() + rect.get_width()/2.0, height+2,
                 '{:.1f}'.format(height), ha='center', va='bottom',
                 fontsize=14)

    plt.savefig('score.png')


perc_success()
