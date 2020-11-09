from Functions import db_functions as dbf
import config as cfg
import matplotlib.image as image
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import groupby, count


class Player(object):
	def __init__(self, name):
		self.name = name
		self.color = get_user_color(self.name)
		# self.bets_played = preds[preds['user'] == self.name].shape[0]
		# self.quotes_win, self.quotes_lose = self.quotes_win_lose()
		# self.ratio = f'{len(self.quotes_win)}/{self.bets_played}'
		# self.perc = round(len(self.quotes_win) / self.bets_played * 100, 1)
		# self.mean_quote = round(self.quotes_win[1:-1].mean(), 2)
		self.best_series = self.set_series('WINNING')
		self.worst_series = self.set_series('LOSING')
		self.current_series = self.set_series('CURRENT')
		self.cake = self.set_cake_value()

	def quotes_win_lose(self):

		df = preds[preds['user'] == self.name].copy()
		df.sort_values('quote', inplace=True)

		quotes_win = df[df['label'] == 'WINNING']['quote'].values
		quotes_lose = df[df['label'] == 'LOSING']['quote'].values

		return quotes_win, quotes_lose

	def set_cake_value(self) -> float:

		lost = user_euros_lost(nickname=self.name)
		won = user_euros_won(nickname=self.name)
		cake_value = lost - won

		return round(max(0, cake_value), 1)

	def set_series(self, label):

		df = preds[preds['user'] == self.name]['label'].reset_index(drop=True)
		last_pred = df.index[-1]
		cn = count()

		if label == 'CURRENT':
			labels = ['WINNING', 'LOSING']
			for label in labels:
				data = df[df == label].index
				all_series = (list(g) for _, g in groupby(
						data, lambda x: x - next(cn)))
				last = list(all_series)[-1]
				if last_pred in last:
					return len(last), label

		data = df[df == label].index

		all_series = (list(g) for _, g in groupby(data,
		                                          lambda x: x - next(cn)))

		# noinspection PyTypeChecker
		record = max(reversed(list(all_series)), key=len)

		return ((len(record), 'Concluded') if record[-1] != last_pred else
				(len(record), 'Ongoing'))


class Stats(object):
	def __init__(self):
		self.win_teams, self.lose_teams = stats_on_teams_or_bets('teams')
		self.win_bets, self.lose_bets = stats_on_teams_or_bets('bets')
		self.win_preds = winning_preds_perc()
		self.win_combos = winning_combos_perc()
		self.money = money_bal()
		self.highest_win_quote, self.lowest_los_quote = quotes_rec()

		# for i in cfg.YEARS:
		# 	score(i)
		cake()
		series()
		stats_of_the_month()


def cake() -> None:

	"""
	Return a pie chart showing the amount of euros lost because of only one
	LOSING bet.
	"""

	def real_value(val):
		"""Return the real value instead of the %."""
		return round(val/100*sum(euros), 1)

	data = [(name, players[name].cake, players[name].color)
	        for name in get_people() if players[name].cake]
	data.sort(key=lambda x: x[1], reverse=True)

	names = [el[0] for el in data]
	euros = [el[1] for el in data]
	colors = [el[2] for el in data]

	plt.axis('equal')
	explode = [0.04] * len(names)
	explode[0] = 0.07

	patches, text, autotext = plt.pie(
			euros, labels=names, explode=explode, colors=colors,
			startangle=120, radius=1.5, autopct=real_value)

	# Change the style of the plot
	for patch in patches:
		patch.set_linewidth(1.5)
		patch.set_edgecolor('black')
	for x in range(len(names)):
		if x == 0:
			text[x].set_fontsize(30)
			autotext[x].set_fontsize(30)
		else:
			text[x].set_fontsize(15)
			autotext[x].set_fontsize(15)

	plt.savefig('cake.png', dpi=120, bbox_inches='tight')
	plt.gcf().clear()


def compute_index(predictions: pd.DataFrame, nickname: str) -> float:

	indices = []
	for i in predictions['bet_id'].values:
		tmp = predictions[(predictions['bet_id'] <= i) &
		                  (predictions['user'] == nickname)]
		win = tmp[tmp['label'] == 'WINNING']
		if win.shape[0]:
			indices.append(np.prod(win['quote']) / tmp.shape[0])
		else:
			indices.append(0)
	return indices[-1]


