import time
import datetime
import pytz
import numpy as np
from collections import defaultdict
from nltk.util import ngrams
from nltk.metrics.distance import jaccard_distance

import db_functions as dbf
import config as cfg


def add_short_names(matches: list) -> list:

    new_format = []
    for hhmm, team1, team2, q1, qx, q2 in matches:

        team1 = team1.replace(' ', '')
        team2 = team2.replace(' ', '')
        short1 = team1[1:4] if '*' in team1 else team1[:3]
        short2 = team2[1:4] if '*' in team2 else team2[:3]

        new_format.append((hhmm, short1, short2, q1, qx, q2))

    return new_format


def add_quotes_1x2(matches: list) -> list:
    matches_quotes = []
    for match_id, team1, team2, date in matches:
        q1 = dbf.db_select(
                table='quotes',
                columns=['quote'],
                where=f'match = {match_id} AND bet = "ESITO FINALE 1X2_1"')[0]
        qx = dbf.db_select(
                table='quotes',
                columns=['quote'],
                where=f'match = {match_id} AND bet = "ESITO FINALE 1X2_X"')[0]
        q2 = dbf.db_select(
                table='quotes',
                columns=['quote'],
                where=f'match = {match_id} AND bet = "ESITO FINALE 1X2_2"')[0]

        q1 = format(q1, '.2f').rjust(5)
        qx = format(qx, '.2f').rjust(5)
        q2 = format(q2, '.2f').rjust(5)
        matches_quotes.append((date, team1, team2, q1, qx, q2))

    return matches_quotes


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


def all_preds_are_complete(list_of_bets: list) -> list:

    dt = datetime.datetime.now()
    completed_bets = []
    for bet_id, bet_date in list_of_bets:
        preds = dbf.db_select(table='predictions',
                              columns=['date'],
                              where=f'bet_id = {bet_id}')
        preds = [str_to_dt(d) for d in preds]

        still_to_play = [1 for pred_date in preds if pred_date > dt]

        if not sum(still_to_play):
            completed_bets.append((bet_id, bet_date))

    return completed_bets


def autoplay() -> bool:

    bet_id = get_pending_bet_id()
    preds = dbf.db_select(table='predictions',
                          columns=['id'],
                          where=f'bet_id = {bet_id} AND status = "Confirmed"')
    return True if len(preds) == cfg.N_BETS else False


def bet_mapping(bets_and_quotes: [(str, float)]) -> dict:

    bets_and_quotes = [(f, b, q) for fb, q in bets_and_quotes
                       for f, b in (fb.split('_'),)]

    map_dict = defaultdict(list)
    for f, b, q in bets_and_quotes:
        q = format(q, '.2f').rjust(5)
        map_dict[f].append((b, q))

    return map_dict


def create_list_of_matches(bet_id: int) -> str:

    """
    Create a list of the matches inside the bet.
    """

    matches = dbf.db_select(
            table='predictions',
            columns=['user', 'date', 'team1', 'team2', 'bet_alias', 'quote'],
            where=f'bet_id = {bet_id} AND status="Confirmed"')

    # Sort matches by datetime
    matches = sorted(matches, key=lambda x: x[1])

    message = ''
    for user, dt, team1, team2, rawbet, quote in matches:
        # Extract the time
        dt = str_to_dt(dt_as_string=dt)
        hhmm = str(dt.hour).zfill(2) + ':' + str(dt.minute).zfill(2)

        message += (f'<b>{user}</b>:     {team1}-{team2} ({hhmm})    '
                    f'{rawbet}      @<b>{quote}</b>\n\n')

    return message


def create_summary_pending_bet() -> str:

    """
    Create the message with the summary of the bet still open.
    """

    bet_id = get_pending_bet_id()
    if bet_id:
        message = create_list_of_matches(bet_id=bet_id)
        quotes_prod = get_quotes_prod(bet_id)
        prize = round(quotes_prod*cfg.DEFAULT_EUROS, 1)
        last_line = f'\n\nVincita con {cfg.DEFAULT_EUROS}€: <b>{prize}</b>'
        return message + last_line
    return 'Nessuna scommessa attiva'


