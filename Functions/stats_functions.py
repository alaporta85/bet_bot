import Classes as cl
import datetime
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import sqlite3
import matplotlib.image as image
import numpy as np

partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']
colors_dict = {'Zoppo': '#7fffd4',
               'Nano': '#ffff35',
               'Testazza': '#2eb82e',
               'Nonno': '#ff3300',
               'Pacco': '#028eb9'
               }


def score():

    fin_data = [(name, cl.players[name].index) for name in cl.players]
    fin_data.sort(key=lambda x: x[1], reverse=True)
    max_value = fin_data[0][1]

    names = [el[0] for el in fin_data]
    indices = [round(el[1] / max_value, 3) for el in fin_data]
    ratio = [cl.players[name].ratio for name in names]
    perc = [cl.players[name].perc for name in names]
    mean_quote = [cl.players[name].mean_quote for name in names]
    colors = [colors_dict[name] for name in names]

    bars = plt.bar(range(5), indices, 0.5, color=colors, edgecolor='black',
                   linewidth=0.5, clip_on=False)
    plt.xticks(range(5), names, fontsize=14)
    plt.ylim(0, 1.35)
    plt.box(on=None)
    plt.tick_params(axis='x', which='both', bottom=False, labelbottom=True)
    plt.tick_params(axis='y', which='both', left=False, labelleft=False)

    for i, bar in enumerate(bars):
        text = '{}\n({}%)\n{}'.format(ratio[i], perc[i], mean_quote[i])
        plt.text(bar.get_x() + bar.get_width() / 2.0, indices[i] + 0.03,
                 '{}'.format(text), ha='center', va='bottom', fontsize=10,
                 style='italic')
    for i, bar in enumerate(bars):
        text = '{}'.format(indices[i])
        plt.text(bar.get_x() + bar.get_width() / 2.0, indices[i] + 0.22,
                 '{}'.format(text), ha='center', va='bottom', fontsize=12,
                 fontweight='bold')

    plt.savefig('score.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def cake():

    """
    Return a pie chart showing the amount of euros lost because of only one
    LOSING bet.
    """

    def real_value(val):

        """Return the real value instead of the %."""

        return round(val/100*sum(euros), 1)

    data = [(name, cl.players[name].cake) for name in partecipants if
            cl.players[name].cake]
    data.sort(key=lambda x: x[1], reverse=True)

    names = [el[0] for el in data]
    euros = [el[1] for el in data]
    colors = [colors_dict[name] for name in names]

    plt.axis('equal')
    explode = [0.04] * len(names)
    explode[0] = 0.07

    patches, text, autotext = plt.pie(euros, labels=names, explode=explode,
                                      colors=colors[:len(names)],
                                      startangle=120, radius=1.5,
                                      autopct=real_value)

    # Change the style of the plot
    for patch in patches:
        patch.set_linewidth(1.5)
        patch.set_edgecolor('black')
    for x in range(len(names)):
        if x == 0:
            text[x].set_fontsize(30)
            autotext[x].set_fontsize(30)
        else:
            text[x].set_fontsize(18)
            autotext[x].set_fontsize(18)

    plt.savefig('euros_lost.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def series():

    series_pos = sorted([(name, cl.players[name].best_series) for name in
                         partecipants], key=lambda x: x[1][0], reverse=True)
    green_arrows = [g for i, g in enumerate(series_pos) if g[1] == 'Ongoing']
    names = [el[0] for el in series_pos]
    series_pos = [el[1][0] for el in series_pos]

    series_neg = [cl.players[name].worst_series for name in names]
    red_arrows = [i for i, g in enumerate(series_neg) if g[1] == 'Ongoing']
    series_neg = [el[0] for el in series_neg]
    abs_max = max((max(series_pos), max(series_neg)))

    bar_width = 0.4
    fig, ax = plt.subplots()
    fig.set_size_inches(10, 7)
    im1 = image.imread('Images/green_arrow.png')
    im2 = image.imread('Images/red_arrow.png')

    # Inserting arrows in the plot
    for i, e in enumerate(names):
        if i in green_arrows:
            from_w = i - bar_width
            to_w = i
            from_h = series_pos[i] + abs_max / 200
            to_h = series_pos[i] + abs_max / 10
            ax.imshow(im1, aspect='auto', extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

        elif i in red_arrows:
            from_w = i
            to_w = i + bar_width
            from_h = series_neg[i] + abs_max / 200
            to_h = series_neg[i] + abs_max / 10
            ax.imshow(im2, aspect='auto', extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

    plt.bar([x - bar_width / 2 for x in range(5)], series_pos, bar_width,
            color='g')

    plt.bar([x + bar_width/2 for x in range(5)], series_neg, bar_width,
            color='r')

    plt.xticks(range(5), names, fontsize=17)
    plt.yticks(fontsize=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    plt.tick_params(axis='x', bottom=False)
    plt.ylim(0, abs_max)

    plt.savefig('series.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def first_n_spots(integer, alist):

    """
    Input 'alist' is a sorted list of tuples and has the form:

        alist = [(43.5, MILAN), (40.2, JUVENTUS), (40.2, INTER), (38.7, LAZIO)]

    Return the first 'integer' elements of alist. In case there are elements
    with the same value, all those elements will be included.
    In the example above with integer = 2, function should return the first 2
    teams of the list, MILAN and JUVENTUS. But actually INTER shares the spot
    with JUVENTUS because they have the same value. That means in this case

        first_n_spots(2, alist)

    will return

        [(43.5, MILAN), (40.2, JUVENTUS), (40.2, INTER)]

    Used inside create_message.
    """

    if len(alist) <= integer:
        return alist
    else:
        if alist[integer - 1][0] != alist[integer][0]:
            return alist[:integer]
        else:
            return first_n_spots(integer + 1, alist)


def group_by_value(integer, alist):

    """
    Input 'alist' is the output of first_n_spots.
    Return a list where the elements with the same value are grouped. If

        alist = [(43.5, MILAN), (40.2, JUVENTUS), (40.2, INTER)]

    then group_by_value(alist) will return

        [(43.5, [MILAN]), (40.2, [JUVENTUS, INTER])]

    Used inside create_message.
    """

    output = first_n_spots(integer, alist)
    only_values = [element[0] for element in output]

    if len(set(only_values)) == len(output):
        new_list = [(element[0], [element[1]]) for element in output]
        return new_list
    else:
        last = output[0][0]
        temp = [output[0][1]]
        fin = []
        for x in range(1, len(output)):
            perc = output[x][0]
            team = output[x][1]
            if perc == last and x != len(output) - 1:
                temp.append(team)
            elif perc == last and x == len(output) - 1:
                temp.append(team)
                fin.append((last, temp))
                return fin
            elif perc != last and x != len(output) - 1:
                fin.append((last, temp))
                temp = [team]
                last = perc
            else:
                fin.append((last, temp))
                return fin


def create_message(integer, message1, message2, list1, list2, astring):

    """
    Fill message1 and message2, put them together and return the result.
    Used inside two functions:

        - stats_on_teams
        - stats_on_bets
        - stats_on_quotes
    """

    winning = group_by_value(integer, list1)
    losing = group_by_value(integer, list2)

    for element in winning:
        if not message1:
            message1 += '<i>WINNING {}</i>: <b>{}</b> ({}%)'.format(
                    astring, '/'.join(element[1]), element[0])
        else:
            message1 += ', <b>{}</b> ({}%)'.format('/'.join(element[1]),
                                                   element[0])

    for element in losing:
        if not message2:
            message2 += '<i>LOSING {}</i>: <b>{}</b> ({}%)'.format(
                    astring, '/'.join(element[1]), element[0])
        else:
            message2 += ', <b>{}</b> ({}%)'.format('/'.join(element[1]),
                                                   element[0])

    return message1 + '\n' + message2 + '\n\n'


def money():

    """Return a message showing the money balance."""

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    money_bet = list(c.execute('''SELECT bet_euros FROM bets WHERE
                               bet_result != "Unknown"'''))
    money_bet = sum([element[0] for element in money_bet])

    money_won = list(c.execute('''SELECT bet_prize FROM bets WHERE
                               bet_result = "WINNING"'''))
    db.close()

    if money_won:
        money_won = sum([element[0] for element in money_won])
    else:
        money_won = 0

    return '<i>Money balance</i>: <b>{}</b>\n\n'.format(money_won - money_bet)


def abs_perc():

    """Return a message showing the percentage of WINNING bets."""

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    win = 0

    raw_list = list(c.execute('''SELECT pred_label FROM predictions WHERE
                              pred_label != "Unknown"'''))
    db.close()

    for element in raw_list:
        if element[0] == 'WINNING':
            win += 1

    perc = round(win / len(raw_list) * 100, 1)

    return '<i>WINNING matches</i>: <b>{}%</b>\n\n'.format(perc)


def stats_on_teams():

    """
    Return a message showing the teams which have been guessed and failed
    the most together with their percentages.
    """

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    predictions = list(c.execute('''SELECT pred_team1, pred_team2, pred_label
                                 FROM predictions WHERE
                                 pred_label != "NULL"'''))

    db.close()

    total = {}
    winning = {}
    losing = {}

    for element in predictions:
        team1 = element[0]
        team2 = element[1]
        label = element[2]

        # Update total dict
        if team1 in total:
            total[team1] += 1
        else:
            total[team1] = 1
        if team2 in total:
            total[team2] += 1
        else:
            total[team2] = 1

        # Update team1 data
        if label == 'WINNING' and team1 in winning:
            winning[team1] += 1
        elif label == 'WINNING' and team1 not in winning:
            winning[team1] = 1
        if label == 'LOSING' and team1 in losing:
            losing[team1] += 1
        elif label == 'LOSING' and team1 not in losing:
            losing[team1] = 1

        # Update team2 data
        if label == 'WINNING' and team2 in winning:
            winning[team2] += 1
        elif label == 'WINNING' and team2 not in winning:
            winning[team2] = 1
        if label == 'LOSING' and team2 in losing:
            losing[team2] += 1
        elif label == 'LOSING' and team2 not in losing:
            losing[team2] = 1

    # Teams which played x times with x<th will not be counted
    th = 6
    winning = [(round(winning[team] / total[team] * 100, 1), team) for team in
               winning if total[team] >= th]
    winning.sort(key=lambda x: x[0], reverse=True)

    losing = [(round(losing[team] / total[team] * 100, 1), team) for team in
              losing if total[team] >= th]
    losing.sort(key=lambda x: x[0], reverse=True)

    spots = 2

    message = create_message(spots, '', '', winning, losing, 'teams')

    return message


def stats_on_bets():

    """
    Return a message showing the bets which have been guessed and failed
    the most together with their percentages.
    """

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    raw_list = list(c.execute('''SELECT pred_field, pred_label FROM
                              predictions WHERE pred_label != "NULL"'''))

    predictions = []
    for element in raw_list:
        value = list(c.execute('''SELECT field_nice_value FROM fields WHERE
                               field_id = ?''', (element[0],)))[0][0]
        predictions.append((value, element[1]))

    db.close()

    total = {}
    winning = {}
    losing = {}

    for element in predictions:
        bet = element[0]
        label = element[1]

        # Update total dict
        if bet in total:
            total[bet] += 1
        else:
            total[bet] = 1

        # Update data
        if label == 'WINNING' and bet in winning:
            winning[bet] += 1
        elif label == 'WINNING' and bet not in winning:
            winning[bet] = 1
        if label == 'LOSING' and bet in losing:
            losing[bet] += 1
        elif label == 'LOSING' and bet not in losing:
            losing[bet] = 1

    # Bets played x times with x<th will not be counted
    th = 6
    winning = [(round(winning[bet] / total[bet] * 100, 1), bet) for bet
               in winning if total[bet] >= th]
    winning.sort(key=lambda x: x[0], reverse=True)

    losing = [(round(losing[bet] / total[bet] * 100, 1), bet) for bet
              in losing if total[bet] >= th]
    losing.sort(key=lambda x: x[0], reverse=True)

    spots = 2

    message = create_message(spots, '', '', winning, losing, 'bets')

    return message


def stats_on_quotes():

    """
    Return a message showing the highest WINNING and lowest LOSING quotes
    together with the user who played them.
    """

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    winning = list(c.execute('''SELECT pred_quote, pred_user, pred_team1,
                             pred_team2, pred_rawbet FROM predictions WHERE
                             pred_label = "WINNING"'''))

    losing = list(c.execute('''SELECT pred_quote, pred_user, pred_team1,
                            pred_team2, pred_rawbet FROM predictions WHERE
                            pred_label = "LOSING"'''))
    db.close()

    winning.sort(key=lambda x: x[0], reverse=True)
    losing.sort(key=lambda x: x[0])

    grouped_winning = group_by_value(1, winning[:2])
    grouped_losing = group_by_value(1, losing[:2])

    h_quote = grouped_winning[0][0]
    l_quote = grouped_losing[0][0]

    message1 = '<i>Highest WINNING quote</i>: <b>{}</b> ({})'.format(
                                     h_quote, ', '.join(grouped_winning[0][1]))
    message2 = '<i>Lowest LOSING quote</i>: <b>{}</b> ({})'.format(
                                     l_quote, ', '.join(grouped_losing[0][1]))

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