def get_bets_as_df() -> pd.DataFrame:

	cols = ['date', 'euros', 'prize', 'result']

	bets = dbf.db_select(table='bets',
	                     columns=cols,
	                     where='result != "Unknown"')

	bets = pd.DataFrame(bets, columns=cols)
	bets.index += 1
	bets['date'] = pd.to_datetime(bets['date'], infer_datetime_format=True)

	return bets


def get_people() -> list:
	return dbf.db_select(table='people', columns=['nick'], where='')


def get_preds_as_df() -> pd.DataFrame:

	cols = ['id', 'bet_id', 'user', 'date', 'team1', 'team2',
	        'league', 'bet_alias', 'quote', 'result', 'label']

	preds = dbf.db_select(table='predictions',
	                      columns=cols,
	                      where='result != "NULL"')

	preds = pd.DataFrame(preds, columns=cols)
	preds.set_index('id', drop=True, inplace=True)
	preds.index.name = None
	preds['date'] = pd.to_datetime(preds['date'], infer_datetime_format=True)

	return preds


def get_user_avg_quotes(predictions: pd.DataFrame, nickname: str) -> tuple:

	cond1 = predictions['user'] == nickname
	cond2 = predictions['label'] == 'WINNING'

	won = predictions.loc[cond1 & cond2, 'quote'].sort_values()
	tot = predictions.loc[cond1, 'quote'].sort_values()

	won = won.iloc[1:-1].mean()
	tot = tot.iloc[1:-1].mean()

	return round(tot, 2), round(won, 2)


def get_user_color(nickname: str) -> str:

	color = dbf.db_select(table='people',
	                      columns=['color'],
	                      where=f'nick = "{nickname}"')[0]
	return color


def get_user_perc(predictions: pd.DataFrame, nickname: str) -> float:
	cond1 = predictions['user'] == nickname
	cond2 = predictions['label'] == 'WINNING'

	won = predictions[cond1 & cond2].shape[0]
	tot = predictions[cond1].shape[0]

	return round(won/tot * 100, 1)


def get_user_ratio(predictions: pd.DataFrame, nickname: str) -> str:

	cond1 = predictions['user'] == nickname
	cond2 = predictions['label'] == 'WINNING'

	won = predictions[cond1 & cond2].shape[0]
	tot = predictions[cond1].shape[0]

	return f'{won}/{tot}'


def money_bal() -> float:

	prize = bets[bets['result'] == 'WINNING']['prize'].sum()
	bet = bets['euros'].sum()

	return round(prize - bet, 1)


def normalize_indices(raw_indices: np.array) -> np.array:

	norm_indices = raw_indices / np.max(raw_indices)
	norm_indices[norm_indices <= 1e-3] = 0
	return np.around(norm_indices, 3)


def quotes_rec() -> tuple:

	max_win = preds[preds['label'] == 'WINNING']['quote'].max()
	win = (max_win,
	       '/'.join(list(preds[preds['quote'] == max_win]['user'].values)))

	min_lose = preds[preds['label'] == 'LOSING']['quote'].min()
	lose = (min_lose,
	       '/'.join(list(preds[preds['quote'] == min_lose]['user'].values)))

	return win, lose


