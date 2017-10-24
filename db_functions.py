import sqlite3


def start_db():
    db = sqlite3.connect('bet_bot_db')
    c = db.cursor()

    return db, c


def print_tables():

    '''Print tables in the database.'''

    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'")

    names = [table[0] for table in tables]

    for name in names:
        print(name)


def print_columns(table_name):

    '''Print columns'names in the database.'''

    c.execute('select * from %s' % table_name)

    names = [description[0] for description in c.description]

    for name in names:
        print(name)


def get_table_content(table_name):

    '''Return rows' content of the table.'''

    content = c.execute('''SELECT * FROM %s''' % table_name)

    return list(content)


def get_value(column, table_name, WHERE_KEY, WHERE_VALUE):

    '''Return a specific value addressed by the inputs parameters.'''

    c.execute('''SELECT %s FROM %s WHERE %s = "%s"''' % (column,
                                                         table_name,
                                                         WHERE_KEY,
                                                         WHERE_VALUE))

    res = c.fetchone()

    return res[0]


def empty_table(table_name):

    '''Delete the bet from the temporary folder.'''

    c.execute('''DELETE FROM %s''' % table_name)

    db.commit()


def insert_quote(user, quote):

    '''Update user's data with the new quote.'''

    c.execute('''INSERT INTO quotes2017 (user, quote)
    VALUES (?, ?)''', (user, quote))

    db.commit()


def delete_content(table_name, user_id):

    '''Delete the bet from the temporary folder.'''

    c.execute('''DELETE FROM %s WHERE id = %d''' % (table_name, user_id))

    db.commit()
