import sqlite3
import datetime
import re


def todays_date():

    """
    Return a tuple containing the date of the day and the time as integers.
    If command is sent on May 16th, 1985 at 15:48 the output will be:

        (19850516, 1548)
    """

    date_time = str(datetime.datetime.now())

    date = date_time.split(' ')[0]
    time = date_time.split(' ')[1]

    date = '{}/{}/{}'.format(date.split('-')[0],
                             date.split('-')[1],
                             date.split('-')[2])

    date = int(date.replace('/', ''))
    time = int(time.replace(':', '')[:4])

    return date, time


def start_db():

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    return db, c


def get_table_content(table_name):

    """Return rows' content of the table."""

    db, c = start_db()

    content = list(c.execute('''SELECT * FROM {}'''.format(table_name)))

    db.close()

    return content


def get_value(column, table_name, WHERE_KEY, WHERE_VALUE):

    """Return a specific value addressed by the inputs parameters."""

    db, c = start_db()

    res = list(c.execute('''SELECT {} FROM {} WHERE {} = "{}"'''.format(
            column, table_name, WHERE_KEY, WHERE_VALUE)))

    db.close()

    res = [element[0] for element in res]

    try:
        return res[0]
    except TypeError:
        return 0
    except IndexError:
        return 0


def empty_table(table_name):

    """Delete the bet from the temporary folder."""

    db, c = start_db()

    c.execute('''DELETE FROM {}'''.format(table_name))

    db.commit()
    db.close()


def check_before_play(db, c):

    """
    Return all the matches in the 'Pending' bet which have been played
    already or started.
    """

    invalid_matches = []

    time_now = datetime.datetime.now()

    bet_id = list(c.execute('''SELECT bet_id FROM bets WHERE
                            bet_status = "Pending" '''))[0][0]

    matches = list(c.execute('''SELECT pred_id, pred_user, pred_team1,
                             pred_team2, pred_date FROM bets INNER
                             JOIN predictions on pred_bet = bet_id WHERE
                             bet_id = ?''', (bet_id,)))

    for match in matches:
        match_date = datetime.datetime.strptime(match[4], '%Y-%m-%d %H:%M:%S')
        if match_date < time_now:
            invalid_matches.append(match[1:])
            c.execute('''DELETE FROM predictions WHERE pred_id = ?''',
                      (match[0],))
            db.commit()

    return invalid_matches
