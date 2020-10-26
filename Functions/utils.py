import datetime
import numpy as np
from nltk.util import ngrams
from nltk.metrics.distance import jaccard_distance

import db_functions as dbf
import config as cfg


def autoplay(bet_id: int) -> bool:

    preds = dbf.db_select(table='predictions',
                          columns=['id'],
                          where=f'bet_id = {bet_id}')
    return True if len(preds) == cfg.N_BETS else False


def create_list_of_matches(bet_id: int) -> str:

    """
    Create a list of the matches inside the bet.
    """

    matches = dbf.db_select(
            table='predictions',
            columns=['user', 'date', 'team1', 'team2', 'bet_alias', 'quote'],
            where=f'bet_id = {bet_id}')

    # Sort matches by datetime
    matches = sorted(matches, key=lambda x: x[1])

    message = ''
    for user, dt, team1, team2, rawbet, quote in matches:
        # Extract the time
        dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        hhmm = str(dt.hour).zfill(2) + ':' + str(dt.minute).zfill(2)

        message += (f'<b>{user}</b>:     {team1}-{team2} ({hhmm})    '
                    f'{rawbet}      @<b>{quote}</b>\n')

    return message


def create_summary(euros: int) -> str:

    """
    Create the message with the summary of the bet still open.
    """

    try:
        bet_id = dbf.db_select(table='bets',
                               columns=['id'],
                               where='status = "Pending"')[0]
        message = create_list_of_matches(bet_id)
        quotes_prod = get_quotes_prod(bet_id)
        prize = round(quotes_prod*euros, 1)
        last_line = f'\n\nPossible win with 5€: <b>{prize}</b>'
        return message + last_line
    except IndexError:
        pass

    bet_ids = dbf.db_select(
            table='bets',
            columns=['id'],
            where='status = "Placed" AND result = "Unknown"')

    if bet_ids:
        message = 'Open bets:\n\n'
        for bet_id in bet_ids:
            message = create_list_of_matches(bet_id)
            quotes_prod = get_quotes_prod(bet_id)
            prize = round(quotes_prod * euros, 1)
            last_line = f'{message}\nPossible win: <b>{prize} €</b>\n\n\n'
        # noinspection PyUnboundLocalVariable
        return message + last_line
    else:
        return 'No bets yet. Choose the first one.'


def get_league_name(league_name: str) -> str:
    all_leagues = dbf.db_select(table='leagues', columns=['name'], where='')
    return jaccard_result(in_opt=league_name, all_opt=all_leagues, ngrm=3)


def get_league_url(league_name: str) -> str:

    league = get_league_name(league_name)
    url = dbf.db_select(table='leagues',
                        columns=['url'],
                        where=f'name = "{league}"')[0]
    return url


def get_match_url(team1: str, team2: str) -> str:

    try:
        url = dbf.db_select(
                table='matches',
                columns=['url'],
                where=f'team1 = "{team1}" AND team2 = "{team2}"')[0]
    except IndexError:
        url = dbf.db_select(
                table='matches',
                columns=['url'],
                where=f'team1 = "*{team1}" AND team2 = "*{team2}"')[0]

    return url


def get_nickname(update) -> str:

    name = update.message.from_user.first_name
    nickname = dbf.db_select(table='people',
                             columns=['nick'],
                             where=f'name = "{name}"')[0]
    return nickname


def get_quotes_prod(bet_id: int) -> float:

    quotes = dbf.db_select(table='predictions',
                           columns=['quote'],
                           where=f'bet_id = {bet_id}')
    return np.prod(np.array(quotes))


def get_role(update) -> str:

    name = update.message.from_user.first_name
    role = dbf.db_select(table='people',
                         columns=['role'],
                         where=f'name = "{name}"')[0]
    return role


def insert_new_bet_entry() -> int:

    dbf.db_insert(table='bets',
                  columns=['status', 'result'],
                  values=['Pending', 'Unknown'])

    bet_id = dbf.db_select(table='bets',
                           columns=['id'],
                           where='status = "Pending"')[0]
    return bet_id


def jaccard_result(in_opt: str, all_opt: list, ngrm: int) -> str:

    """
    Fix user input.
    """

    in_opt = in_opt.lower().replace(' ', '')
    n_in = set(ngrams(in_opt, ngrm))

    out_opts = [pl.lower().replace(' ', '') for pl in all_opt]
    n_outs = [set(ngrams(pl, ngrm)) for pl in out_opts]

    distances = [jaccard_distance(n_in, n_out) for n_out in n_outs]

    if len(set(distances)) == 1:
        return jaccard_result(in_opt, all_opt, ngrm-1) if ngrm > 2 else ''
    else:
        return all_opt[np.argmin(distances)]


def nothing_pending(nickname: str) -> bool:

    pending = dbf.db_select(table='predictions',
                            columns=['user'],
                            where='status = "Not Confirmed"')

    return True if nickname not in pending else False


def outside_quote_limits(nickname: str) -> bool:

    """
    Check if quotes limits are respected.
    """

    pred_id, quote = dbf.db_select(table='predictions',
                                   columns=['id', 'quote'],
                                   where=(f'user = "{nickname}" AND ' +
                                          'status = "Not Confirmed"'))[0]

    if not cfg.LIM_LOW < quote < cfg.LIM_HIGH:
        dbf.db_delete(table='predictions', where=f'id = {pred_id}')
        return True
    else:
        return False


def remove_pending_same_match(nickname: str):

    team1, team2 = dbf.db_select(
            table='predictions',
            columns=['team1', 'team2'],
            where=f'user = "{nickname}" AND status = "Not Confirmed"')[0]

    cond1 = f'team1 = "{team1}" AND team2 = "{team2}"'
    cond2 = f'user != "{nickname}"'
    cond3 = 'status = "Not Confirmed"'
    dbf.db_delete(table='predictions',
                  where=f'{cond1} AND {cond2} AND {cond3}')


def select_team(in_team: str) -> str:

    """
    Find correct team name.
    """

    in_team = in_team[1:] if in_team[0] == '*' else in_team
    all_teams = dbf.db_select(table='teams', columns=['name'], where='')

    return jaccard_result(in_opt=in_team, all_opt=all_teams, ngrm=3)


def update_db_after_confirm(nickname: str) -> int:

    """
    Update the table 'predictions'.
    """

    # Check if there is any bet with status 'Pending' in the 'bets' table
    try:
        bet_id = dbf.db_select(table='bets',
                               columns=['id'],
                               where='status = "Pending"')[0]
    except IndexError:
        bet_id = insert_new_bet_entry()

    remove_pending_same_match(nickname)

    dbf.db_update(table='predictions',
                  columns=['bet_id', 'status'],
                  values=[bet_id, 'Confirmed'],
                  where=f'user = "{nickname}" AND status = "Not Confirmed"')

    # Insert the bet into the "to_play" table
    update_to_play_table(nickname=nickname, bet_id=bet_id)


    return bet_id


def update_to_play_table(nickname: str, bet_id: int):

    # TODO change bet values in table predictions with their alias
    team1, team2, bet_alias = dbf.db_select(
            table='predictions',
            columns=['team1', 'team2', 'bet_alias'],
            where=f'user = "{nickname}" AND bet_id = {bet_id}')[-1]

    # TODO make sure there is only 1 name for each alias in table fields
    field, bet = dbf.db_select(table='fields',
                               columns=['name', 'bet'],
                               where=f'alias = "{bet_alias}"')[0]

    url = get_match_url(team1=team1, team2=team2)
    dbf.db_insert(table='to_play',
                  columns=['url', 'field', 'bet'],
                  values=[url, field, bet])
