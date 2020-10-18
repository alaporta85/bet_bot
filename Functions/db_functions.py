import sqlite3
import datetime
import pandas as pd
from nltk.metrics.distance import jaccard_distance
from nltk.util import ngrams
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def check_before_play(bet_id):

    """
    Return all the matches in the 'Pending' bet which have been played
    already or started.

    :param bet_id: int


    :return: list of tuples, (user, datetime, team1, team2)
    """

    invalid_matches = []

    time_now = datetime.datetime.now()

    matches = db_select(
            table='bets INNER JOIN predictions on pred_bet = bet_id',
            columns=['pred_id', 'pred_user', 'pred_date', 'pred_team1',
                        'pred_team2'],
            where='bet_id = {}'.format(bet_id))

    for match in matches:
        match_date = datetime.datetime.strptime(match[2], '%Y-%m-%d %H:%M:%S')
        if match_date < time_now:
            invalid_matches.append(match[1:])
            db_delete(
                    table='predictions',
                    where='pred_id = {}'.format(match[0]))

    return invalid_matches


def empty_table(table):

    """
    Delete everything from table.

    :param table: str

    """

    db, c = start_db()

    query = f'DELETE FROM {table}'

    c.execute(query)
    db.commit()
    db.close()


def db_delete(table, where):

    """
    Remove entry from database.

    :param table: str
    :param where: str

    """

    db, c = start_db()

    query = f'DELETE FROM {table} WHERE {where}'

    c.execute(query)
    db.commit()
    db.close()


def db_insert(table, columns, values):

    """
    Insert a new row in the table.

    :param table: str, name of the table
    :param columns: list, each element of the list is a column of the table.
    :param values: list, values of the corresponding columns

    """

    db, c = start_db()

    cols = ', '.join(columns)
    vals = ', '.join([f'"{v}"' for v in values])
    query = f'INSERT INTO {table} ({cols}) VALUES ({vals})'

    c.execute(query)
    db.commit()
    db.close()


def db_select(table, columns, where=None):

    """
    Return content from a specific table of the database.

    :param table: str, name of the table
    :param columns: list, each element of the list is a column of the table.
    :param where: str, condition

    :return: list of tuples or list of elements

    """

    db, c = start_db()

    cols = ', '.join(columns)
    if where:
        query = f'SELECT {cols} FROM {table} WHERE {where}'
    else:
        query = f'SELECT {cols} FROM {table}'

    content = list(c.execute(query))
    db.close()

    if len(columns) == 1 and columns[0] != '*':
        content = [el[0] for el in content if el[0]]

    return content


def db_update(table, columns, values, where):

    """
    Update values in the table.

    :param table: str, name of the table
    :param columns: list, each element of the list is a column of the table.
    :param values: list, values of the corresponding columns
    :param where: str, condition

    """

    db, c = start_db()

    vals = ', '.join([f'{c}="{v}"' for c, v in zip(columns, values)])
    query = f'UPDATE {table} SET {vals} WHERE {where}'

    c.execute(query)
    db.commit()
    db.close()


def jaccard_result(input_option, all_options, ngrm):

    """
    Trova il valore esatto corrispondente a quello inserito dall'user.

    :param input_option: str

    :param all_options: list of str

    :param ngrm: int, lunghezza degli ngrammi


    :return jac_res: str

    """

    dist = 1
    tri_guess = set(ngrams(input_option, ngrm))
    jac_res = ''

    for opt in all_options:
        p = opt.replace(' ', '')
        trit = set(ngrams(p, ngrm))
        jd = jaccard_distance(tri_guess, trit)
        if not jd:
            return opt
        elif jd < dist:
            dist = jd
            jac_res = opt

    if not jac_res and ngrm > 2:
        return jaccard_result(input_option, all_options, ngrm - 1)

    elif not jac_res and ngrm == 2:
        return False

    return jac_res


def select_team(input_team):

    if '*' in input_team:
        input_team = input_team[1:]

    try:
        team_name = db_select(
                table='teams_short',
                columns=['team_short_name'],
                where='team_short_value = "{}"'.format(input_team))[0]

    except IndexError:

        team_name = jaccard_result(input_team,
                                   db_select(
                                           table='teams',
                                           columns=['team_name']), 3)

    return team_name


def start_db():

    db = sqlite3.connect('extended_db.db')
    c = db.cursor()

    return db, c
