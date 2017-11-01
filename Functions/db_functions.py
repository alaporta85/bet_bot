import sqlite3


def start_db():

    db = sqlite3.connect('bet_bot_db')
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

    c.execute('''SELECT {} FROM {} WHERE {} = "{}"'''.format(column,
                                                             table_name,
                                                             WHERE_KEY,
                                                             WHERE_VALUE))

    res = c.fetchone()

    db.close()

    try:
        return res[0]
    except TypeError:
        return 0


def empty_table(table_name):

    '''Delete the bet from the temporary folder.'''

    db, c = start_db()

    c.execute('''DELETE FROM {}'''.format(table_name))

    db.commit()
    db.close()


def insert_quote(user, quote):

    '''Update user's data with the new quote.'''

    db, c = start_db()

    c.execute('''INSERT INTO quotes2017 (user, quote)
    VALUES (?, ?)''', (user, quote))

    db.commit()
    db.close()


def delete_content(table_name, team1):

    '''Delete the bet from the temporary folder.'''

    db, c = start_db()

    c.execute('''DELETE FROM {} WHERE team1 = {}'''.format(table_name, team1))

    db.commit()
    db.close()
