import sqlite3
import datetime
#from Functions import logging as log


def todays_date():

    date_time = str(datetime.datetime.now())

    date = date_time.split(' ')[0]
    time = date_time.split(' ')[1]

    date = '{}/{}/{}'.format(date.split('-')[0],
                             date.split('-')[1],
                             date.split('-')[2])

    time = int(time.replace(':', '')[:4])

    return date, time


def start_db():

    db = sqlite3.connect('bet_bot_db_stats 12.55.43')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    return db, c


def print_tables():

    '''Print tables in the database.'''

    db, c = start_db()

    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'")

    names = [table[0] for table in tables]

    db.close()

    for name in names:
        print(name)


def print_columns(table_name):

    '''Print columns'names in the database.'''

    db, c = start_db()

    c.execute('SELECT * FROM {}'.format(table_name))

    names = [description[0] for description in c.description]

    db.close()

    for name in names:
        print(name)


def get_table_content(table_name):

    '''Return rows' content of the table.'''

    db, c = start_db()

    content = list(c.execute('''SELECT * FROM {}'''.format(table_name)))

    db.close()

    return content


def get_value(column, table_name, WHERE_KEY, WHERE_VALUE):

    '''Return a specific value addressed by the inputs parameters.'''

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

    '''Delete the bet from the temporary folder.'''

    db, c = start_db()

    c.execute('''DELETE FROM {}'''.format(table_name))

    db.commit()
    db.close()


def check_before_play(db, c):

    '''Return all the matches in the 'Pending' bets which have been played
       already or started.'''

    matches = []
    invalid_matches = []

    date, time = todays_date()
    date = int(date.replace('/', ''))

    bets_id_list = list(c.execute('''SELECT bets_id FROM bets WHERE
                                  status = "Pending" '''))
    bets_id_list = [element[0] for element in bets_id_list]

    for bets_id in bets_id_list:
        matches = list(c.execute('''SELECT matches_id, user, team1, team2,
                                 yymmdd_match, hhmm FROM bets INNER JOIN
                                 matches on matches.bets_id = bets.bets_id
                                 WHERE bets.bets_id = ?''', (bets_id,)))

    for match in matches:
        match_date = int(match[4].replace('/', ''))
        match_time = int(match[5].replace(':', ''))
        if match_date < date or (match_date == date and match_time < time):
            invalid_matches.append(match[1:])
            c.execute('''DELETE FROM matches WHERE matches_id = ?''',
                      (match[0],))
            db.commit()

    return invalid_matches
