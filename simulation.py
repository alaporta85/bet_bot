import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations
import seaborn as sns
sns.set()

from Functions import db_functions as dbf


def all_bets_per_day(data_array: np.array, n_trials: int,
                     n_preds: int) -> list:

    bets = np.random.randint(low=0, high=data_array.shape[0],
                             size=n_trials*n_preds)
    bets = np.array(np.array_split(bets, n_trials))
    return [data_array[bet].flatten() for bet in bets]


def day_balance(euros_per_bet: int, list_of_bets: list):

    fake_money_won = np.array([np.prod(bet) for bet in list_of_bets])
    fake_money_won *= euros_per_bet

    perc_winning = (fake_money_won > 0).sum() / len(fake_money_won)*100
    return fake_money_won.mean(), perc_winning


def get_data(use_combo: bool) -> pd.DataFrame:

    cols = ['date', 'team1', 'team2', 'league', 'bet_alias', 'quote', 'label']
    data = dbf.db_select(table='simulations', columns=cols, where='')
    df = pd.DataFrame(data, columns=cols)

    if not use_combo:
        df = df[~df['bet_alias'].str.contains('+', regex=False)].copy()
    df.replace({'WINNING': 1, 'LOSING': 0}, inplace=True)

    return df


def get_money_and_prizes():
    money_bet = dbf.db_select(table='bets',
                              columns=['euros', 'prize', 'result'],
                              where='status = "Placed"')

    euros, prizes, labels = zip(*money_bet)

    euros = np.array(euros)
    labels = [True if i == 'WINNING' else False for i in labels]
    prizes = np.multiply(np.array(prizes), np.array(labels))
    return euros[euros > 0], prizes[euros > 0]


def get_trend(euros_played: np.array, euros_won: np.array):
    balance = euros_won - euros_played
    return [sum(balance[:i]) for i in range(1, len(balance)+1)]


def quote_simulation(n_preds_per_bet: int,
                     n_trials: int, quotes_to_test: np.array, tolerance: float,
                     use_combo: bool):

    real_money_bet, real_money_won = get_money_and_prizes()
    real_trend = get_trend(euros_played=real_money_bet,
                           euros_won=real_money_won)
    n_bets = len(real_trend)
    euros_per_bet = real_money_bet.sum() / n_bets

    df = get_data(use_combo=use_combo)

    n_figs = quotes_to_test.shape[0]
    cols = 3
    rows = n_figs//cols if not n_figs % cols else n_figs//cols + 1
    _, axes = plt.subplots(rows, cols, figsize=(25, 4*rows))
    axes = axes.flatten()

    fake_money_bet = [euros_per_bet for _ in range(1, n_bets+1)]
    for i in range(n_figs):
        print(f'\rFigure: {i+1}/{n_figs}', end='')

        q = quotes_to_test[i]
        ax = axes[i]

        cond1 = df['quote'] >= q - tolerance
        cond2 = df['quote'] <= q + tolerance
        filt_data = df.loc[cond1 & cond2, ['quote', 'label']].values

        fake_money_won = []
        win_perc = []
        for _ in range(n_bets):
            day_bets = all_bets_per_day(data_array=filt_data,
                                        n_trials=n_trials,
                                        n_preds=n_preds_per_bet)

            day_money_won, day_perc = day_balance(euros_per_bet=euros_per_bet,
                                                  list_of_bets=day_bets)

            fake_money_won.append(day_money_won)
            win_perc.append(day_perc)

        fake_trend = get_trend(euros_played=np.array(fake_money_bet),
                               euros_won=np.array(fake_money_won))
        ax.plot(fake_trend)
        ax.plot(real_trend, alpha=.3)
        ax.set_title((f'Quota: {q: .2f}. '
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

    wins = np.array([np.prod(i) for i in all_bets])
    wins = np.argwhere(wins > 0)
    for w in wins:
        plt.axvline(x=w, c='r', alpha=.3)
    return


# quote_simulation(n_preds_per_bet=2, n_trials=3,
#                  quotes_to_test=np.arange(1.4, 3.1, .2),
#                  tolerance=.1, use_combo=True)

# system_simulation(combs_to_play=[2, 3], euros_per_bet=2)
