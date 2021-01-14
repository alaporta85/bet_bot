import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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


def run_simulation(datafr: pd.DataFrame, n_days: int, n_bets_per_day: int,
                   n_preds_per_bet: int, n_trials: int, euros_per_bet: int,
                   quotes_to_test: np.array, use_combo: bool):

    df = datafr.copy()
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

        tolerance = .1
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


# N_DAYS = 100
# N_BETS_PER_DAY = 3
# N_PREDS_PER_BET = 3
# EUROS_PER_BET = 3
# N_TRIALS = 100
# USE_COMBO = True
# QUOTES_TO_TEST = np.arange(2.6, 3.1, .2)
#
# cols = ['date', 'team1', 'team2', 'league', 'bet_alias', 'quote', 'label']
# data = dbf.db_select(table='simulations', columns=cols, where='')
# data = pd.DataFrame(data, columns=cols)
#
# run_simulation(datafr=data, n_days=N_DAYS, n_bets_per_day=N_BETS_PER_DAY,
#                n_preds_per_bet=N_PREDS_PER_BET, n_trials=N_TRIALS,
#                euros_per_bet=EUROS_PER_BET, quotes_to_test=QUOTES_TO_TEST,
#                use_combo=USE_COMBO)
