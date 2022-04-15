import time
import db_functions as dbf


def db_insertmany(table: str, columns: list, values: list):

	"""
	Insert a new row in the table.
	"""

	db, c = dbf.start_db()

	cols = ', '.join(columns)
	vals = ', '.join(['?' for _ in values[0]])
	query = f'INSERT INTO {table} ({cols}) VALUES ({vals})'

	c.executemany(query, values)
	db.commit()
	db.close()


def one_by_one(n):
	for _ in range(n):
		dbf.db_insert(table='prova',
					  columns=['Field2_str', 'Field3_float', 'Field4_str'],
					  values=['aaa', .5, 'bbb'])


def all_at_once(n):
	values = [('aaa', .5, 'bbb') for _ in range(n)]
	db_insertmany(table='prova',
	              columns=['Field2_str', 'Field3_float', 'Field4_str'],
				  values=values)


N = 15

dbf.empty_table('prova')
t0 = time.time()
one_by_one(N)
print('One by one:', time.time() - t0)

dbf.empty_table('prova')
t0 = time.time()
all_at_once(N)
print('All at once:', time.time() - t0)
