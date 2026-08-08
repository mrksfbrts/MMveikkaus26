"""Haamuhanska – pisteytys"""


def get_1x2(home_goals, away_goals):
    """Palauttaa ottelun 1X2-tuloksen."""
    return "1" if home_goals > away_goals else "2" if home_goals < away_goals else "X"


def calculate_match_points(pred, real, double=False):
    """Laskee yhden kohteen pisteet eri veikkaustyypeille."""
    if not pred or not real:
        return 0

    rh, ra = real.get("home_goals"), real.get("away_goals")
    if rh is None or ra is None:
        return 0

    # Erillinen 1X2: yksi tai kaksi merkkiä.
    if pred.get("kind") == "1x2" or "mark_opts" in pred:
        actual = get_1x2(rh, ra)
        opts = pred.get("mark_opts", [])
        return 5 if actual in opts else 0

    # Erillinen moniveto: vain täsmälleen oikea tulos.
    if pred.get("kind") == "moniveto":
        return 5 if rh in pred.get("home_opts", []) and ra in pred.get("away_opts", []) else 0

    # Vanha NHL-tyyppi: 1X2 + moniveto samassa kohteessa.
    if "mark" in pred:
        pts = 7 if rh in pred.get("home_opts", []) and ra in pred.get("away_opts", []) else 0
        if pred.get("mark") == get_1x2(rh, ra):
            pts += 3
        return pts * 2 if double else pts

    # Normaali tarkka tulosveikkaus.
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
    return pts * 2 if double else pts
