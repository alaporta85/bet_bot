import time
import datetime
import numpy as np
from collections import defaultdict
from nltk.util import ngrams
from nltk.metrics.distance import jaccard_distance

import db_functions as dbf
import config as cfg


def adjust_text_width(text: str, length: int) -> str:

    if length <= len(text):
        return text

    extra_spaces = length - len(text)
    return text.replace(':', f':{" "*extra_spaces}')


def all_bets_per_team(team_name: str) -> str:

    """
    Return a message with all the bets for the selected team.
    """

    match_id, _, team1, team2, *_ = get_match_details(team_name=team_name)[0]

    team1 = team1.replace('*', '')
    team2 = team2.replace('*', '')

    quotes = dbf.db_select(table='quotes',
                           columns=['bet', 'quote'],
                           where=f'match = {match_id}')
    standard = [(b, q) for b, q in quotes if '+' not in b]
    standard = bet_mapping(standard)
    combo = [(b, q) for b, q in quotes if '+' in b]
    combo = bet_mapping(combo)

    message_standard = f'{team1} - {team2}'
    for field in standard:
        message_standard += f'\n\n{field}\n\n'
        for b, q in standard[field]:
            message_standard += adjust_text_width(f'\t\t\t- {b}: {q}\n', 30)

    message_combo = ''
    for field in combo:
        message_combo += f'\n\n{field}\n\n'
        for b, q in combo[field]:
            message_combo += adjust_text_width(f'\t\t\t- {b}: {q}\n', 30)

    return message_standard, message_combo


def autoplay() -> bool:

    bet_id = get_pending_bet_id()
    preds = dbf.db_select(table='predictions',
                          columns=['id'],
                          where=f'bet_id = {bet_id}')
    return True if len(preds) == cfg.N_BETS else False


def bet_mapping(bets_and_quotes: [(str, float)]) -> dict:

    bets_and_quotes = [(f, b, q) for fb, q in bets_and_quotes
                       for f, b in (fb.split('_'),)]

    map_dict = defaultdict(list)
    for f, b, q in bets_and_quotes:
        map_dict[f].append((b, q))

    return map_dict


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


def create_summary_pending_bet() -> str:

    """
    Create the message with the summary of the bet still open.
    """

    bet_id = get_pending_bet_id()
    if bet_id:
        message = create_list_of_matches(bet_id)
        quotes_prod = get_quotes_prod(bet_id)
        prize = round(quotes_prod*cfg.DEFAULT_EUROS, 1)
        last_line = f'\n\nVincita con {cfg.DEFAULT_EUROS}€: <b>{prize}</b>'
        return message + last_line
    return ''


def create_summary_placed_bets():

    bet_ids = get_placed_but_open_bet_details()
    if bet_ids:
        message = 'Scommesse ancora aperte:\n\n'
        for bet_id, prize in bet_ids:
            message += create_list_of_matches(bet_id)
            message += f'{message}\nVincita: <b>{prize} €</b>\n\n\n'
        return message
    return ''


def fix_bet_name(bet_name: str) -> str:

    vals2replace = [(' ', ''), ('*', ''), (',', '.'), ('+', ''),
                    ('TEMPO', 'T'), ('TP', 'T'),
                    ('1T', 'PT'), ('2T', 'ST'),
                    ('GG', 'GOAL'), ('GOL', 'GOAL'),
                    ('NG', 'NOGOAL'), ('NOGOL', 'NOGOAL'),
                    ('HANDICAP', 'H'), ('HAND', 'H')]
    for old, new in vals2replace:
        bet_name = bet_name.replace(old, new)

    all_alias = dbf.db_select(table='fields', columns=['alias'], where='')
    return jaccard_result(in_opt=bet_name, all_opt=all_alias, ngrm=2)


def fix_league_name(league_name: str) -> str:
    all_leagues = dbf.db_select(table='leagues', columns=['name'], where='')
    return jaccard_result(in_opt=league_name, all_opt=all_leagues, ngrm=3)


def fix_team_name(team_name: str) -> str:

    if '*' in team_name:
        all_teams = dbf.db_select(table='teams',
                                  columns=['name'],
                                  where=f'league = "CHAMPIONS LEAGUE"')
    else:
        all_teams = dbf.db_select(table='teams', columns=['name'],
                                  where=f'league != "CHAMPIONS LEAGUE"')

    return jaccard_result(in_opt=team_name, all_opt=all_teams, ngrm=3)


def get_bet_quote(match_id: int, bet_name: str) -> float:

    field_bet = dbf.db_select(table='fields',
                              columns=['name'],
                              where=f'alias = "{bet_name}"')[0]

    quote = dbf.db_select(table='quotes',
                          columns=['quote'],
                          where=f'match = {match_id} AND bet = "{field_bet}"')

    return quote[0] if quote else 0.0


def get_league_url(league_name: str) -> str:

    league = fix_league_name(league_name)
    url = dbf.db_select(table='leagues',
                        columns=['url'],
                        where=f'name = "{league}"')[0]
    return url


def get_match_details(team_name: int) -> list:

    match = dbf.db_select(
            table='matches',
            columns=['*'],
            where=f'team1 = "{team_name}" OR team2 = "{team_name}"')

    return match


def get_nickname(update) -> str:

    name = update.message.from_user.first_name
    nickname = dbf.db_select(table='people',
                             columns=['nick'],
                             where=f'name = "{name}"')[0]
    return nickname


def get_pending_bet_id() -> int:

    pending = dbf.db_select(table='bets',
                            columns=['id'],
                            where='status = "Pending"')
    return pending[0] if pending else 0


