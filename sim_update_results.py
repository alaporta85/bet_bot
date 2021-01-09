import datetime
import numpy as np
import db_functions as dbf
from itertools import product


def esito_1x2(goals_tm1: int, goals_tm2: int, tempo: str) -> list:

	t = f' {tempo}' if tempo else tempo

	if goals_tm1 == goals_tm2:
		return [f'X{t}']
	else:
		return [f'1{t}'] if goals_tm1 > goals_tm2 else [f'2{t}']


def doppia_chance(goals_tm1: int, goals_tm2: int) -> list:
	if goals_tm1 == goals_tm2:
		return ['1X', 'X2']
	else:
		return ['1X', '12'] if goals_tm1 > goals_tm2 else ['X2', '12']


def goal_nogoal(goals_tm1: int, goals_tm2: int) -> list:
	return ['GOAL'] if goals_tm1 and goals_tm2 else ['NOGOAL']


def esito_pt_finale(goals_tm1_pt: int, goals_tm2_pt: int,
					goals_tm1_st: int, goals_tm2_st: int) -> str:

	pt = esito_1x2(goals_tm1=goals_tm1_pt, goals_tm2=goals_tm2_pt, tempo='')[0]

	goals_tm1 = goals_tm1_pt + goals_tm1_st
	goals_tm2 = goals_tm2_pt + goals_tm2_st
	finale = esito_1x2(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')[0]

	return f'{pt}/{finale}'


def esito_pt_st(goals_tm1_pt: int, goals_tm2_pt: int,
				goals_tm1_st: int, goals_tm2_st: int) -> str:

	pt = esito_1x2(goals_tm1=goals_tm1_pt,
	               goals_tm2=goals_tm2_pt,
	               tempo='PT')[0]

	st = esito_1x2(goals_tm1=goals_tm1_st,
	               goals_tm2=goals_tm2_st,
	               tempo='ST')[0]

	return f'{pt} + {st}'


def under_over(goals_tm1: int, goals_tm2: int, tempo: str) -> list:

	t = f' {tempo}' if tempo else tempo
	goal_sum = goals_tm1 + goals_tm2

	under = [f'UNDER {i}{t}' for i in np.arange(goal_sum+.5, 9)]
	over = [f'OVER {i}{t}' for i in np.arange(0.5, goal_sum)]
	return under + over


def esito_finale_gg_ng(goals_tm1: int, goals_tm2: int) -> str:
	combo1 = esito_1x2(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')[0]
	combo2 = goal_nogoal(goals_tm1=goals_tm1, goals_tm2=goals_tm2)[0]
	return f'{combo1} + {combo2}'


def esito_finale_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = esito_1x2(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')
	combo2 = under_over(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def doppia_chance_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = doppia_chance(goals_tm1=goals_tm1, goals_tm2=goals_tm2)
	combo2 = under_over(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def doppia_chance_gg_ng(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = doppia_chance(goals_tm1=goals_tm1, goals_tm2=goals_tm2)
	combo2 = goal_nogoal(goals_tm1=goals_tm1, goals_tm2=goals_tm2)

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def gg_ng_under_over(goals_tm1: int, goals_tm2: int) -> list:
	combo1 = goal_nogoal(goals_tm1=goals_tm1, goals_tm2=goals_tm2)
	combo2 = under_over(goals_tm1=goals_tm1, goals_tm2=goals_tm2, tempo='')

	prod = product(combo1, combo2)
	return [f'{i} + {j}' for i, j in prod]


def str_to_dt(dt_as_string: str, style: str = '%Y-%m-%d %H:%M:%S') -> datetime:
	return datetime.datetime.strptime(dt_as_string, style)


def add_expired_quotes() -> None:

	matches = dbf.db_select(table='matches', columns=['id', 'date'], where='')

	now_dt = datetime.datetime.now()
	past_matches = [str(i) for i, dt in matches if str_to_dt(dt) < now_dt]

	all_options = dbf.db_select(table='quotes',
	                            columns=['match', 'bet', 'quote'],
	                            where=f'match in ({",".join(past_matches)})')
	all_options = [i for i in all_options if 'HAND' not in i[1]]
	all_options = [i for i in all_options if i[1] != 'GOAL/NO GOAL_GOAL']
	all_options = [i for i in all_options if i[1] != 'GOAL/NO GOAL_NOGOAL']

	for match_id, bet, quote in all_options:

		bet_alias = dbf.db_select(table='fields',
		                          columns=['alias'],
		                          where=f'name = "{bet}"')[0]

		_, lg, tm1, tm2, date, _ = dbf.db_select(table='matches',
		                                         columns=['*'],
		                                         where=f'id = {match_id}')[0]

		dbf.db_insert(table='simulations',
					  columns=['date', 'team1', 'team2',
							   'league', 'bet_alias', 'quote'],
					  values=[date, tm1, tm2, lg, bet_alias, quote])


def pred_is_correct(pred_id: int) -> bool:

	pred, tm1_pt, tm2_pt, tm1_st, tm2_st = dbf.db_select(
			table='simulations',
			columns=['bet_alias', 'goals_tm1_pt', 'goals_tm2_pt',
			         'goals_tm1_st', 'goals_tm2_st'],
			where=f'id = {pred_id}')[0]

	tm1 = tm1_pt + tm1_st
	tm2 = tm2_pt + tm2_st

	if (pred in esito_1x2(goals_tm1=tm1, goals_tm2=tm2, tempo='') or

		pred in esito_1x2(goals_tm1=tm1_pt, goals_tm2=tm2_pt, tempo='PT') or

		pred in doppia_chance(goals_tm1=tm1, goals_tm2=tm2) or

		pred == esito_pt_finale(goals_tm1_pt=tm1_pt, goals_tm2_pt=tm2_pt,
		                        goals_tm1_st=tm1_st, goals_tm2_st=tm2_st) or

		pred == esito_pt_st(goals_tm1_pt=tm1_pt, goals_tm2_pt=tm2_pt,
		                    goals_tm1_st=tm1_st, goals_tm2_st=tm2_st) or

		pred in under_over(goals_tm1=tm1, goals_tm2=tm2, tempo='') or

		pred in under_over(goals_tm1=tm1_pt, goals_tm2=tm2_pt, tempo='PT') or

		pred in under_over(goals_tm1=tm1_st, goals_tm2=tm2_st, tempo='ST') or

		pred == esito_finale_gg_ng(goals_tm1=tm1, goals_tm2=tm2) or

		pred in esito_finale_under_over(goals_tm1=tm1, goals_tm2=tm2) or

		pred in doppia_chance_under_over(goals_tm1=tm1, goals_tm2=tm2) or

		pred in doppia_chance_gg_ng(goals_tm1=tm1, goals_tm2=tm2) or

		pred in gg_ng_under_over(goals_tm1=tm1, goals_tm2=tm2)):

		return True
	else:
		return False


def add_labels() -> None:

	pred_ids = dbf.db_select(table='simulations',
	                         columns=['id'],
	                         where='label IS NULL')
	for pred_id in pred_ids:
		label = 'WINNING' if pred_is_correct(pred_id=pred_id) else 'LOSING'
		dbf.db_update(table='simulations',
		              columns=['label'],
		              values=[label],
		              where=f'id = {pred_id}')
