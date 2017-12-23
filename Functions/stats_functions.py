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

    """Return a bar plot showing the % of right bet for each partecipant."""

    # Dict to store the TOTAL number of bets played by each partecipant
    total = {name: 0 for name in partecipants}

    # Dict to store the WINNING number of bets played by each partecipant
    wins = {name: 0 for name in partecipants}

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    try:
        unknown_id = list(c.execute('''SELECT bet_id FROM bets WHERE
                                    bet_result = "Unknown" '''))[0][0]
    except IndexError:
        unknown_id = 0

    all_bets_list = list(c.execute('''SELECT pred_bet, pred_user, pred_label
                                   FROM predictions WHERE pred_bet != ?''',
                                   (unknown_id,)))

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

    """Return a bar plot showing the average quote for each partecipant."""

    total = {name: 0 for name in partecipants}
    quotes = {name: 0 for name in partecipants}

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    all_bets_list = list(c.execute('''SELECT pred_user, pred_quote FROM
                                   predictions WHERE pred_label = "WINNING"
                                   '''))
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
    plt.title('Average WINNING quote', fontsize=18)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height+0.1,
                 '{:.2f}'.format(height), ha='center', va='bottom',
                 fontsize=16)

    plt.savefig('aver_quote.png', dpi=120, bbox_inches='tight')
    plt.gcf().clear()


def records():

    """
    Return two messages: one for the WINNING bet with the highest quote
    and one for the LOSING bet with the lowest quote.
    """

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    try:
        unknown_id = list(c.execute('''SELECT bet_id FROM bets WHERE
                                    bet_result = "Unknown" '''))[0][0]
    except IndexError:
        unknown_id = 0

    all_bets_list = list(c.execute('''SELECT pred_user, pred_team1, pred_team2,
                                   pred_rawbet, pred_quote, pred_label FROM
                                   predictions WHERE pred_bet != ?''',
                                   (unknown_id,)))
    db.close()

    # Initialize parameters
    h_name = ''
    h_team1 = ''
    h_team2 = ''
    h_rawbet = ''
    h_quote = 0

    l_name = ''
    l_team1 = ''
    l_team2 = ''
    l_rawbet = ''
    l_quote = 5000

    for element in all_bets_list:
        temp_name = element[0]
        temp_team1 = element[1]
        temp_team2 = element[2]
        temp_rawbet = element[3]
        temp_quote = element[4]
        temp_label = element[5]

        if temp_label == 'WINNING':
            if temp_quote > h_quote:
                h_name = temp_name
                h_team1 = temp_team1
                h_team2 = temp_team2
                h_rawbet = temp_rawbet
                h_quote = temp_quote
        else:
            if temp_quote < l_quote:
                l_name = temp_name
                l_team1 = temp_team1
                l_team2 = temp_team2
                l_rawbet = temp_rawbet
                l_quote = temp_quote

    h_message = ('Highest WINNING quote is ' +
                 '{} from:\n\n{}\n{} - {}\n{}'.format(h_quote, h_name,
                                                      h_team1, h_team2,
                                                      h_rawbet))
    l_message = ('Lowest LOSING quote is ' +
                 '{} from:\n\n{}\n{} - {}\n{}'.format(l_quote, l_name,
                                                      l_team1, l_team2,
                                                      l_rawbet))

    return h_message, l_message


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

        losing_list = list(c.execute('''SELECT pred_user FROM bets INNER JOIN
                                     predictions ON pred_bet = bet_id WHERE
                                     pred_bet = ? AND pred_label = "LOSING"''',
                                     (temp_id,)))

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
        unknown_id = 0

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
    abs_max = max([max(records_pos), max(records_neg)])

    bar_width = 0.4
    fig, ax = plt.subplots()
    im = image.imread('Images/green_arrow.png')
    height, width = im.shape[:2]
    a_ratio = height/width

    # Inserting arrows in the plot
    for person in to_plot_pos_list:
        if person[3] == 'Ongoing':
            from_w = to_plot_pos_list.index(person) - bar_width + 0.06
            to_w = to_plot_pos_list.index(person) - 0.06
            from_h = person[1] + 0.02
            to_h = person[1] + 0.2 + 0.28*a_ratio
            ax.imshow(im, aspect=a_ratio, extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

    for person in to_plot_neg_list:
        if person[3] == 'Ongoing':
            from_w = to_plot_neg_list.index(person) + 0.06
            to_w = to_plot_neg_list.index(person) + bar_width - 0.06
            from_h = person[1] + 0.02
            to_h = person[1] + 0.2 + 0.28*a_ratio
            ax.imshow(im, aspect='auto', extent=(from_w, to_w, from_h, to_h),
                      zorder=-1)

    plt.bar([x - bar_width/2 for x in range(5)], records_pos,
            bar_width, color='g', label='Positive')

    plt.bar([x + bar_width/2 for x in range(5)], records_neg,
            bar_width, color='r', label='Negative')

    plt.xticks(range(5), names, fontsize=14)
    plt.title('Series', fontsize=18)
    plt.ylim(1)
    plt.yticks(range(abs_max + 1))

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
