from Functions import db_functions as dbf
import Classes as cl
import datetime
from itertools import groupby
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import sqlite3

db, c = dbf.start_db()
colors_dict = list(c.execute('''SELECT person, color FROM colors'''))
colors_dict = {el[0]: el[1] for el in colors_dict}
partecipants = [el for el in colors_dict]
db.close()


def create_message(integer, list1, list2, astring):
    win_to_print = []
    lose_to_print = []

    counter = 0
    for i, g in groupby(list1, lambda x: x[0]):
        if counter < integer:
            lst = list(g)
            teams = '/'.join([el[1] for el in lst])
            win_to_print.append((i, teams))
            counter += len(lst)
        else:
            counter = 0
            break

    for i, g in groupby(list2, lambda x: x[0]):
        if counter < integer:
            lst = list(g)
            teams = '/'.join([el[1] for el in lst])
            lose_to_print.append((i, teams))
            counter += len(lst)
        else:
            break

    message1 = '<i>WINNING {}</i>: '.format(astring)
    message2 = '<i>LOSING {}</i>: '.format(astring)

    for perc, teams in win_to_print:
        message1 += '<b>{}</b>({}%), '.format(teams, perc)
    message1 = message1[:-2]

    for perc, teams in lose_to_print:
        message2 += '<b>{}</b>({}%), '.format(teams, perc)
    message2 = message2[:-2]

    return '{}\n{}'.format(message1, message2)


def money():

    """Return a message showing the money balance."""

    return '<i>Money balance</i>: <b>{}</b>\n\n'.format(cl.stats.money_bal())


def abs_perc():

    """Return a message showing the percentage of WINNING bets."""

    return '<i>WINNING matches</i>: <b>{}%</b>\n\n'.format(cl.stats.win_preds)


def stats_on_teams():

    """
    Return a message showing the teams which have been guessed and failed
    the most together with their percentages.
    """
    win = cl.stats.win_teams
    lose = cl.stats.lose_teams

    return create_message(2, win, lose, 'teams') + '\n\n'


def stats_on_bets():

    """
    Return a message showing the bets which have been guessed and failed
    the most together with their percentages.
    """
    win = cl.stats.win_bets
    lose = cl.stats.lose_bets

    return create_message(2, win, lose, 'bets') + '\n\n'


def stats_on_quotes():

    """
    Return a message showing the highest WINNING and lowest LOSING quotes
    together with the user who played them.
    """

    message1 = '<i>Highest WINNING quote</i>: <b>{}</b> ({})'
    message2 = '<i>Lowest LOSING quote</i>: <b>{}</b> ({})'

    quote, user = cl.stats.highest_win_quote
    message1 = message1.format(quote, user)

    quote, user = cl.stats.lowest_los_quote
    message2 = message2.format(quote, user)

    return message1 + '\n' + message2 + '\n\n'


def stats_on_combos():

    """Return a message showing the percentage of WINNING combos."""

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    combos = list(c.execute('''SELECT pred_rawbet, pred_label FROM predictions
                             WHERE pred_label != "NULL"'''))
    db.close()

    combos = [element for element in combos if '+' in element[0]]
    win = 0

    for element in combos:
        if element[1] == 'WINNING':
            win += 1

    perc = round(win / len(combos) * 100, 1)

    return '<i>WINNING combos</i>: <b>{}%</b>\n\n'.format(perc)


