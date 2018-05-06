import sqlite3
import numpy as np
from itertools import groupby, count


partecipants = ['Testazza', 'Nonno', 'Pacco', 'Zoppo', 'Nano']


def update_bets_preds():

	db = sqlite3.connect('extended_db')
	c = db.cursor()
	c.execute("PRAGMA foreign_keys = ON")

	bets = list(c.execute('''SELECT bet_id, bet_date, bet_euros, bet_prize,
						  bet_result FROM bets WHERE
						  bet_result != "Unknown"'''))

	preds = list(c.execute('''SELECT pred_id, pred_bet, pred_user, pred_date,
						   pred_time, pred_team1, pred_team2, pred_league,
						   pred_field, pred_rawbet, pred_quote, pred_status,
						   pred_result, pred_label FROM predictions WHERE
						   pred_label != "NULL"'''))
	db.close()

	return bets, preds


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


class Stats(object):
	def __init__(self):
		self.win_teams, self.lose_teams = self.stats_on_teams_or_bets('teams')
		self.win_bets, self.lose_bets = self.stats_on_teams_or_bets('bets')
		self.win_preds = self.winning_preds()
		self.money = self.money_bal()
		self.highest_win_quote, self.lowest_los_quote = self.quotes_rec()

	def stats_on_teams_or_bets(self, string):

		total = {}
		win = {}
		lose = {}

		if string == 'teams':
			data = [(el[5], el[6], el[13]) for el in preds]
		else:
			data = [(el[0], el[9], el[13]) for el in preds]

		for var1, var2, label in data:
			if string == 'teams':
				total[var1] = total[var1] + 1 if var1 in total else 1
			total[var2] = total[var2] + 1 if var2 in total else 1
			if label == 'WINNING':
				if string == 'teams':
					win[var1] = win[var1] + 1 if var1 in win else 1
				win[var2] = win[var2] + 1 if var2 in win else 1
			else:
				if string == 'teams':
					lose[var1] = lose[var1] + 1 if var1 in lose else 1
				lose[var2] = lose[var2] + 1 if var2 in lose else 1

		# Teams which played x times with x<th will not be counted
		th = 6
		win = [(round(win[team] / total[team] * 100, 1), team) for team
		        in win if total[team] >= th]
		win.sort(key=lambda x: x[0], reverse=True)

		lose = [(round(lose[team] / total[team] * 100, 1), team) for team
		        in lose if total[team] >= th]
		lose.sort(key=lambda x: x[0], reverse=True)

		return win, lose

	def winning_preds(self):
		return round(sum([1 for el in preds if el[13] == 'WINNING']) /
		             len(preds) * 100, 1)

	def money_bal(self):
		return (sum([el[3] for el in bets if el[4] == 'WINNING']) -
		        sum([el[2] for el in bets]))

	def quotes_rec(self):

		win, lose = (0, 0)

		data = [(el[2], el[10]) for el in preds if el[13] == 'WINNING']
		data.sort(key=lambda x: x[1], reverse=True)
		for i, g in groupby(data, lambda x: x[1]):
			win = (i, '/'.join(list([el[0] for el in g])))
			break

		data = [(el[2], el[10]) for el in preds if el[13] == 'LOSING']
		data.sort(key=lambda x: x[1])
		for i, g in groupby(data, lambda x: x[1]):
			lose = (i, '/'.join(list([el[0] for el in g])))
			break

		return win, lose




bets, preds = update_bets_preds()
players = {name: Player(name) for name in partecipants}
stats = Stats()
# print('aaa')