def create_summary_placed_bets() -> str:

    bet_ids = get_placed_but_open_bet_ids()
    if bet_ids:
        message = 'Scommesse ancora aperte:\n\n'
        # TODO add prize in message
        for bet_id in bet_ids:
            message += create_list_of_matches(bet_id=bet_id)
            message += f'\n{" "*20}{"*"*20}\n\n'
        return message
    return 'Nessuna scommessa attiva'


def datetime_to_time(matches: list) -> list:

    new_format = []
    for dt_str, team1, team2, quote1, quotex, quote2 in matches:
        dt = str_to_dt(dt_str)
        hh = str(dt.hour).zfill(2)
        mm = str(dt.minute).zfill(2)

        new_format.append((f'{hh}:{mm}', team1, team2, quote1, quotex, quote2))

    return new_format


def euros_to_play(command_input: list) -> int:

    if not command_input:
        return cfg.DEFAULT_EUROS

    try:
        euros = int(command_input[0])
        if euros < 2:
            return cfg.DEFAULT_EUROS
        else:
            return euros

    except ValueError:
        return cfg.DEFAULT_EUROS


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
        where = 'league = "CHAMPIONS LEAGUE"'
    else:
        where = 'league != "CHAMPIONS LEAGUE"'

    all_teams = dbf.db_select(table='matches',
                              columns=['team1', 'team2'], where=where)

    all_teams = [t for el in all_teams for t in el]
    return jaccard_result(in_opt=team_name, all_opt=all_teams, ngrm=3)


def get_bet_quote(match_id: int, bet_name: str) -> float:

    field_bet = dbf.db_select(table='fields',
                              columns=['name'],
                              where=f'alias = "{bet_name}"')[0]

    quote = dbf.db_select(table='quotes',
                          columns=['quote'],
                          where=f'match = {match_id} AND bet = "{field_bet}"')

    return quote[0] if quote else 0.0


def get_bets_to_update() -> list:

    bets = dbf.db_select(table='bets',
                         columns=['id', 'date'],
                         where='status = "Placed" AND result = "Unknown"')
    bets.sort(key=lambda x: x[0], reverse=True)

    bets = all_preds_are_complete(list_of_bets=bets)

    if not bets:
        cfg.LOGGER.info('Nessuna scommessa da aggiornare.')

    return bets


def get_confirmed_matches(league_name: str) -> list:

    bet_id = get_pending_bet_id()

    cond1 = f'bet_id = {bet_id}'
    cond2 = f'league = "{league_name}"'
    cond3 = 'status = "Confirmed"'
    matches = dbf.db_select(
            table='predictions',
            columns=['team1', 'team2', 'date'],
            where=f'{cond1} AND {cond2} AND {cond3}')
    return matches


def get_info_to_print(league_name: str, datetime: datetime) -> list:

    all_matches = get_matches_of_the_day(league_name=league_name,
                                         datetime=datetime)
    confirmed = get_confirmed_matches(league_name=league_name)

    available = [i for i in all_matches if i[1:] not in confirmed]
    available = add_quotes_1x2(matches=available)
    available = datetime_to_time(matches=available)
    available = add_short_names(matches=available)

    return available


def get_league_url(league_name: str) -> str:

    league = fix_league_name(league_name)
    url = dbf.db_select(table='leagues',
                        columns=['url'],
                        where=f'name = "{league}"')[0]
    return url


def get_match_details(team_name: str) -> list:

    match = dbf.db_select(
            table='matches',
            columns=['*'],
            where=f'team1 = "{team_name}" OR team2 = "{team_name}"')

    return match


def get_matches_of_the_day(league_name: str, datetime: datetime) -> list:

    matches = dbf.db_select(table='matches',
                            columns=['id', 'team1', 'team2', 'date'],
                            where=f'league = "{league_name}"')
    return [match for match in matches if
            str_to_dt(match[-1]).day == datetime.day]


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


def get_placed_but_open_bet_ids() -> list:

    bet_ids = dbf.db_select(
            table='bets',
            columns=['id'],
            where='status = "Placed" AND result = "Unknown"')

    return bet_ids


def get_preds_available_to_play() -> list:

    dt_now = datetime.datetime.now()
    preds = dbf.db_select(table='to_play', columns=['*'], where='')

    available = []
    for _, url, dt, panel, field, bet in preds:
        if str_to_dt(dt) > dt_now:
            available.append((url, panel, field, bet))

    return available