def score(which) -> None:

	if which == 'general':
		year1, year2 = 2017, 2030
	else:
		year1, year2 = which.split('-')

	from_ = datetime.strptime(f'{year1}-08-01 00:00:00', '%Y-%m-%d %H:%M:%S')
	to_ = datetime.strptime(f'{year2}-07-31 00:00:00', '%Y-%m-%d %H:%M:%S')

	tmp = preds[(from_ <= preds['date']) & (preds['date'] <= to_)]

	names = [name for name in players]
	indices = np.array([compute_index(tmp, name) for name in names])
	indices = normalize_indices(raw_indices=indices)
	data = sorted(zip(names, indices), key=lambda x: x[1], reverse=True)

	names, indices = zip(*data)

	ratio = [get_user_ratio(tmp, name) for name in names]
	perc = [get_user_perc(tmp, name) for name in names]

	quotes = [get_user_avg_quotes(tmp, name) for name in names]
	avg_quote, avg_quoteW = zip(*quotes)

	colors = [get_user_color(name) for name in names]

	fig, ax = plt.subplots(figsize=(9, 7))

	bars = plt.bar(range(5), indices, 0.5, color=colors, edgecolor='black',
	               linewidth=.8, clip_on=False)
	plt.xticks(range(5), names, fontsize=16)
	plt.ylim(0, 1.35)
	plt.box(on=None)
	plt.tick_params(axis='x', which='both', bottom=False, labelbottom=True)
	plt.tick_params(axis='y', which='both', left=False, labelleft=False)
	plt.title(which, fontsize=16, fontweight='bold', style='italic')

	last_update = dbf.db_select(
			table='last_results_update',
			columns=['message'],
			where='')[0]
	plt.text(0.81, 0.98, str(last_update), transform=ax.transAxes,
	         fontsize=8)

	for i, bar in enumerate(bars):
		text = f'{ratio[i]}\n{perc[i]}%\n{avg_quote[i]}\n{avg_quoteW[i]}'
		plt.text(bar.get_x() + bar.get_width()/2, indices[i] + 0.03,
		         text, ha='center', va='bottom', fontsize=12, style='italic')

	for i, bar in enumerate(bars):
		text = f'{indices[i]}'
		plt.text(bar.get_x() + bar.get_width()/2, indices[i] + 0.23,
		         text, ha='center', va='bottom', fontsize=14, fontweight='bold')

	for bar in bars:
		if not bar.get_height():
			bar.set_linewidth(0)

	plt.text(.8, .9, 'Score', horizontalalignment='center',
	         transform=ax.transAxes, fontweight='bold', fontsize=14)

	expl = 'Win/Total\n%\nAvg Quote\nAvg Quote WIN'
	plt.text(.8, .75, expl, horizontalalignment='center',
	         transform=ax.transAxes, style='italic', fontsize=12)

	plt.savefig(f'score_{which}.png', dpi=120, bbox_inches='tight')
	plt.gcf().clear()


def series() -> None:

	def insert_arrows() -> None:
		for i, e in enumerate(names):
			if i in green_arrows:
				from_w = i - bar_width
				to_w = i
				from_h = series_pos[i] + plot_height / 200
				to_h = series_pos[i] + plot_height / 10
				ax.imshow(green_icon, aspect='auto',
				          extent=(from_w, to_w, from_h, to_h),
				          zorder=-1)

			elif i in red_arrows:
				from_w = i
				to_w = i + bar_width
				from_h = series_neg[i] + plot_height / 200
				to_h = series_neg[i] + plot_height / 10
				ax.imshow(red_icon, aspect='auto',
				          extent=(from_w, to_w, from_h, to_h),
				          zorder=-1)

	def insert_lines():
		current_series = [players[nm].current_series for nm in names]
		for i, g in enumerate(current_series):
			if i not in green_arrows + red_arrows:
				value, label = g
				if label == 'WINNING':
					xmin = i - bar_width
					xmax = i
				else:
					xmin = i
					xmax = i + bar_width

				ax.hlines(y=value, xmin=xmin, xmax=xmax,
				          linewidth=3, color='black')

	series_pos = [(name, players[name].best_series) for name in players]
	series_pos.sort(key=lambda x: x[1][0], reverse=True)
	green_arrows = [i for i, g in enumerate(series_pos) if g[1][1] == 'Ongoing']
	names, data = zip(*series_pos)
	series_pos, _ = zip(*data)

	series_neg = [players[name].worst_series for name in names]
	red_arrows = [i for i, g in enumerate(series_neg) if g[1] == 'Ongoing']
	series_neg, _ = zip(*series_neg)

	plot_height = max((max(series_pos), max(series_neg)))

	bar_width = 0.4
	fig, ax = plt.subplots(figsize=(10, 7))
	green_icon = image.imread('Images/green_arrow.png')
	red_icon = image.imread('Images/red_arrow.png')

	insert_arrows()
	insert_lines()

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
	plt.ylim(0, plot_height)

	plt.savefig('series.png', dpi=120, bbox_inches='tight')
	plt.gcf().clear()


