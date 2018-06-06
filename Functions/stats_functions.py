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

    return '<i>Money balance</i>: <b>{}</b>\n\n'.format(cl.stats.money)


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

    return '<i>WINNING combos</i>: <b>{}%</b>\n\n'.format(cl.stats.win_combos)
