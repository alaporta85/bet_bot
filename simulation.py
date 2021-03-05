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


def day_balance(n_bets: int, euros_per_bet: int, list_of_bets: list):

    fake_money_won = np.array([np.prod(bet) for bet in list_of_bets])
    perc_winning = (fake_money_won > 0).sum() / len(fake_money_won)*100

    fake_money_won *= euros_per_bet
    fake_money_won = np.array_split(fake_money_won, n_bets)

    return np.array(fake_money_won).mean(axis=1), perc_winning


def get_axes(n_figures: int) -> np.array:
    cols = 3
    row_int, row_rest = n_figures // cols, n_figures % cols
    rows = row_int if not row_rest else row_int + 1
    _, axes = plt.subplots(rows, cols, figsize=(25, 4 * rows))
    return axes.flatten()


def get_data(use_combo: bool) -> pd.DataFrame:

    cols = ['date', 'team1', 'team2', 'league', 'bet_alias', 'quote', 'label']
    data = dbf.db_select(table='simulations', columns=cols, where='')
    df = pd.DataFrame(data, columns=cols)

    if not use_combo:
        df = df[~df['bet_alias'].str.contains('+', regex=False)].copy()
    df.replace({'WINNING': 1, 'LOSING': 0}, inplace=True)

    return df


def get_money_and_prizes():
    money_bet = dbf.db_select(
            table='bets',
            columns=['euros', 'prize', 'result'],
            where='status = "Placed" AND result != "Unknown"')

    euros, prizes, labels = zip(*money_bet)

    euros = np.array(euros)
    labels = [True if i == 'WINNING' else False for i in labels]
    prizes = np.multiply(np.array(prizes), np.array(labels))
    return euros[euros > 0], prizes[euros > 0]


def get_trend(euros_played: np.array, euros_won: np.array):
    balance = euros_won - euros_played
    return [sum(balance[:i]) for i in range(1, len(balance)+1)]


def plot_quote_distr(datafr: pd.DataFrame, q_sep: float, fine_step: float,
                     coarse_step: float) -> None:

    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(25, 6))
    sns.histplot(
            data=datafr.loc[datafr['quote'] <= q_sep, 'quote'],
            bins=np.arange(1, q_sep + .1, fine_step), ax=ax1, label='TOTAL')

    sns.histplot(
            data=datafr.loc[(datafr['quote'] <= q_sep) &
                            (datafr['label'] == 'WINNING'), 'quote'],
            bins=np.arange(1, q_sep + .1, fine_step), ax=ax1, color='g',
            label='WINNING')

    max_quote = datafr['quote'].max()
    sns.histplot(
            data=datafr.loc[datafr['quote'] > q_sep, 'quote'],
            bins=np.arange(q_sep, max_quote + .1, coarse_step), ax=ax2,
            label='TOTAL')
    sns.histplot(
            data=datafr.loc[(datafr['quote'] > q_sep) &
                            (datafr['label'] == 'WINNING'), 'quote'],
            bins=np.arange(q_sep, max_quote + .1, coarse_step), ax=ax2,
            color='g', label='WINNING')
    ax1.legend()
    ax2.legend()


def quote_simulation(n_trials: int, quotes_to_test: np.array,
                     tolerance: float, use_combo: bool):

    # Money played and money won for real, day by day
    real_mn_bet, real_mn_won = get_money_and_prizes()

    # Number of bets played for real
    n_bets = len(real_mn_bet)

    # Day by day balance
    real_trend = get_trend(euros_played=real_mn_bet, euros_won=real_mn_won)

    # Percentage of bets won
    real_perc = (real_mn_won > 0).sum() / n_bets

    # Euros to play per bet
    euros_per_bet = real_mn_bet.sum() / n_bets

    df = get_data(use_combo=use_combo)

    n_figs = quotes_to_test.shape[0]
    axes = get_axes(n_figures=n_figs)

    fake_money_bet = np.array([euros_per_bet for _ in range(n_bets)])
    for i, q in enumerate(quotes_to_test):
        print(f'\rFigure: {i+1}/{n_figs}', end='')

        ax = axes[i]

        cond1 = df['quote'] >= q - tolerance
        cond2 = df['quote'] <= q + tolerance
        filt_data = df.loc[cond1 & cond2, ['quote', 'label']].values

        for n_preds in [1, 2, 3, 4, 5]:
            day_bets = all_bets_per_day(data_array=filt_data,
                                        n_trials=n_trials*n_bets,
                                        n_preds=n_preds)

            fake_money_won, win_perc = day_balance(n_bets=n_bets,
                                                   euros_per_bet=euros_per_bet,
                                                   list_of_bets=day_bets)

            fake_trend = get_trend(euros_played=fake_money_bet,
                                   euros_won=fake_money_won)

            ax.plot(fake_trend, label=f'{n_preds}, {win_perc: .1f} %')
            ax.set_title(f'Quota: {q: .2f}', fontsize=15)

        ax.plot(real_trend, label=f'real, {real_perc: .2f} %')
        ax.legend()


def system_simulation(combs_to_play: dict):

    bet_ids = dbf.db_select(table='bets',
                            columns=['id'],
                            where='result != "Unknown" AND euros > 0')

    all_bets = [dbf.db_select(table='predictions',
                              columns=['quote', 'label'],
                              where=f'bet_id = {b_id}') for b_id in bet_ids]
    all_bets = [[(q, 1) if lb == 'WINNING' else (q, 0) for q, lb in bet]
                for bet in all_bets]

    bets_as_system = []
    for i, bet in enumerate(all_bets, 1):

        size = len(bet)
        win = 0
        played = 0
        for j in range(1, size+1):
            if j not in combs_to_play:# and j != size:
                continue
            euros_per_bet = combs_to_play[j]
            comb = list(combinations(bet, j))
            for c in comb:
                win += np.prod(np.array(c).flatten())*euros_per_bet
                played += euros_per_bet

        bets_as_system.append(win - played)


    _, ax = plt.subplots(figsize=(25, 6))
    bal = [sum(bets_as_system[:i]) for i in range(1, len(bets_as_system)+1)]
    plt.plot(bal)

    # Money played and money won for real, day by day
    real_mn_bet, real_mn_won = get_money_and_prizes()

    # Day by day balance
    real_trend = get_trend(euros_played=real_mn_bet, euros_won=real_mn_won)
    plt.plot(real_trend)

    wins = np.array([np.prod(i) for i in all_bets])
    wins = np.argwhere(wins > 0)
    for w in wins:
        plt.axvline(x=w, c='r', alpha=.3)
    return


# df = get_data(use_combo=True)
# plot_quote_distr(datafr=df, q_sep=5.0, fine_step=.2, coarse_step=2.0)


# quote_simulation(n_trials=100, quotes_to_test=np.arange(1.4, 3.1, .2),
#                  tolerance=.1, use_combo=True)

# system_simulation(combs_to_play={2: 5,
#                                  3: 5,
#                                  4: 5})
# df = get_data(use_combo=True)
# cond1 = df['quote'] >= 1.6 - .05
# cond2 = df['quote'] <= 1.6 + .05
# filt_data = df.loc[cond1 & cond2, ['quote', 'label']].values
# day_bets = all_bets_per_day(data_array=filt_data,
#                             n_trials=4,
#                             n_preds=3)
# print('a')