def stats_of_the_month() -> None:

	"""Best and Worst of every month based on the index."""

	def plot(winners: dict, losers: dict):

		win = [(name, len(winners[name])) for name in winners]
		win.sort(key=lambda x: x[1], reverse=True)

		names, n_win = zip(*win)

		lose = [(name, len(losers[name])) for name in names]
		_, n_lose = zip(*lose)

		plot_height = max(max(n_win), max(n_lose))

		fig, ax = plt.subplots(figsize=(13, 6))
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		bar_width = 0.45
		bars1 = plt.bar([x - bar_width/2 for x in range(5)], n_win,
		                bar_width, color='g')
		bars2 = plt.bar([x + bar_width/2 for x in range(5)], n_lose,
		                bar_width, color='r')

		plt.xticks(range(5), names, fontsize=25)
		plt.yticks(range(plot_height + 1), fontsize=16)
		plt.tick_params(axis='x', which='both', bottom=False, labelbottom=True)

		for x in range(5):
			winners[names[x]].reverse()
			message = '\n'.join(winners[names[x]][:3])

			plt.text(bars1[x].get_x() + bars1[x].get_width()/2,
			         bars1[x].get_height() + 0.05, message, ha='center',
			         va='bottom', fontsize=15)

		for x in range(5):
			losers[names[x]].reverse()
			message = '\n'.join(losers[names[x]][:3])

			plt.text(bars2[x].get_x() + bars2[x].get_width() / 2,
			         bars2[x].get_height() + 0.05, message, ha='center',
			         va='bottom', fontsize=15)

		plt.savefig('sotm.png', dpi=120, bbox_inches='tight')
		plt.gcf().clear()

	dict_win = {name: [] for name in players}
	dict_lose = {name: [] for name in players}

	tmp = preds.copy()
	tmp['year'] = tmp['date'].apply(lambda x: x.year)
	tmp['month'] = tmp['date'].apply(lambda x: x.month)
	tmp = tmp[['bet_id', 'user', 'quote', 'label', 'year', 'month']]
	for i, g in tmp.groupby(['year', 'month']):
		y, m = i
		y = datetime.strptime(str(y), '%Y').strftime('%y')
		m = datetime.strptime(str(m), '%m').strftime('%b')

		data = []
		for name in players:
			data.append((name, compute_index(g, name)))

		maximum = max([el[1] for el in data])
		minimum = min([el[1] for el in data])

		winners = [el[0] for el in data if el[1] == maximum]
		losers = [el[0] for el in data if el[1] == minimum]

		for name in winners:
			dict_win[name].append(f"{m} '{y}")

		for name in losers:
			dict_lose[name].append(f"{m} '{y}")

	plot(dict_win, dict_lose)


def stats_on_teams_or_bets(which: str) -> list:

	def for_teams(label):

		res = preds[preds['label'] == label][['team1', 'team2']]
		res = pd.concat([res['team1'], res['team2']])
		res = res.value_counts()

		return res.to_dict()

	def for_bets(label):

		res = preds[preds['label'] == label]['bet_alias']
		res = res.value_counts()

		return res.to_dict()

	if which == 'teams':
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


def user_euros_lost(nickname: str) -> float:

	# Get bets with cake
	info = preds.groupby(['bet_id', 'label']).count().reset_index()
	bets_cake = info[(info['label'] == 'LOSING') &
	                 (info['user'] == 1)]['bet_id'].values

	# Among all cakes get the one of the user
	cond1 = preds['bet_id'].isin(bets_cake)
	cond2 = preds['user'] == nickname
	cond3 = preds['label'] == 'LOSING'
	user_errors = preds.loc[cond1 & cond2 & cond3]

	prizes = bets.loc[user_errors['bet_id'].values, 'prize'].values
	quotes = user_errors['quote'].values

	return np.sum(np.divide(prizes, quotes))


def user_euros_won(nickname: str) -> float:

	# Get all won bets
	bets_won = bets.loc[bets['result'] == 'WINNING']

	# Gets won bets where user gave prediction
	cond1 = preds['bet_id'].isin(bets_won.index)
	cond2 = preds['user'] == nickname
	bets_won_with_user = preds[cond1 & cond2]

	# Get prizes of bets where user gave prediction
	cond = bets_won.index.isin(bets_won_with_user['bet_id'])
	prizes = bets_won.loc[cond, 'prize'].values

	# Get user's quotes in those bets
	quotes = bets_won_with_user['quote'].values
	prize_without_user = np.divide(prizes, quotes)

	return np.sum(prizes) - np.sum(prize_without_user)


def winning_combos_perc() -> float:

	combo = preds[preds['bet_alias'].str.contains('+', regex=False)]
	win_combo = combo[combo['label'] == 'WINNING'].shape[0]

	return round(win_combo / combo.shape[0] * 100, 1)


def winning_preds_perc() -> float:

	win_preds = preds[preds['label'] == 'WINNING'].shape[0]
	return round(win_preds / preds.shape[0] * 100, 1)


bets = get_bets_as_df()
preds = get_preds_as_df()

players = {name: Player(name) for name in get_people()}
stats = Stats()
