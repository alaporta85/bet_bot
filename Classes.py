from Functions import db_functions as dbf
import matplotlib.image as image
import sqlite3
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from itertools import groupby, count


db, c = dbf.start_db()
colors_dict = list(c.execute('''SELECT person, color FROM colors'''))
colors_dict = {el[0]: el[1] for el in colors_dict}
partecipants = [el for el in colors_dict]
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


class Stats(object):
	def __init__(self):
		self.win_teams, self.lose_teams = stats_on_teams_or_bets('teams')
		self.win_bets, self.lose_bets = stats_on_teams_or_bets('bets')
		self.win_preds = winning_preds()
		self.money = money_bal()
		self.highest_win_quote, self.lowest_los_quote = quotes_rec()

		score()
		cake()
		series()


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


def stats_on_teams_or_bets(string):

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


def winning_preds():
		return round(sum([1 for el in preds if el[13] == 'WINNING']) /
					 len(preds) * 100, 1)


def money_bal():
		return (sum([el[3] for el in bets if el[4] == 'WINNING']) -
				sum([el[2] for el in bets]))


def quotes_rec():

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


def score():

		fin_data = [(name, players[name].index) for name in players]
		fin_data.sort(key=lambda x: x[1], reverse=True)
		max_value = fin_data[0][1]

		names = [el[0] for el in fin_data]
		indices = [round(el[1] / max_value, 3) for el in fin_data]
		ratio = [players[name].ratio for name in names]
		perc = [players[name].perc for name in names]
		mean_quote = [players[name].mean_quote for name in names]
		colors = [colors_dict[name] for name in names]

		bars = plt.bar(range(5), indices, 0.5, color=colors, edgecolor='black',
					   linewidth=0.5, clip_on=False)
		plt.xticks(range(5), names, fontsize=14)
		plt.ylim(0, 1.35)
		plt.box(on=None)
		plt.tick_params(axis='x', which='both', bottom=False, labelbottom=True)
		plt.tick_params(axis='y', which='both', left=False, labelleft=False)

		for i, bar in enumerate(bars):
			text = '{}\n({}%)\n{}'.format(ratio[i], perc[i], mean_quote[i])
			plt.text(bar.get_x() + bar.get_width() / 2.0, indices[i] + 0.03,
					 '{}'.format(text), ha='center', va='bottom', fontsize=10,
					 style='italic')
		for i, bar in enumerate(bars):
			text = '{}'.format(indices[i])
			plt.text(bar.get_x() + bar.get_width() / 2.0, indices[i] + 0.22,
					 '{}'.format(text), ha='center', va='bottom', fontsize=12,
					 fontweight='bold')
		for bar in bars:
			if not bar.get_height():
				bar.set_linewidth(0)

		plt.savefig('score.png', dpi=120, bbox_inches='tight')
		plt.gcf().clear()


def cake():

	"""
	Return a pie chart showing the amount of euros lost because of only one
	LOSING bet.
	"""

	def real_value(val):

		"""Return the real value instead of the %."""

		return round(val/100*sum(euros), 1)

	data = [(name, players[name].cake) for name in partecipants if
			players[name].cake]
	data.sort(key=lambda x: x[1], reverse=True)

	names = [el[0] for el in data]
	euros = [el[1] for el in data]
	colors = [colors_dict[name] for name in names]

	plt.axis('equal')
	explode = [0.04] * len(names)
	explode[0] = 0.07

	patches, text, autotext = plt.pie(euros, labels=names, explode=explode,
									  colors=colors[:len(names)],
									  startangle=120, radius=1.5,
									  autopct=real_value)

	# Change the style of the plot
	for patch in patches:
		patch.set_linewidth(1.5)
		patch.set_edgecolor('black')
	for x in range(len(names)):
		if x == 0:
			text[x].set_fontsize(30)
			autotext[x].set_fontsize(30)
		else:
			text[x].set_fontsize(18)
			autotext[x].set_fontsize(18)

	plt.savefig('cake.png', dpi=120, bbox_inches='tight')
	plt.gcf().clear()


def series():

	series_pos = sorted([(name, players[name].best_series) for name in
						 partecipants], key=lambda x: x[1][0], reverse=True)
	green_arrows = [g for i, g in enumerate(series_pos) if g[1] == 'Ongoing']
	names = [el[0] for el in series_pos]
	series_pos = [el[1][0] for el in series_pos]

	series_neg = [players[name].worst_series for name in names]
	red_arrows = [i for i, g in enumerate(series_neg) if g[1] == 'Ongoing']
	series_neg = [el[0] for el in series_neg]
	abs_max = max((max(series_pos), max(series_neg)))

	bar_width = 0.4
	fig, ax = plt.subplots()
	fig.set_size_inches(10, 7)
	im1 = image.imread('Images/green_arrow.png')
	im2 = image.imread('Images/red_arrow.png')

	# Inserting arrows in the plot
	for i, e in enumerate(names):
		if i in green_arrows:
			from_w = i - bar_width
			to_w = i
			from_h = series_pos[i] + abs_max / 200
			to_h = series_pos[i] + abs_max / 10
			ax.imshow(im1, aspect='auto', extent=(from_w, to_w, from_h, to_h),
					  zorder=-1)

		elif i in red_arrows:
			from_w = i
			to_w = i + bar_width
			from_h = series_neg[i] + abs_max / 200
			to_h = series_neg[i] + abs_max / 10
			ax.imshow(im2, aspect='auto', extent=(from_w, to_w, from_h, to_h),
					  zorder=-1)

	plt.bar([x - bar_width / 2 for x in range(5)], series_pos, bar_width,
			color='g')

	plt.bar([x + bar_width/2 for x in range(5)], series_neg, bar_width,
			color='r')

	plt.xticks(range(5), names, fontsize=17)
	plt.yticks(fontsize=15)
	ax.spines['right'].set_visible(False)
	ax.spines['top'].set_visible(False)
	ax.spines['bottom'].set_visible(False)
	plt.tick_params(axis='x', bottom=False)
	plt.ylim(0, abs_max)

	plt.savefig('series.png', dpi=120, bbox_inches='tight')
	plt.gcf().clear()


bets, preds = update_bets_preds()
players = {name: Player(name) for name in partecipants}
stats = Stats()
