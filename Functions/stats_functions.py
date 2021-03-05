import numpy as np
import pandas as pd
import db_functions as dbf
from itertools import groupby


def abs_perc() -> str:
    return f'<i>Pronostici vinti</i>: <b>{winning_preds_perc()}%</b>\n\n'


def create_message(win_data: list, lose_data: list,
                   category: str, first_n: int) -> str:
    win_to_print = []
    lose_to_print = []

    counter = 0
    for i, g in groupby(win_data, lambda x: x[0]):
        if counter < first_n:
            _, names = zip(*g)
            names = '/'.join(names)
            win_to_print.append((i, names))
            counter += len(names)
        else:
            counter = 0
            break

    for i, g in groupby(lose_data, lambda x: x[0]):
        if counter < first_n:
            _, names = zip(*g)
            names = '/'.join(names)
            lose_to_print.append((i, names))
            counter += len(names)
        else:
            break

    message1 = f'<i>{category} più azzeccate</i>: '
    for perc, names in win_to_print:
        message1 += f'<b>{names}</b>({perc}%), '
    message1 = message1[:-2]

    message2 = f'<i>{category} più sbagliate</i>: '
    for perc, names in lose_to_print:
        message2 += f'<b>{names}</b>({perc}%), '
    message2 = message2[:-2]

    return f'{message1}\n{message2}'


def money() -> float:

    data = dbf.db_select(table='bets',
                         columns=['euros', 'prize', 'result'],
                         where='prize IS NOT NULL')
    euros_out, euros_in, results = zip(*data)

    euros_out = sum(euros_out)
    euros_in = sum([v for i, v in enumerate(euros_in) if results[i][0] == 'W'])
    bal = round(euros_in - euros_out, 1)

    return f'<i>Bilancio</i>: <b>{bal}€</b>\n\n'


def quotes_rec() -> tuple:

    data = dbf.db_select(table='predictions',
                         columns=['user', 'quote'],
                         where='label = "WINNING"')
    data.sort(key=lambda x: x[1], reverse=True)
    quote = data[0][1]
    users = []
    for n, q in data:
        if q == quote:
            users.append(n)
        else:
            break

    win = (quote, '/'.join(users))

    data = dbf.db_select(table='predictions',
                         columns=['user', 'quote'],
                         where='label = "LOSING"')
    data.sort(key=lambda x: x[1])
    quote = data[0][1]
    users = []
    for n, q in data:
        if q == quote:
            users.append(n)
        else:
            break

    lose = (quote, '/'.join(users))

    return win, lose


def stats_on_bets() -> str:

    """
    Return a message showing the bets which have been guessed and failed
    the most together with their percentages.
    """
    win, lose = stats_on_teams_or_bets('bets')

    return create_message(win_data=win, lose_data=lose,
                          category='Scommesse', first_n=2) + '\n\n'


def stats_on_combos() -> str:
    return f'<i>Combo vincenti</i>: <b>{winning_combos_perc()}%</b>\n\n'


def stats_on_quotes() -> str:
    highest_win_quote, lowest_los_quote = quotes_rec()

    quote, user = highest_win_quote
    message1 = f'<i>Miglior quota vincente</i>: <b>{quote}</b> ({user})'

    quote, user = lowest_los_quote
    message2 = f'<i>Peggior quota sbagliata</i>: <b>{quote}</b> ({user})'

    return f'{message1}\n{message2}\n\n'


def stats_on_teams() -> str:

    """
    Return a message showing the teams which have been guessed and failed
    the most together with their percentages.
    """
    win, lose = stats_on_teams_or_bets('teams')

    return create_message(win_data=win, lose_data=lose,
                          category='Squadre', first_n=2) + '\n\n'


def stats_on_teams_or_bets(which: str) -> list:

    def for_teams(label):

        teams = dbf.db_select(table='predictions',
                              columns=['team1', 'team2'],
                              where=f'label = "{label}"')

        return pd.Series(np.array(teams).flatten()).value_counts().to_dict()

    def for_bets(label):

        bets = dbf.db_select(table='predictions',
                             columns=['bet_alias'],
                             where=f'label = "{label}"')

        return pd.Series(np.array(bets).flatten()).value_counts().to_dict()

    if which == 'teams':
        win = for_teams('WINNING')
        lose = for_teams('LOSING')

    else:
        win = for_bets('WINNING')
        lose = for_bets('LOSING')

    total = {x: (win.get(x, 0) + lose.get(x, 0)) for x in set(win) | set(lose)}

    # Teams which played x times with x<th will not be counted
    th = 6
    win = [(round(win[team] / total[team] * 100, 1), team) for team
           in win if total[team] >= th]
    win.sort(key=lambda x: x[0], reverse=True)

    lose = [(round(lose[team] / total[team] * 100, 1), team) for team
            in lose if total[team] >= th]
    lose.sort(key=lambda x: x[0], reverse=True)

    return win, lose


def winning_combos_perc() -> float:

    data = dbf.db_select(table='predictions',
                         columns=['bet_alias', 'label'],
                         where='label IS NOT NULL')
    combo = [i for i in data if '+' in i[0]]
    win = sum([1 for _, l in combo if l == 'WINNING'])

    return round(win / len(combo) * 100, 1)


def winning_preds_perc() -> float:

    tot = dbf.db_select(table='predictions', columns=['label'], where='')
    win = (np.array(tot) == 'WINNING').sum()
    return round(win / len(tot) * 100, 1)
