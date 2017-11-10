import matplotlib.pyplot as plt
import sqlite3
import matplotlib.image as image

partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']
colors_dict = {'Zoppo': '#7fffd4',
               'Nano': '#ffad33',
               'Testazza': '#2eb82e',
               'Nonno': '#ff3300',
               'Pacco': '#028eb9'
               }


def perc_success():

    '''Return a bar plot showing the % of right bet for each partecipant.'''

    # Dict to store the TOTAL number of bets played by each partecipant
    total = {name: 0 for name in partecipants}

    # Dict to store the WINNING number of bets played by each partecipant
    wins = {name: 0 for name in partecipants}

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT bets_id, user, label FROM
                                   matches'''))
    n_bets = all_bets_list[-1][0]

    db.close()

    # Fill the dicts
    for bet in all_bets_list:
        user = bet[1]
        label = bet[2]
        total[user] += 1
        if label == 'WINNING':
            wins[user] += 1

    # Prepare the data for the plot
    final_data = [(user, total[user], round(((wins[user]/total[user])*100), 1))
                  for user in total]
    final_data.sort(key=lambda x: x[2], reverse=True)

    names = [element[0] for element in final_data]
    colors = [colors_dict[name] for name in names]
    perc = [element[2] for element in final_data]
    printed_perc = []
    for x in range(len(names)):
        user = names[x]
        single_perc = str(perc[x])
        personal_bets = str(total[user])
        printed_perc.append(single_perc + '({})'.format(personal_bets))

    bars = plt.bar(range(5), perc, 0.5,  color=colors)
    plt.xticks(range(5), names, fontsize=14)
    plt.ylabel('% of success', fontsize=15)
    plt.ylim(0, 100)
    plt.title('Total number of bets: {}'.format(n_bets), fontsize=18)

    count = 0
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height+2,
                 '{}'.format(printed_perc[count]), ha='center', va='bottom',
                 fontsize=15)
        count += 1

    plt.savefig('score.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def aver_quote():

    '''Return a bar plot showing the average quote for each partecipant.'''

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
    colors = [colors_dict[name] for name in names]
    values = [element[1] for element in final_data]

    bars = plt.bar(range(5), values, 0.5,  color=colors)
    plt.xticks(range(5), names, fontsize=14)
    plt.yticks(range(1, 5, 1), fontsize=14)
    plt.ylim(1, 4)
    plt.title('Average quote', fontsize=18)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height+0.1,
                 '{:.2f}'.format(height), ha='center', va='bottom',
                 fontsize=16)

    plt.savefig('aver_quote.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def records():

    '''Return two messages: one for the WINNING bet with the highest quote
       and one for the LOSING bet with the lowest quote.'''

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT user, team1, team2, field, bet,
                                   quote, label FROM matches'''))
    db.close()

    # Initialize parameters
    h_name = ''
    h_team1 = ''
    h_team2 = ''
    h_field = ''
    h_bet = ''
    h_quote = 0

    l_name = ''
    l_team1 = ''
    l_team2 = ''
    l_field = ''
    l_bet = ''
    l_quote = 5000

    for element in all_bets_list:
        temp_name = element[0]
        temp_team1 = element[1]
        temp_team2 = element[2]
        temp_field = element[3]
        temp_bet = element[4]
        temp_quote = element[5]
        temp_label = element[6]

        if temp_label == 'WINNING':
            if temp_quote > h_quote:
                h_name = temp_name
                h_team1 = temp_team1
                h_team2 = temp_team2
                h_field = temp_field
                h_bet = temp_bet
                h_quote = temp_quote
        else:
            if temp_quote < l_quote:
                l_name = temp_name
                l_team1 = temp_team1
                l_team2 = temp_team2
                l_field = temp_field
                l_bet = temp_bet
                l_quote = temp_quote

    h_message = ('Highest WINNING quote is ' +
                 '{} from:\n\n{}\n{} - {}\n{}\n{}'.format(h_quote, h_name,
                                                          h_team1, h_team2,
                                                          h_field, h_bet))
    l_message = ('Lowest LOSING quote is ' +
                 '{} from:\n\n{}\n{} - {}\n{}\n{}'.format(l_quote, l_name,
                                                          l_team1, l_team2,
                                                          l_field, l_bet))

    return h_message, l_message


