from Classes import stats
from itertools import groupby


def abs_perc() -> str:
    return f'<i>Pronostici vinti</i>: <b>{stats.win_preds}%</b>\n\n'


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


def money() -> str:
    return f'<i>Bilancio</i>: <b>{stats.money}€</b>\n\n'


def stats_on_bets() -> str:

    """
    Return a message showing the bets which have been guessed and failed
    the most together with their percentages.
    """
    win = stats.win_bets
    lose = stats.lose_bets

    return create_message(win_data=win, lose_data=lose,
                          category='Scommesse', first_n=2) + '\n\n'


def stats_on_combos() -> str:
    return f'<i>Combo vincenti</i>: <b>{stats.win_combos}%</b>\n\n'


def stats_on_quotes() -> str:

    quote, user = stats.highest_win_quote
    message1 = f'<i>Miglior quota vincente</i>: <b>{quote}</b> ({user})'

    quote, user = stats.lowest_los_quote
    message2 = f'<i>Peggior quota sbagliata</i>: <b>{quote}</b> ({user})'

    return f'{message1}\n{message2}\n\n'


def stats_on_teams() -> str:

    """
    Return a message showing the teams which have been guessed and failed
    the most together with their percentages.
    """
    win = stats.win_teams
    lose = stats.lose_teams

    return create_message(win_data=win, lose_data=lose,
                          category='Squadre', first_n=2) + '\n\n'
