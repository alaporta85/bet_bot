import numpy as np
from itertools import product
import db_functions as dbf


def esito_finale_1x2(goals_tm1: int, goals_tm2: int) -> list:
	if goals_tm1 == goals_tm2:
		return ['X']
	else:
		return ['1'] if goals_tm1 > goals_tm2 else ['2']


def esito_parziale_1x2(goals_tm1: int, goals_tm2: int, tempo: str) -> list:
	return [f'{esito_finale_1x2(goals_tm1, goals_tm2)} {tempo}']


def doppia_chance(goals_tm1: int, goals_tm2: int) -> list:
	if goals_tm1 == goals_tm2:
		return ['1X', 'X2']
	else:
		return ['1X', '12'] if goals_tm1 > goals_tm2 else ['X2', '12']


def goal_nogoal(goals_tm1: int, goals_tm2: int) -> list:
	return ['GOAL'] if goals_tm1 and goals_tm2 else ['NOGOAL']


def esito_pt_finale(goals_tm1: int, goals_tm2: int,
					goals_tm1_pt: int, goals_tm2_pt: int) -> str:

	pt = esito_finale_1x2(goals_tm1_pt, goals_tm2_pt)[0]
	finale = esito_finale_1x2(goals_tm1, goals_tm2)[0]
	return f'{pt}/{finale}'


def esito_pt_st(goals_tm1_pt: int, goals_tm2_pt: int,
				goals_tm1_st: int, goals_tm2_st: int) -> str:

	pt = esito_finale_1x2(goals_tm1_pt, goals_tm2_pt)[0]
	st = esito_finale_1x2(goals_tm1_st, goals_tm2_st)[0]
	return f'{pt} PT + {st} ST'


def under_over_finale(goals_tm1: int, goals_tm2: int) -> list:
	goal_sum = goals_tm1 + goals_tm2
	under = [f'UNDER {i}' for i in np.arange(goal_sum+.5, 9)]
	over = [f'OVER {i}' for i in np.arange(0.5, goal_sum)]
	return under + over


def under_over_parziale(goals_tm1: int, goals_tm2: int, tempo: str) -> list:
	return [f'{i} {tempo}' for i in under_over_finale(goals_tm1, goals_tm2)]


def esito_finale_gg_ng(goals_tm1: int, goals_tm2: int) -> str:
	combo1 = esito_finale_1x2(goals_tm1, goals_tm2)[0]
	combo2 = goal_nogoal(goals_tm1, goals_tm2)[0]
	return f'{combo1} + {combo2}'


def esito_finale_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = esito_finale_1x2(goals_tm1, goals_tm2)
	combo2 = under_over_finale(goals_tm1, goals_tm2)

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def doppia_chance_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = doppia_chance(goals_tm1, goals_tm2)
	combo2 = under_over_finale(goals_tm1, goals_tm2)

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def doppia_chance_gg_ng(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = doppia_chance(goals_tm1, goals_tm2)
	combo2 = goal_nogoal(goals_tm1, goals_tm2)

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def gg_ng_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = goal_nogoal(goals_tm1, goals_tm2)
	combo2 = under_over_finale(goals_tm1, goals_tm2)

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def add_all_quotes():

	all_options = dbf.db_select(table='quotes',
	                            columns=['match', 'bet', 'quote'],
	                            where='')

	for match_id, bet, quote in all_options:

		_, bet_alias = bet.split('_')

		_, lg, tm1, tm2, date, _ = dbf.db_select(table='matches',
		                                         columns=['*'],
		                                         where=f'id = {match_id}')[0]

		dbf.db_insert(table='simulations',
					  columns=['date', 'team1', 'team2',
							   'league', 'bet_alias', 'quote'],
					  values=[date, tm1, tm2, lg, bet_alias, quote])
