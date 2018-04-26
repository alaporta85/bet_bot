import sqlite3
import numpy as np
from itertools import groupby, count


partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']

db = sqlite3.connect('extended_db')
c = db.cursor()
c.execute("PRAGMA foreign_keys = ON")

bets = list(c.execute('''SELECT bet_id, bet_date, bet_euros, bet_prize,
					  bet_result FROM bets WHERE bet_result != "Unknown"'''))

preds = list(c.execute('''SELECT pred_id, pred_bet, pred_user, pred_date,
					   pred_time, pred_team1, pred_team2, pred_league,
					   pred_field, pred_rawbet, pred_quote, pred_status,
					   pred_result, pred_label FROM predictions WHERE
					   pred_label != "NULL"'''))
db.close()


class Player(object):
	def __init__(self, name):
		self.name = name
		self.bets_played = len([1 for pred in preds if pred[2] == self.name])
		self.quotes_index = self.set_quotes_index()
		self.quotes_win = sorted([pred[10] for pred in preds if
		                          pred[2] == self.name and
		                          pred[13] == 'WINNING'], reverse=True)
		self.quotes_lose = [prev[10] for prev in preds if prev[2] == self.name
		                    and prev[13] == 'LOSING']
		self.ratio = '{}/{}'.format(len(self.quotes_win), self.bets_played)
		self.perc = round(len(self.quotes_win) / self.bets_played * 100, 1)
		self.mean_quote = round(np.array(self.quotes_win[1:-1]).mean(), 2)
		self.index = np.prod(self.quotes_index) / self.bets_played
		self.best_series = self.set_best_series()
		self.worst_series = self.set_worst_series()
		self.cake = self.set_cake_value()


	def set_quotes_index(self):
		quotes_index = []

		for i in range(1, len(bets) + 1):
			try:
				bet = [(el[1], el[10], el[13]) for el in preds if el[1] == i
				       and el[2] == self.name][0]
				if bet[2] == 'WINNING':
					quotes_index.append(bet[1])
				else:
					quotes_index.append(1)
			except IndexError:
				quotes_index.append(1)

		return np.array(quotes_index)

	def set_cake_value(self):
		value = 0
		for bet in bets:
			_id = bet[0]
			prize = bet[3]
			if bet[4] == 'LOSING':
				losing_preds = [pred for pred in preds if pred[1] == _id and
				                pred[13] == 'LOSING']
				if len(losing_preds) == 1 and losing_preds[0][2] == self.name:
					value += prize / losing_preds[0][10]

		return round(value, 1)

	def set_best_series(self):
		last_pred = [el[1] for el in preds if el[2] == self.name][-1]
		data = [el[1] for el in preds if el[2] == self.name and
		        el[13] == 'WINNING']
		c = count()
		series = max((list(g) for _, g in groupby(data, lambda x: x - next(c))),
		             key=len)

		return ((len(series), 'Concluded') if series[-1] != last_pred else
		        (len(series), 'Ongoing'))

	def set_worst_series(self):
		last_pred = [el[1] for el in preds if el[2] == self.name][-1]
		data = [el[1] for el in preds if el[2] == self.name and
		        el[13] == 'LOSING']
		c = count()
		series = max((list(g) for _, g in groupby(data, lambda x: x - next(c))),
		             key=len)

		return ((len(series), 'Concluded') if series[-1] != last_pred else
		        (len(series), 'Ongoing'))



players = {name: Player(name) for name in partecipants}
# print('aaa')
