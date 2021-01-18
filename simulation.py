import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations
import seaborn as sns
sns.set()

from Functions import db_functions as dbf


def all_bets_per_day(data_array: np.array, n_trials: int,
                     n_bets: int, n_preds: int) -> list:

    bets = np.random.randint(low=0, high=data_array.shape[0],
                             size=n_trials*n_bets*n_preds)
    bets = np.array(np.array_split(bets, n_trials*n_bets))
    return [data_array[bet].flatten() for bet in bets]


def day_balance(n_trials: int, euros_per_bet: int, list_of_bets: list):
    prizes = [np.prod(bet) for bet in list_of_bets]

    perc_winning = (np.array(prizes) > 0).sum() / len(prizes)*100
    money_won = (sum(prizes)*euros_per_bet) / n_trials
    money_played = (len(list_of_bets)*euros_per_bet / n_trials)
    return money_won - money_played, perc_winning


def quote_simulation(n_days: int, n_bets_per_day: int, n_preds_per_bet: int,
                     n_trials: int, euros_per_bet: int,
                     quotes_to_test: np.array, tolerance: float,
                     use_combo: bool):

    cols = ['date', 'team1', 'team2', 'league', 'bet_alias', 'quote', 'label']
    data = dbf.db_select(table='simulations', columns=cols, where='')
    df = pd.DataFrame(data, columns=cols)

    if not use_combo:
        df = df[~df['bet_alias'].str.contains('+', regex=False)].copy()
    df.replace({'WINNING': 1, 'LOSING': 0}, inplace=True)

    n_figs = quotes_to_test.shape[0]
    cols = 3
    rows = n_figs//cols if not n_figs % cols else n_figs//cols + 1
    _, axes = plt.subplots(rows, cols, figsize=(25, 4*rows))
    axes = axes.flatten()

    for i in range(n_figs):
        print(f'\rFigure: {i+1}/{n_figs}', end='')

        q = quotes_to_test[i]
        ax = axes[i]

        cond1 = df['quote'] >= q - tolerance
        cond2 = df['quote'] <= q + tolerance
        filt_data = df.loc[cond1 & cond2, ['quote', 'label']].values

        day_balances = []
        cumulative_balances = []
        win_perc = []
        for _ in range(n_days):
            day_bets = all_bets_per_day(data_array=filt_data,
                                        n_trials=n_trials,
                                        n_bets=n_bets_per_day,
                                        n_preds=n_preds_per_bet)

            day_bal, day_perc = day_balance(n_trials=n_trials,
                                            euros_per_bet=euros_per_bet,
                                            list_of_bets=day_bets)

            day_balances.append(day_bal)
            cumulative_balances.append(sum(day_balances))
            win_perc.append(day_perc)

        ax.plot(cumulative_balances)
        ax.set_title((f'Quota: {q: .1f}. '
                      f'Win: {np.array(win_perc).mean(): .1f} %'),
                     fontsize=15)


def system_simulation(combs_to_play: list, euros_per_bet: int):

    bet_ids = dbf.db_select(table='bets',
                            columns=['id'],
                            where='result != "Unknown"')

    all_bets = [dbf.db_select(table='predictions',
                              columns=['quote', 'label'],
                              where=f'bet_id = {b_id}') for b_id in bet_ids]
    all_bets = [[(q, 1) if lb == 'WINNING' else (q, 0) for q, lb in bet]
                for bet in all_bets]

    bets_as_system = []
    for i, bet in enumerate(all_bets, 1):
        win = 0
        n_combs = 0
        for j in range(1, len(bet)+1):
            if j not in combs_to_play:
                continue
            comb = list(combinations(bet, j))
            for c in comb:
                win += np.prod(np.array(c).flatten())*euros_per_bet
                n_combs += 1

        bets_as_system.append(win - n_combs*euros_per_bet)

    a = [sum(bets_as_system[:i]) for i in range(1, len(bets_as_system)+1)]
    plt.plot(a)
    return


# run_simulation(n_days=100, n_bets_per_day=3, n_preds_per_bet=3, n_trials=100,
#                euros_per_bet=3, quotes_to_test=np.arange(2.6, 3.1, .2),
#                tolerance=.1, use_combo=True)

system_simulation(combs_to_play=[5], euros_per_bet=2)