def get_quotes_prod(bet_id: int) -> float:

    quotes = dbf.db_select(table='predictions',
                           columns=['quote'],
                           where=f'bet_id = {bet_id}')
    return round(np.prod(np.array(quotes)), 1)


def get_role(update) -> str:

    try:
        name = update.message.from_user.first_name
        role = dbf.db_select(table='people',
                             columns=['role'],
                             where=f'name = "{name}"')[0]
    except AttributeError:
        role = 'Admin'

    return role


def get_start_time(hh: int, mm: int, ss: int):
    tmp = datetime.datetime.now()
    tmp = tmp.replace(hour=hh, minute=mm, second=ss)
    return pytz.timezone('Europe/Rome').localize(tmp)


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


def is_float(any_string: str) -> bool:
    try:
        float(any_string.replace(',', '.'))
        return True
    except ValueError:
        return False


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

    team1, team2, league = dbf.db_select(
            table='predictions',
            columns=['team1', 'team2', 'league'],
            where=f'user = "{nickname}" AND status = "Not Confirmed"')[0]

    duplicate = dbf.db_select(
            table='predictions',
            columns=['id'],
            where=(f'bet_id = {bet_id} AND team1 = "{team1}" AND ' +
                   f'team2 = "{team2}" AND league = "{league}" AND' +
                   ' status = "Confirmed"'))

    return True if duplicate else False


def match_already_started(**kwargs) -> bool:

    where = None
    if 'nickname' in kwargs:
        value = kwargs['nickname']
        where = f'user = "{value}" AND status = "Not Confirmed"'
    elif 'match_id' in kwargs:
        value = kwargs['match_id']
        where = f'id = {value}'

    table = kwargs['table']
    dt_pred = dbf.db_select(table=table, columns=['date'], where=where)[0]
    return str_to_dt(dt_as_string=dt_pred) < datetime.datetime.now()


def match_is_out_of_range(match_date: datetime) -> bool:

    today = datetime.datetime.now()
    secs_diff = (match_date - today).total_seconds()
    hours_diff = secs_diff // 3600
    return True if hours_diff > cfg.HOURS_RANGE else False


def matches_per_day(dt: datetime) -> str:

    """
    Return a message containing all the matches scheduled for that day.
    """

    message = ''
    all_leagues = dbf.db_select(table='leagues', columns=['name'], where='')
    for league in all_leagues:

        matches = get_info_to_print(league_name=league, datetime=dt)
        if not matches:
            continue

        message += f'\t\t\t\t{league}\n\n'
        for hhmm, team1, team2, q1, qx, q2 in matches:
            message += f'{hhmm} {team1}-{team2}\t\t{q1} {qx} {q2}\n'
        message += '\n\n\n'

    if not message:
        message = 'Nessun match trovato.'

    return message


def nothing_pending(nickname: str) -> bool:

    pending = dbf.db_select(
            table='predictions',
            columns=['id'],
            where=f'user = "{nickname}" AND status = "Not Confirmed"')

    return True if not pending else False


def notify_inactive_fields() -> str:
    all_fields = dbf.db_select(table='fields',
                               columns=['name'],
                               where='')
    all_fields = [f.split('_')[0] for f in all_fields]

    fields_found = dbf.db_select(table='quotes',
                               columns=['bet'],
                               where='')
    fields_found = [f.split('_')[0] for f in fields_found]

    missing = set(all_fields) - set(fields_found)

    if missing:
        missing = sorted(list(missing))

        message = "\n\t\t\t- ".join(missing)
        return f'Scommesse mancanti:\n\n\t\t\t- {message}'
    else:
        return ''


def prediction_to_delete(nickname: str) -> int:

    bet_id = get_pending_bet_id()
    if not bet_id:
        return 0

    cond1 = f'bet_id = {bet_id}'
    cond2 = f'user = "{nickname}"'
    cond3 = 'status = "Confirmed"'
    confirmed = dbf.db_select(
            table='predictions',
            columns=['id'],
            where=f'{cond1} AND {cond2} AND {cond3}')

    return 0 if not confirmed else confirmed[-1]


