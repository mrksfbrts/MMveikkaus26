"""Haamuhanska – pisteytys"""


def get_1x2(home_goals, away_goals):
    return "1" if home_goals > away_goals else "2" if home_goals < away_goals else "X"


def calculate_match_points(pred, real, double=False):
    if not pred or not real:
        return 0
    rh, ra = real.get("home_goals"), real.get("away_goals")
    if rh is None or ra is None:
        return 0

    player_double = bool(pred.get("double", double))

    # 1X2: yhden merkin normaali veikkaus tai pelaajan valitsema tuplamerkki.
    if pred.get("kind") == "1x2" or "mark_opts" in pred:
        actual = get_1x2(rh, ra)
        return 5 if actual in pred.get("mark_opts", []) else 0

    # Moniveto: pelaaja valitsee suoraan tarkat tulokset. Jokeri antaa yhden
    # lisätuloksen, mutta ei muuta yhden oikean tuloksen pistearvoa.
    if pred.get("kind") == "moniveto":
        score_opts = {(int(x[0]), int(x[1])) for x in pred.get("score_opts", [])}
        if not score_opts and pred.get("home_opts") and pred.get("away_opts"):
            score_opts = {(int(h), int(a)) for h in pred.get("home_opts", []) for a in pred.get("away_opts", [])}
        return 5 if (rh, ra) in score_opts else 0

    # NHL 1X2 + Moniveto: tarkka tulosvalinta + 1X2 samassa kohteessa.
    if pred.get("kind") == "nhl" or "mark" in pred:
        score_opts = {(int(x[0]), int(x[1])) for x in pred.get("score_opts", [])}
        if not score_opts and pred.get("home_opts") and pred.get("away_opts"):
            score_opts = {(int(h), int(a)) for h in pred.get("home_opts", []) for a in pred.get("away_opts", [])}
        pts = 7 if (rh, ra) in score_opts else 0
        if pred.get("mark") == get_1x2(rh, ra):
            pts += 3
        return pts

    # Tulosveto: pelaajan oma tuplapistevalinta kaksinkertaistaa kohteen pisteet.
    ph, pa = pred.get("home_goals"), pred.get("away_goals")
    if None in (ph, pa):
        return 0
    if get_1x2(ph, pa) != get_1x2(rh, ra):
        return 0
    if ph == rh and pa == ra:
        pts = 10
    elif ((ph == rh and abs(pa - ra) == 1) or (pa == ra and abs(ph - rh) == 1)):
        pts = 7
    elif ph == rh or pa == ra:
        pts = 6
    elif get_1x2(ph, pa) == "X":
        pts = 5
    else:
        pts = 4
    return pts * 2 if player_double else pts
