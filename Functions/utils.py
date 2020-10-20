import numpy as np
from nltk.util import ngrams
from nltk.metrics.distance import jaccard_distance

import db_functions as dbf


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


def select_team(in_team: str) -> str:

    """
    Find correct team name.
    """

    in_team = in_team[1:] if in_team[0] == '*' else in_team
    all_teams = dbf.db_select(table='teams', columns=['name'], where='')

    return jaccard_result(in_opt=in_team, all_opt=all_teams, ngrm=3)
