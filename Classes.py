from Functions import db_functions as dbf
import matplotlib.image as image
import sqlite3
from datetime import datetime
import numpy as np
import pandas as pd
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
		self.bets_played = len(preds[preds['User'] == self.name])
		self.indices = compute_indices(preds, self.name)
		self.quotes_win, self.quotes_lose = self.quotes_win_lose()
		self.ratio = '{}/{}'.format(len(self.quotes_win), self.bets_played)
		self.perc = round(len(self.quotes_win) / self.bets_played * 100, 1)
		self.mean_quote = round(self.quotes_win[1:-1].mean(), 2)
		self.index = self.indices[-1]
		self.best_series = self.set_series('WINNING')
		self.worst_series = self.set_series('LOSING')
		self.cake = self.set_cake_value()

	def quotes_win_lose(self):

		df = preds[preds['User'] == self.name]

		quotes_win = df[df['Label'] == 'WINNING']['Quote'].values
		quotes_lose = df[df['Label'] == 'LOSING']['Quote'].values

		return quotes_win, quotes_lose

	def set_cake_value(self):

		value = 0

		for i in preds['Bet'].unique():
			df = preds[(preds['Bet'] == i) & (preds['Label'] == 'LOSING')]
			prize = bets.loc[i, 'Prize']
			if (len(df) == 1) and (df['User'].iloc[0] == self.name):
				value += prize/df['Quote'].values[0]

		return round(value, 1)

	def set_series(self, label):

		df = preds[preds['User'] == self.name]['Label'].reset_index(drop=True)
		last_pred = df.index[-1]
		cn = count()
		data = df[df == label].index
		series = max(
				(list(g) for _, g in groupby(data, lambda x: x - next(cn))),
				 key=len)

		return ((len(series), 'Concluded') if series[-1] != last_pred else
				(len(series), 'Ongoing'))


class Stats(object):
	def __init__(self):
		self.win_teams, self.lose_teams = stats_on_teams_or_bets('teams')
		self.win_bets, self.lose_bets = stats_on_teams_or_bets('bets')
		self.win_preds = winning_preds()
		self.win_combos = winning_combos()
		self.money = money_bal()
		self.highest_win_quote, self.lowest_los_quote = quotes_rec()

		normalize_indices()
		score()
		cake()
		series()
		stats_of_the_month()


def update_bets_preds():

	db = sqlite3.connect('extended_db')
	c = db.cursor()
	c.execute("PRAGMA foreign_keys = ON")

	query_bets = (
		'''SELECT bet_id, bet_date, bet_euros, bet_prize, bet_result FROM bets
		   WHERE bet_result != "Unknown"''')
	header_bets = ['Id', 'Date', 'Euros', 'Prize', 'Result']

	bets = pd.DataFrame(list(c.execute(query_bets)), columns=header_bets)
	bets.set_index('Id', drop=True, inplace=True)
	bets.index.name = None

	query_preds = (
		'''SELECT pred_id, pred_bet, pred_user, pred_date, pred_team1,
		   pred_team2, pred_league, pred_field, pred_rawbet, pred_quote,
		   pred_status, pred_result, pred_label FROM predictions WHERE
		   pred_label != "NULL"''')
	header_preds = ['Id', 'Bet', 'User', 'Date', 'Team1', 'Team2', 'League',
	                'Field', 'Rawbet', 'Quote', 'Status', 'Result', 'Label']

	preds = pd.DataFrame(list(c.execute(query_preds)), columns=header_preds)
	preds.set_index('Id', drop=True, inplace=True)
	preds.index.name = None

	db.close()

	return bets, preds


def compute_indices(dataframe, name):

	indices = []

	for i, g in dataframe.groupby('Bet'):
		if name not in g['User'].values and not indices:
			indices.append(0)
		elif name not in g['User'].values:
			indices.append(indices[-1])
		else:
			df = dataframe[(dataframe['Bet'] <= i) &
			               (dataframe['User'] == name)]
			df_win = df[df['Label'] == 'WINNING']
			if len(df_win):
				indices.append(np.prod(df_win['Quote'])/len(df))
			else:
				indices.append(0)

	return np.array(indices)


def normalize_indices():

	data = {name: players[name].indices for name in players}

	for i in range(len(bets)):
		maximum = max([data[name][i] for name in data])
		for name in data:
			players[name].indices[i] /= maximum

	return


