import sqlite3
import numpy as np


partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']

db = sqlite3.connect('extended_db')
c = db.cursor()
c.execute("PRAGMA foreign_keys = ON")

bets = list(c.execute('''SELECT pred_id, pred_bet, pred_user, pred_date,
					  pred_time, pred_team1, pred_team2, pred_league,
					  pred_field, pred_rawbet, pred_quote, pred_status,
					  pred_result, pred_label FROM predictions WHERE
					  pred_label != "NULL"'''))
db.close()
n_bets = bets[-1][1]


class Player(object):
	def __init__(self, name):
		self.name = name
		self.bets_played = len([1 for bet in bets if bet[2] == self.name])
		self.quotes_index = self.set_quotes_index()
		self.quotes_win = sorted([bet[10] for bet in bets if
		                          bet[2] == self.name and bet[13] == 'WINNING'],
		                         reverse=True)
		self.quotes_lose = [bet[10] for bet in bets if bet[2] == self.name and
		                    bet[13] == 'LOSING']
		self.ratio = '{}/{}'.format(len(self.quotes_win), self.bets_played)
		self.perc = round(len(self.quotes_win) / self.bets_played * 100, 1)
		self.mean_quote = round(np.array(self.quotes_win[1:-1]).mean(), 2)
		self.index = np.prod(self.quotes_index) / self.bets_played
		self.best_series = 0
		self.worst_series = 0
		self.cake = 0


	def set_quotes_index(self):
		quotes_index = []

		for i in range(1, n_bets + 1):
			try:
				bet = [(el[1], el[10], el[13]) for el in bets if el[1] == i and
				       el[2] == self.name][0]
				if bet[2] == 'WINNING':
					quotes_index.append(bet[1])
				else:
					quotes_index.append(1)
			except IndexError:
				quotes_index.append(1)

		return np.array(quotes_index)



players = {name: Player(name) for name in partecipants}
# print('aaa')