def stats_of_the_month():

    """Best and Worst of every month based on the index."""

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
              'Oct', 'Nov', 'Dec', ]

    dict_win = {name: [] for name in partecipants}
    dict_lose = {name: [] for name in partecipants}

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_preds = list(c.execute('''SELECT pred_user, pred_date, pred_quote,
                               pred_label FROM predictions WHERE
                               pred_label != "NULL" '''))
    db.close()

    for x in range(1, 13):
        indexes = {name: 0 for name in partecipants}
        preds_month = [el for el in all_preds if int(str(el[1])[4:6]) == x]
        if preds_month:
            highest = 0
            lowest = 100000
            year = '\'' + str(preds_month[0][1])[2:4]
            date = months[x - 1] + ' {}'.format(year)
            for name in partecipants:
                index = 1
                preds_name = [el for el in preds_month if el[0] == name]
                for pred in preds_name:
                    if pred[3] == 'WINNING':
                        index *= pred[2]
                index /= len(preds_name)
                if index > highest:
                    highest = index
                if index < lowest:
                    lowest = index
                indexes[name] = index
            for name in indexes:
                if indexes[name] == highest:
                    dict_win[name].append((round(indexes[name], 1), date))
                if indexes[name] == lowest:
                    dict_lose[name].append((round(indexes[name], 1), date))

    win = [(name, len(dict_win[name])) for name in partecipants]
    win.sort(key=lambda x: x[1], reverse=True)

    names = [el[0] for el in win]
    lose = [(name, len(dict_lose[name])) for name in names]

    abs_max = max(max([el[1] for el in win]), max([el[1] for el in lose]))

    fig, ax = plt.subplots()
    fig.set_size_inches(13, 6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    bar_width = 0.45
    bars1 = plt.bar([x - bar_width/2 for x in range(5)], [el[1] for el in win],
            bar_width, color='g')
    bars2 = plt.bar([x + bar_width / 2 for x in range(5)],
                    [el[1] for el in lose], bar_width, color='r')

    plt.xticks(range(5), names, fontsize=25)
    plt.yticks(range(abs_max + 1), fontsize=16)
    plt.tick_params(axis='x', which='both', bottom='off', labelbottom='on')

    for x in range(5):
        dict_win[names[x]].sort(key=lambda x: int(x[1][5:]))
        dict_win[names[x]].reverse()
        message = ''
        for bet in dict_win[names[x]]:
            message += bet[1] + '\n'
        message = message[:-1]

        plt.text(bars1[x].get_x() + bars1[x].get_width() / 2,
                 bars1[x].get_height() + 0.05, message, ha='center',
                 va='bottom', fontsize=15)

    for x in range(5):
        dict_lose[names[x]].sort(key=lambda x: int(x[1][5:]))
        dict_lose[names[x]].reverse()
        message = ''
        for bet in dict_lose[names[x]]:
            message += bet[1] + '\n'
        message = message[:-1]

        plt.text(bars2[x].get_x() + bars2[x].get_width() / 2,
                 bars2[x].get_height() + 0.05, message, ha='center',
                 va='bottom', fontsize=15)

    plt.savefig('sotm.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def stats_on_weekday():

    """Return a message showing:

        1. The percentage of WINNING matches on Saturday
        2. The percentage of WINNING matches on Sunday
        3. The percentage of WINNING matches in SERIE A on Saturday
        4. The percentage of WINNING matches in OTHERS on Saturday
    """

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_preds = list(c.execute('''SELECT pred_user, pred_date, pred_label,
                               pred_league FROM predictions WHERE
                               pred_label != "NULL" '''))

    tot_sat = 0
    win_sat = 0
    tot_sun = 0
    win_sun = 0
    leagues_tot = {'SERIE A': 0, 'OTHERS': 0}
    leagues_win = {'SERIE A': 0, 'OTHERS': 0}

    for pred in all_preds:
        year = int(str(pred[1])[:4])
        month = int(str(pred[1])[4:6])
        day = int(str(pred[1])[6:])
        label = pred[2]
        league = list(c.execute('''SELECT league_name FROM leagues WHERE
                                league_id = {}'''.format(pred[3])))[0][0]
        if league != 'SERIE A':
            league = 'OTHERS'

        weekday = datetime.date(year, month, day).weekday()

        if weekday == 5:
            tot_sat += 1
            leagues_tot[league] += 1
            if label == 'WINNING':
                win_sat += 1
                leagues_win[league] += 1
        elif weekday == 6:
            tot_sun += 1
            if label == 'WINNING':
                win_sun += 1

    perc_sat = round(win_sat / tot_sat * 100, 1)
    perc_sun = round(win_sun / tot_sun * 100, 1)
    perc_seriea = round(leagues_win['SERIE A'] / leagues_tot['SERIE A'] * 100,
                        1)
    perc_others = round(leagues_win['OTHERS'] / leagues_tot['OTHERS'] * 100, 1)

    message = ('<i>Matches won/played on Saturday</i>: {}/{} (<b>{}%</b>)\n'
               '<i>Matches won/played on Sunday</i>: {}/{} (<b>{}%</b>)\n'
               '<i>Matches won/played in SERIE A on Saturday</i>: {}/{} '
               '(<b>{}%</b>)\n'
               '<i>Matches won/played in OTHERS on Saturday</i>: {}/{} '
               '(<b>{}%</b>)\n\n'
               .format(win_sat, tot_sat, perc_sat, win_sun, tot_sun, perc_sun,
                       leagues_win['SERIE A'], leagues_tot['SERIE A'],
                       perc_seriea, leagues_win['OTHERS'],
                       leagues_tot['OTHERS'], perc_others))

    return message