def euros_lost_for_one_bet():

    '''Return a pie chart showing the amount of euros lost because of only one
       LOSING bet.'''

    def real_value(val):

        '''Return the real value instead of the %.'''

        return round(val/100*sum(euros), 1)

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    amount = {name: 0 for name in partecipants}

    all_bets_list = list(c.execute('''SELECT bets_id, prize FROM bets
                                   WHERE result = "Non Vincente" '''))

    for x in range(len(all_bets_list)):
        temp_id = all_bets_list[x][0]
        temp_prize = all_bets_list[x][1]

        losing_list = list(c.execute('''SELECT user FROM bets INNER JOIN
                                     matches ON matches.bets_id = bets.bets_id
                                     WHERE matches.bets_id = ? AND
                                     matches.label = "LOSING" ''', (temp_id,)))

        losing_list = [element[0] for element in losing_list]
        if len(losing_list) == 1:
            amount[losing_list[0]] += temp_prize

    db.close()

    data = [(name, amount[name]) for name in amount]
    data.sort(key=lambda x: x[1], reverse=True)

    names = [element[0] for element in data if element[1]]
    colors = [colors_dict[name] for name in names]
    euros = [element[1] for element in data if element[1]]
    n_values = len(euros)

    plt.axis('equal')
    plt.title('Euros lost for 1 person', fontsize=25, position=(0.5, 1.3))
    explode = [0.04 for x in range(n_values)]
    explode[0] = 0.07

    patches, text, autotext = plt.pie(euros, labels=names, explode=explode,
                                      colors=colors[:n_values],
                                      startangle=120, radius=1.5,
                                      autopct=real_value)

    # Change the style of the plot
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


def series():

#    partecipants = ['Nano']
    pos = {name: [] for name in partecipants}
    neg = {name: [] for name in partecipants}

    db = sqlite3.connect('bet_bot_db_stats')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    for name in partecipants:
        ref_list = list(c.execute('''SELECT ddmmyy, label FROM matches WHERE
                                  user = ? ''', (name,)))

        count_pos = 0
        dates_pos = []
        count_neg = 0
        dates_neg = []
        last_label = ''

        for x in range(len(ref_list)):
            date = ref_list[x][0]
            label = ref_list[x][1]

            if not last_label and label == 'WINNING':
                count_pos += 1
                dates_pos.append(date)

            elif not last_label and label == 'LOSING':
                count_neg += 1
                dates_neg.append(date)

            elif last_label == 'WINNING' and label == 'WINNING':
                if x == len(ref_list) - 1:
                    count_pos += 1
                    if not pos[name] or count_pos == pos[name][0][0]:
                        pass
                    elif count_pos > pos[name][0][0]:
                        pos[name] = []
                    dates_pos.append('Ongoing')
                    dates_pos.insert(0, count_pos)
                    pos[name].append(tuple(dates_pos))
                else:
                    count_pos += 1

            elif last_label == 'LOSING' and label == 'LOSING':
                if x == len(ref_list) - 1:
                    count_neg += 1
                    if not neg[name] or count_neg == neg[name][0][0]:
                        pass
                    elif count_neg > neg[name][0][0]:
                        neg[name] = []
                    dates_neg.append('Ongoing')
                    dates_neg.insert(0, count_neg)
                    neg[name].append(tuple(dates_neg))
                else:
                    count_neg += 1

            elif last_label == 'LOSING' and label == 'WINNING':
                previous_date = ref_list[x-1][0]

                if x != len(ref_list) - 1:
                    count_pos += 1
                    dates_pos.append(date)

                if not neg[name] or count_neg == neg[name][0][0]:
                    pass
                elif count_neg > neg[name][0][0]:
                    neg[name] = []
                else:
                    count_neg = 0
                    continue
                dates_neg.append(previous_date)
                dates_neg.insert(0, count_neg)
                neg[name].append(tuple(dates_neg))
                count_neg = 0
                dates_neg = []

            elif last_label == 'WINNING' and label == 'LOSING':
                previous_date = ref_list[x-1][0]

                if x != len(ref_list) - 1:
                    count_neg += 1
                    dates_neg.append(date)

                if not pos[name] or count_pos == pos[name][0][0]:
                    pass
                elif count_pos > pos[name][0][0]:
                    pos[name] = []
                else:
                    count_pos = 0
                    continue
                dates_pos.append(previous_date)
                dates_pos.insert(0, count_pos)
                pos[name].append(tuple(dates_pos))
                count_pos = 0
                dates_pos = []

            last_label = label

    db.close()

    for name in partecipants:
        pos[name] = [element for element in pos[name] if element[0] > 1]
        neg[name] = [element for element in neg[name] if element[0] > 1]

    return pos, neg


pos, neg = series()
