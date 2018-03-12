import datetime
import matplotlib.pyplot as plt
import sqlite3
import matplotlib.image as image

partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']
colors_dict = {'Zoppo': '#7fffd4',
               'Nano': '#ffff35',
               'Testazza': '#2eb82e',
               'Nonno': '#ff3300',
               'Pacco': '#028eb9'
               }


def score():

    fin_data = []

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    try:
        query = '''SELECT bet_id FROM bets WHERE bet_result = "Unknown"'''
        unknown_ids = [element[0] for element in list(c.execute(query))]
    except IndexError:
        unknown_ids = [0]

    for name in partecipants:

        fin_quote = 1

        query = ('''SELECT pred_quote, pred_label FROM predictions WHERE
                 pred_bet NOT IN ({}) AND pred_user = "{}"'''.format(
                 ', '.join('?' * len(unknown_ids)), name))

        all_quotes = list(c.execute(query, unknown_ids))
        win_quotes = [element[0] for element in all_quotes if
                      element[1] == 'WINNING']

        for quote in win_quotes:
            fin_quote *= quote

        fin_data.append((name, fin_quote / len(all_quotes)))

    fin_data.sort(key=lambda x: x[1], reverse=True)
    norm_factor = fin_data[0][1]
    scores_norm = [round(element[1]/norm_factor, 3) for element in fin_data]

    db.close()

    names = [element[0] for element in fin_data]
    colors = [colors_dict[name] for name in names]

    bars = plt.bar(range(5), scores_norm, 0.5, color=colors)
    plt.xticks(range(5), names, fontsize=14)
    plt.ylabel('Index of success', fontsize=16)
    plt.ylim(0, 1.13)
    plt.tick_params(axis='x',
                    which='both',  # both major and minor ticks are affected
                    bottom='off',  # ticks along the bottom edge are off
                    labelbottom='on'
                    )
    plt.tick_params(axis='y',
                    which='both',  # both major and minor ticks are affected
                    left='off',  # ticks along the bottom edge are off
                    labelleft='off'
                    )

    count = 0
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2.0,
                 scores_norm[count] + 0.03,
                 '{}'.format(scores_norm[count]), ha='center', va='bottom',
                 fontsize=12)
        count += 1

    plt.savefig('score.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def aver_quote():

    """Return a bar plot showing the average quote for each partecipant."""

    total = {name: 0 for name in partecipants}
    quotes = {name: 0 for name in partecipants}

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    query = ('''SELECT pred_user, pred_quote FROM predictions WHERE
             pred_label = "WINNING"''')

    all_bets_list = list(c.execute(query))
    db.close()

    for user, quote in all_bets_list:
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
    plt.title('Average WINNING quote', fontsize=18)

    plt.tick_params(axis='x',
                    which='both',  # both major and minor ticks are affected
                    bottom='off',  # ticks along the bottom edge are off
                    labelbottom='on'
                    )
    plt.tick_params(axis='y',
                    which='both',  # both major and minor ticks are affected
                    left='off',  # ticks along the bottom edge are off
                    labelleft='off'
                    )

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height+0.1,
                 '{:.2f}'.format(height), ha='center', va='bottom',
                 fontsize=16)

    plt.savefig('aver_quote.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def euros_lost_for_one_bet():

    """
    Return a pie chart showing the amount of euros lost because of only one
    LOSING bet.
    """

    def real_value(val):

        """Return the real value instead of the %."""

        return round(val/100*sum(euros), 1)

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    amount = {name: 0 for name in partecipants}

    all_bets_list = list(c.execute('''SELECT bet_id, bet_prize FROM bets
                                   WHERE bet_result = "LOSING" '''))

    for x in range(len(all_bets_list)):
        temp_id = all_bets_list[x][0]
        temp_prize = all_bets_list[x][1]

        losing_list = list(c.execute('''SELECT pred_user, pred_quote FROM bets
                                     INNER JOIN predictions ON
                                     pred_bet = bet_id WHERE pred_bet = ? AND
                                     pred_label = "LOSING"''', (temp_id,)))

        if len(losing_list) == 1:
            amount[losing_list[0][0]] += temp_prize/losing_list[0][1]

    db.close()

    data = [(name, amount[name]) for name in amount]
    data.sort(key=lambda x: x[1], reverse=True)

    names = [element[0] for element in data if element[1]]
    colors = [colors_dict[name] for name in names]
    euros = [element[1] for element in data if element[1]]
    n_values = len(euros)

    plt.axis('equal')
    plt.title('Euros lost for 1 person', fontsize=25, position=(0.5, 1.3))
    explode = [0.04] * n_values
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


def create_series(c, name, series_pos, series_neg):

    """
    Fill the dicts series_pos and series_neg with the elements representing
    the series for each player.
    """

    try:
        unknown_ids = list(c.execute('''SELECT bet_id FROM bets WHERE
                                     bet_result = "Unknown" '''))
        unknown_ids = [element[0] for element in unknown_ids]

    except IndexError:
        unknown_ids = []

    query = ('''SELECT pred_date, pred_label FROM predictions WHERE
             pred_user = "{}" AND pred_bet NOT IN ({})'''.format(
		    name, ', '.join('?' * len(unknown_ids))))
    ref_list = list(c.execute(query, unknown_ids))

    count_pos = 0
    dates_pos = []
    count_neg = 0
    dates_neg = []
    last_label = ''

    for x in range(len(ref_list)):
        date = ref_list[x][0]
        label = ref_list[x][1]

        # If it is the first element we just update the count and append it
        if not last_label and label == 'WINNING':
            count_pos += 1
            dates_pos.append(date)

        elif not last_label and label == 'LOSING':
            count_neg += 1
            dates_neg.append(date)

        # If the current label is the same as the previous one we distinguish
        # two cases
        elif last_label == 'WINNING' and label == 'WINNING':

            # 1. It is the last element in the list. In this case we "mark" it
            # as "Ongoing" and append it to series_pos
            if x == len(ref_list) - 1:
                count_pos += 1
                if (not series_pos[name] or
                   count_pos == series_pos[name][0][0]):
                    pass
                elif count_pos > series_pos[name][0][0]:
                    series_pos[name] = []
                dates_pos.append('Ongoing')
                dates_pos.insert(0, count_pos)
                series_pos[name].append(dates_pos)

            # 2. It is not the last element in list. Simply increase the
            # counter
            else:
                count_pos += 1

        # Same as above
        elif last_label == 'LOSING' and label == 'LOSING':
            if x == len(ref_list) - 1:
                count_neg += 1
                if (not series_neg[name] or
                   count_neg == series_neg[name][0][0]):
                    pass
                elif count_neg > series_neg[name][0][0]:
                    series_neg[name] = []
                dates_neg.append('Ongoing')
                dates_neg.insert(0, count_neg)
                series_neg[name].append(dates_neg)
            else:
                count_neg += 1

        # If the current label is diffent from the last one
        elif last_label == 'LOSING' and label == 'WINNING':

            # Store the date of the previous element
            previous_date = ref_list[x-1][0]

            # If not last element, start the counter for the new serie and
            # append the date
            if x != len(ref_list) - 1:
                count_pos += 1
                dates_pos.append(date)

            # If no element for this person is present or the value is equal
            # to the one already present we just go ahead
            if not series_neg[name] or count_neg == series_neg[name][0][0]:
                pass
            # If the record is higher we empty the list
            elif count_neg > series_neg[name][0][0]:
                series_neg[name] = []
            # If it is lower we set the counter to 0 again and go to the next
            # element in the loop
            else:
                count_neg = 0
                last_label = label
                dates_neg = []
                continue

            dates_neg.append(previous_date)
            dates_neg.insert(0, count_neg)
            series_neg[name].append(dates_neg)
            count_neg = 0
            dates_neg = []

        # Same as above
        elif last_label == 'WINNING' and label == 'LOSING':
            previous_date = ref_list[x-1][0]

            if x != len(ref_list) - 1:
                count_neg += 1
                dates_neg.append(date)

            if not series_pos[name] or count_pos == series_pos[name][0][0]:
                pass
            elif count_pos > series_pos[name][0][0]:
                series_pos[name] = []
            else:
                count_pos = 0
                last_label = label
                dates_pos = []
                continue
            dates_pos.append(previous_date)
            dates_pos.insert(0, count_pos)
            series_pos[name].append(dates_pos)
            count_pos = 0
            dates_pos = []

        last_label = label


def series():

    series_pos = {name: [] for name in partecipants}
    series_neg = {name: [] for name in partecipants}

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    for name in partecipants:
        create_series(c, name, series_pos, series_neg)

    db.close()

    # Delete all the series only 1 match long
    for name in partecipants:
        series_pos[name] = [element for element in series_pos[name]
                            if element[0] > 1]
        series_neg[name] = [element for element in series_neg[name]
                            if element[0] > 1]

    # Here we divide the series in two groups: the longest ones which go inside
    # the to_plot lists and the ones which are not yet the longest but still
    # ongoing which will go inside the coming list
    to_plot_pos = {name: (name, 0, 0, 0) for name in partecipants}
    to_plot_neg = {name: (name, 0, 0, 0) for name in partecipants}
    coming_pos = []
    coming_neg = []

    for name in partecipants:
        try:
            record = max([serie[0] for serie in series_pos[name]])
            for serie in series_pos[name]:
                if serie[0] == record:
                    to_plot_pos[name] = tuple([name] + serie)
                elif serie[0] < record and serie[2] == 'Ongoing':
                    coming_pos.append(tuple([name] + serie))
        except ValueError:
            pass

        try:
            record = max([serie[0] for serie in series_neg[name]])
            for serie in series_neg[name]:
                if serie[0] == record:
                    to_plot_neg[name] = tuple([name] + serie)
                elif serie[0] < record and serie[2] == 'Ongoing':
                    coming_neg.append(tuple([name] + serie))
        except ValueError:
            pass

    if len(coming_pos) > 1:
        coming_pos.sort(key=lambda x: x[1], reverse=True)
    if len(coming_neg) > 1:
        coming_neg.sort(key=lambda x: x[1], reverse=True)

    # From the dicts to_plot_pos and to_plot_neg we create two lists
    # containing the same data but sorted
    to_plot_pos_list = [to_plot_pos[name] for name in to_plot_pos]
    to_plot_pos_list.sort(key=lambda x: x[1], reverse=True)
    to_plot_neg_list = [to_plot_neg[element[0]] for element
                        in to_plot_pos_list]

    names = []
    records_pos = []
    records_neg = []
    for x in range(5):
        names.append(to_plot_pos_list[x][0])
        records_pos.append(to_plot_pos_list[x][1])
        records_neg.append(to_plot_neg_list[x][1])

    highest_pos = max(records_pos)
    highest_neg = max(records_neg)
    abs_max = max([highest_pos, highest_neg])

    bar_width = 0.4
    fig, ax = plt.subplots()
    fig.set_size_inches(10, 7)
    im1 = image.imread('Images/green_arrow.png')
    im2 = image.imread('Images/red_arrow.png')

    # Inserting arrows in the plot
    for person in to_plot_pos_list:
        if person[3] == 'Ongoing':
            from_w = to_plot_pos_list.index(person) - bar_width
            to_w = to_plot_pos_list.index(person)
            from_h = person[1] + abs_max/200
            to_h = person[1] + abs_max/10
            ax.imshow(im1, aspect=1, extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

    for person in to_plot_neg_list:
        if person[3] == 'Ongoing':
            from_w = to_plot_neg_list.index(person)
            to_w = to_plot_neg_list.index(person) + bar_width
            from_h = person[1] + abs_max/200
            to_h = person[1] + abs_max/10
            ax.imshow(im2, aspect='auto', extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

    plt.bar([x - bar_width/2 for x in range(5)], records_pos,
            bar_width, color='g')

    plt.bar([x + bar_width/2 for x in range(5)], records_neg,
            bar_width, color='r')

    plt.xticks(range(5), names, fontsize=17)
    plt.title('Series', fontsize=22)
    plt.ylim(1)
    plt.yticks(range(abs_max + 1), fontsize=13)

    # Inserting text on the top-right
    message = ''
    th = 2
    for element in coming_pos:
        if element[1] + th >= highest_pos:
            text = '- {} {}(P)\n'.format(element[0], element[1])
            message += text
    for element in coming_neg:
        if element[1] + th >= highest_neg:
            text = '- {} {}(N)\n'.format(element[0], element[1])
            message += text
    ax.annotate(message, xy=(1, 1), xycoords='axes fraction', fontsize=16,
                xytext=(-150, -5), textcoords='offset points', ha='left',
                va='top')

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
