import sqlite3


def empty_table(table: str):

    """
    Delete everything from table.
    """

    db, c = start_db()
    query = f'DELETE FROM {table}'

    c.execute(query)
    db.commit()
    db.close()


def db_delete(table: str, where: str):

    """
    Remove entry from database.
    """

    db, c = start_db()
    query = f'DELETE FROM {table} WHERE {where}'

    c.execute(query)
    db.commit()
    db.close()


def db_insert(table: str, columns: list, values: list, last_index=False):

    """
    Insert a new row in the table.
    """

    db, c = start_db()

    cols = ', '.join(columns)
    vals = ', '.join([f'"{v}"' for v in values])
    query = f'INSERT INTO {table} ({cols}) VALUES ({vals})'

    c.execute(query)
    last_id = c.lastrowid
    db.commit()
    db.close()

    if last_index:
        return last_id


def db_select(table: str, columns: list, where: str) -> list:

    """
    Return content from a specific table of the database.
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


def db_update(table: str, columns: list, values: list, where: str):

    """
    Update values in the table.
    """

    db, c = start_db()

    vals = ', '.join([f'{c}="{v}"' for c, v in zip(columns, values)])

    if where:
        query = f'UPDATE {table} SET {vals} WHERE {where}'
    else:
        query = f'UPDATE {table} SET {vals}'

    c.execute(query)
    db.commit()
    db.close()


def start_db():

    db = sqlite3.connect('extended_db.db')
    c = db.cursor()

    return db, c