def get_placed_but_open_bet_details():

    bet_ids = dbf.db_select(
            table='bets',
            columns=['id', 'prize'],
            where='status = "Placed" AND result = "Unknown"')

    return bet_ids


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


def get_user_chat_id(update) -> int:

    name = update.message.from_user.first_name
    chat_id = dbf.db_select(table='people',
                            columns=['chat_id'],
                            where=f'name = "{name}"')[0]
    return chat_id


def insert_new_bet_entry() -> int:

    dbf.db_insert(table='bets',
                  columns=['status', 'result'],
                  values=['Pending', 'Unknown'])

    return get_pending_bet_id()


def jaccard_result(in_opt: str, all_opt: list, ngrm: int) -> str:

    """
    Fix user input.
    """

    in_opt = in_opt.lower().replace(' ', '')
    n_in = set(ngrams(in_opt, ngrm))

    out_opts = [pl.lower().replace(' ', '').replace('+', '') for pl in all_opt]
    n_outs = [set(ngrams(pl, ngrm)) for pl in out_opts]

    if in_opt in out_opts:
        return all_opt[out_opts.index(in_opt)]

    distances = [jaccard_distance(n_in, n_out) for n_out in n_outs]

    if len(set(distances)) == 1:
        return jaccard_result(in_opt, all_opt, ngrm-1) if ngrm > 2 else ''
    else:
        return all_opt[np.argmin(distances)]


def match_already_chosen(nickname: str) -> bool:

    bet_id = get_pending_bet_id()

    team1, team2 = dbf.db_select(
            table='predictions',
            columns=['team1', 'team2'],
            where=f'user = "{nickname}" AND status = "Not Confirmed"')[0]

    duplicate = dbf.db_select(
            table='predictions',
            columns=['id'],
            where=(f'bet_id = {bet_id} AND team1 = "{team1}" AND ' +
                   f'team2 = "{team2}" AND status = "Confirmed"'))

    return True if duplicate else False


# def match_already_started(nickname: str) -> bool:
def match_already_started(**kwargs) -> bool:

    query = None
    if 'nickname' in kwargs:
        value = kwargs['nickname']
        query = f'user = "{value}" AND status = "Not Confirmed"'
    elif 'match_id' in kwargs:
        value = kwargs['match_id']
        query = f'id = {value}'

    table = kwargs['table']
    dt_pred = dbf.db_select(table=table, columns=['date'], where=query)[0]
    return str_to_dt(dt_as_string=dt_pred) < datetime.datetime.now()


def match_is_out_of_range(match_date: datetime) -> bool:

    today = datetime.datetime.now()
    secs_diff = (match_date - today).total_seconds()
    hours_diff = secs_diff // 3600
    return True if hours_diff > cfg.HOURS_RANGE else False


def nothing_pending(nickname: str) -> bool:

    pending = dbf.db_select(
            table='predictions',
            columns=['id'],
            where=f'user = "{nickname}" AND status = "Not Confirmed"')

    return True if not pending else False


def quote_outside_limits(nickname: str) -> bool:

    """
    Check if quotes limits are respected.
    """

    quote = dbf.db_select(table='predictions',
                          columns=['quote'],
                          where=(f'user = "{nickname}" AND ' +
                                 'status = "Not Confirmed"'))[0]

    return quote < cfg.LIM_LOW or quote > cfg.LIM_HIGH


def remove_bet_without_preds() -> None:

    bet_id = get_pending_bet_id()
    if bet_id:
        preds = dbf.db_select(table='predictions',
                              columns=['id'],
                              where=f'bet_id = {bet_id}')
        if not preds:
            dbf.db_delete(table='bets', where=f'id = {bet_id}')


def remove_existing_match_quotes(team_one: str, team_two: str) -> None:

    match_ids = dbf.db_select(
            table='matches',
            columns=['id'],
            where=f'team1 = "{team_one}" AND team2 = "{team_two}"')
    if match_ids:
        for m_id in match_ids:
            dbf.db_delete(table='matches', where=f'id = {m_id}')
            dbf.db_delete(table='quotes', where=f'match = {m_id}')


def remove_expired_match_quotes() -> None:

    match_ids = dbf.db_select(table='matches', columns=['id'], where='')

    for match_id in match_ids:
        if match_already_started(table='matches', match_id=match_id):
            dbf.db_delete(table='matches', where=f'id = {match_id}')
            dbf.db_delete(table='quotes', where=f'match = {match_id}')


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


def str_to_dt(dt_as_string: str) -> datetime:
    return datetime.datetime.strptime(dt_as_string, '%Y-%m-%d %H:%M:%S')


def time_needed(start):
    end = time.time() - start
    mins = int(end // 60)
    secs = round(end % 60)
    return mins, secs


def update_to_play_table(nickname: str, bet_id: int):

    pred_id, team1, team2, bet_alias = dbf.db_select(
            table='predictions',
            columns=['id', 'team1', 'team2', 'bet_alias'],
            where=f'user = "{nickname}" AND bet_id = {bet_id}')[-1]

    field_bet = dbf.db_select(table='fields',
                              columns=['name'],
                              where=f'alias = "{bet_alias}"')[0]
    field, bet = field_bet.split('_')

    *_, url = get_match_details(team_name=team1)[0]
    dbf.db_insert(table='to_play',
                  columns=['pred_id', 'url', 'field', 'bet'],
                  values=[pred_id, url, field, bet])


def wrong_chat(chat_id: int) -> bool:

    if cfg.DEBUG or chat_id != cfg.GROUP_ID:
        return False
    else:
        return True


def wrong_format(input_text: str) -> bool:

    if not input_text or (input_text[0] == '_' or input_text[-1] == '_'):
        return True
    else:
        return False
