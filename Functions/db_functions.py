import sqlite3
import datetime
import pandas as pd
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def start_db():

    db = sqlite3.connect('extended_db')
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    return db, c


def db_select(table, columns_in=None, columns_out=None,
              where=None, dataframe=False):

    """Return rows' content of the table."""

    db, c = start_db()

    if where:
        cursor = c.execute('''SELECT * FROM {} WHERE {}'''.format(table,
                                                                  where))
    else:
        cursor = c.execute('''SELECT * FROM {}'''.format(table))

    cols = [el[0] for el in cursor.description]

    df = pd.DataFrame(list(cursor), columns=cols)
    db.close()

    if not len(df):
        return []

    if columns_in:
        cols = [el for el in cols if el in columns_in]
        df = df[cols]

    elif columns_out:
        cols = [el for el in cols if el not in columns_out]
        df = df[cols]

    if dataframe:
        return df
    else:
        if len(cols) == 1:
            res = [df.loc[i, cols[0]] for i in range(len(df))]
            res = sorted(set(res), key=lambda x: res.index(x))
            return res
        else:
            res = [tuple(df.iloc[i]) for i in range(len(df))]
            return res


def db_insert(table, columns, values, last_row=False):

    db, c = start_db()

    c.execute('''INSERT INTO {} {} VALUES {}'''.format(table, columns, values))
    last_id = c.lastrowid
    db.commit()
    db.close()

    if last_row:
        return last_id


def db_delete(table, where):

    db, c = start_db()

    c.execute('''DELETE FROM {} WHERE {}'''.format(table, where))

    db.commit()
    db.close()


def db_update(table, columns, where):

    db, c = start_db()

    c.execute('''UPDATE {} SET {} WHERE {}'''.format(table, columns, where))

    db.commit()
    db.close()


def empty_table(table_name):

    """Delete the bet from the temporary folder."""

    db, c = start_db()

    c.execute('''DELETE FROM {}'''.format(table_name))

    db.commit()
    db.close()


def check_before_play():

    """
    Return all the matches in the 'Pending' bet which have been played
    already or started.
    """

    invalid_matches = []

    time_now = datetime.datetime.now()

    bet_id = db_select(
            table='bets',
            columns_in=['bet_id'],
            where='bet_status = "Pending"')[0]

    matches = db_select(
            table='bets INNER JOIN predictions on pred_bet = bet_id',
            columns_in=['pred_id', 'pred_user', 'pred_date', 'pred_team1',
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