def stats_on_teams_or_bets(string):

	def for_teams(label):

		res = preds[preds['Label'] == label][['Team1', 'Team2']]
		res = pd.concat([res['Team1'], res['Team2']])
		res = res.value_counts()

		return {team: res.loc[team] for team in res.index}

	def for_bets(label):

		res = preds[preds['Label'] == label]['Rawbet']
		res = res.value_counts()

		return {bet: res.loc[bet] for bet in res.index}

	if string == 'teams':
		win = for_teams('WINNING')
		lose = for_teams('LOSING')

	else:
		win = for_bets('WINNING')
		lose = for_bets('LOSING')

	total = {x: (win.get(x, 0) + lose.get(x, 0)) for x in set(win) | set(lose)}

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

	return round(len(preds[preds['Label'] == 'WINNING'])/len(preds) * 100, 1)


def winning_combos():

	comb = preds[preds['Rawbet'].str.contains('+', regex=False)]

	return round(len(comb[comb['Label'] == 'WINNING']) / len(comb) * 100, 1)


def money_bal():

	return bets[bets['Result'] == 'WINNING']['Prize'].sum() - bets['Euros'].sum()


def quotes_rec():

	maximum = preds[preds['Label'] == 'WINNING']['Quote'].max()
	minimum = preds[preds['Label'] == 'LOSING']['Quote'].min()

	win = (maximum,
	       '/'.join(list(preds[preds['Quote'] == maximum]['User'].values)))
	lose = (minimum,
	       '/'.join(list(preds[preds['Quote'] == minimum]['User'].values)))

	return win, lose


def score():

		fin_data = [(name, players[name].indices[-1]) for name in players]
		fin_data.sort(key=lambda x: x[1], reverse=True)

		names = [el[0] for el in fin_data]
		indices = [round(el[1], 3) for el in fin_data]
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


def stats_of_the_month():

	"""Best and Worst of every month based on the index."""

	def lmb1():
		return lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S').year

	def lmb2():
		return lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S').month

	def plot(dict1, dict2):

		win = [(name, len(dict1[name])) for name in partecipants]
		win.sort(key=lambda x: x[1], reverse=True)

		names = [el[0] for el in win]
		lose = [(name, len(dict2[name])) for name in names]

		abs_max = max(max([el[1] for el in win]), max([el[1] for el in lose]))

		fig, ax = plt.subplots()
		fig.set_size_inches(13, 6)
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		bar_width = 0.45
		bars1 = plt.bar([x - bar_width / 2 for x in range(5)],
		                [el[1] for el in win],
		                bar_width, color='g')
		bars2 = plt.bar([x + bar_width / 2 for x in range(5)],
		                [el[1] for el in lose], bar_width, color='r')

		plt.xticks(range(5), names, fontsize=25)
		plt.yticks(range(abs_max + 1), fontsize=16)
		plt.tick_params(axis='x', which='both', bottom=False, labelbottom=True)

		for x in range(5):
			dict1[names[x]].reverse()
			message = '\n'.join(dict1[names[x]])

			plt.text(bars1[x].get_x() + bars1[x].get_width() / 2,
			         bars1[x].get_height() + 0.05, message, ha='center',
			         va='bottom', fontsize=15)

		for x in range(5):
			dict2[names[x]].reverse()
			message = '\n'.join(dict2[names[x]])

			plt.text(bars2[x].get_x() + bars2[x].get_width() / 2,
			         bars2[x].get_height() + 0.05, message, ha='center',
			         va='bottom', fontsize=15)

		plt.savefig('sotm.png', dpi=120, bbox_inches='tight')
		plt.gcf().clear()

	dict_win = {name: [] for name in partecipants}
	dict_lose = {name: [] for name in partecipants}

	df1 = preds.copy()
	df1['Year'] = df1['Date'].apply(lmb1())
	df1['Month'] = df1['Date'].apply(lmb2())
	df1 = df1[['Bet', 'User', 'Quote', 'Label', 'Year', 'Month']]
	df1.set_index(['Year', 'Month'], inplace=True)
	for i, g in df1.groupby(df1.index):
		temp = []
		for name in partecipants:
			temp.append((name, compute_indices(g, name)[-1]))
		maximum = max([el[1] for el in temp])
		minimum = min([el[1] for el in temp])

		winners = [el[0] for el in temp if el[1] == maximum]
		losers = [el[0] for el in temp if el[1] == minimum]

		for name in winners:
			yy = datetime.strptime(''.join([str(m) for m in i]),
			                       '%Y%m').strftime('%y')

			mm = datetime.strptime(''.join([str(m) for m in i]),
			                       '%Y%m').strftime('%b')

			dict_win[name].append(mm + "'" + yy)

		for name in losers:
			yy = datetime.strptime(''.join([str(m) for m in i]),
			                       '%Y%m').strftime('%y')

			mm = datetime.strptime(''.join([str(m) for m in i]),
			                       '%Y%m').strftime('%b')

			dict_lose[name].append(mm + "'" + yy)

	plot(dict_win, dict_lose)



bets, preds = update_bets_preds()
players = {name: Player(name) for name in partecipants}
stats = Stats()