def qrange_input_is_wrong(user_input):
    args = user_input[0].split('_')
    if len(args) != 3:
        return 'Formato non corretto. Ex: sab_1.8_2'
    elif args[0] not in cfg.WEEKDAYS:
        return f'"{args[0]}" non è un giorno valido. Ex: sab_1.8_2'
    elif not is_float(args[1]):
        return f'"{args[1]}" non è una quota valida. Ex: sab_1.8_2'
    elif not is_float(args[2]):
        return f'"{args[2]}" non è una quota valida. Ex: sab_1.8_2'
    else:
        return ''


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


def remove_matches_without_quotes():
    """
    Sometimes it happens when matches are postponed, for example.
    """
    ids_in_quotes = set(dbf.db_select(table='quotes', columns=['match'],
                                      where=''))
    ids_in_matches = set(dbf.db_select(table='matches', columns=['id'],
                                       where=''))
    missing = ids_in_matches - ids_in_quotes
    for miss in missing:
        dbf.db_delete(table='matches', where=f'id = {miss}')


def remove_not_confirmed_before_play() -> str:
    bet_id = get_pending_bet_id()
    if not bet_id:
        return ''

    where = f'bet_id = {bet_id} AND status = "Not Confirmed"'

    pending = dbf.db_select(table='predictions',
                            columns=['team1', 'team2'],
                            where=where)

    dbf.db_delete(table='predictions', where=where)

    pend_message = ''
    for team1, team2 in pending:
        pend_message += f'{team1}-{team2} eliminata perché non confermata.\n'

    return pend_message


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


def remove_too_late_before_play() -> str:

    preds = dbf.db_select(table='to_play', columns=['*'], where='')
    too_late_ids = []
    dt_now = datetime.datetime.now()
    for pred_id, _, dt, *_ in preds:
        if str_to_dt(dt) <= dt_now:
            too_late_ids.append(pred_id)

    too_late_message = ''
    for pred_id in too_late_ids:
        team1, team2 = dbf.db_select(table='predictions',
                                     columns=['team1', 'team2'],
                                     where=f'id = {pred_id}')[0]
        too_late_message += f'{team1}-{team2} già iniziata.\n'

        dbf.db_delete(table='to_play', where=f'pred_id = {pred_id}')
        dbf.db_delete(table='predictions', where=f'id = {pred_id}')
    remove_bet_without_preds()

    return too_late_message


def str_to_dt(dt_as_string: str, style: str = '%Y-%m-%d %H:%M:%S') -> datetime:
    return datetime.datetime.strptime(dt_as_string, style)


def time_needed(start: time) -> (int, int):
    end = time.time() - start
    mins = int(end // 60)
    secs = round(end % 60)
    return str(mins).zfill(2), str(secs).zfill(2)


def update_budget(budget: float) -> None:
    dbf.db_update(table='last_results_update',
                  columns=['budget'],
                  values=[budget],
                  where='')


def update_to_play_table(nickname: str, bet_id: int) -> None:

    pred_id, dt, team1, team2, league, bet_alias = dbf.db_select(
            table='predictions',
            columns=['id', 'date', 'team1', 'team2', 'league', 'bet_alias'],
            where=f'user = "{nickname}" AND bet_id = {bet_id}')[-1]

    field_bet = dbf.db_select(table='fields',
                              columns=['name'],
                              where=f'alias = "{bet_alias}"')[0]
    field, bet = field_bet.split('_')

    team1 = team1 if league != 'CHAMPIONS LEAGUE' else f'*{team1}'
    match_id, *_, url = get_match_details(team_name=team1)[0]

    panel = dbf.db_select(
            table='quotes',
            columns=['panel'],
            where=f'match = {match_id} AND bet = "{field_bet}"')[0]

    dbf.db_insert(table='to_play',
                  columns=['pred_id', 'url', 'date', 'panel', 'field', 'bet'],
                  values=[pred_id, url, dt, panel, field, bet])


def from_dayname_to_iso(dayname: str) -> int:

    return cfg.WEEKDAYS[dayname] if dayname.lower() in cfg.WEEKDAYS else 0


def weekday_to_dt(isoweekday: int) -> datetime:

    dt = datetime.date.today()
    while dt.isoweekday() != isoweekday:
        dt += datetime.timedelta(1)
    return dt


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
