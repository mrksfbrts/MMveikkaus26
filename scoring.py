"""Haamuhanska – pisteytys

Tässä tiedostossa on nykyisen kisan pisteytyslogiikka.
Ensimmäisessä vaiheessa logiikka on tarkoituksella pidetty
täsmälleen samanlaisena kuin alkuperäisessä mm_veikkaus.py-tiedostossa.

ÄLÄ MUUTA pistearvoja vielä tässä vaiheessa.
"""

def get_1x2(home_goals, away_goals):
    """Palauttaa ottelun 1X2-tuloksen."""
    return "1" if home_goals > away_goals else "2" if home_goals < away_goals else "X"


def calculate_match_points(pred, real, double=False):
    """Laskee nykyisen kisan pisteet yhdestä kohteesta.

    Tämä tukee kahta nykyisessä kisassa käytössä olevaa mallia:

    1. Normaali tulosveikkaus:
       - tarkka tulos = 10 p
       - sama voittaja + toinen maalimäärä yhden päässä = 7 p
       - toinen maalimäärä oikein = 6 p
       - tasapeli oikein = 5 p
       - muu oikea 1X2 = 4 p

    2. NHL-tyyppinen 1X2 + Moniveto:
       - Moniveto oikein = 7 p
       - 1X2 oikein = +3 p
       - tuplakohde = pisteet x 2
    """
    if not pred or not real:
        return 0

    # NHL-tyyppinen veikkaus:
    # "mark" = 1X2, home_opts/away_opts = Moniveto.
    if "mark" in pred:
        rh, ra = real.get("home_goals"), real.get("away_goals")

        if rh is None or ra is None:
            return 0

        pts = (
            7
            if rh in pred.get("home_opts", [])
            and ra in pred.get("away_opts", [])
            else 0
        )

        if pred.get("mark") == get_1x2(rh, ra):
            pts += 3

        return pts * 2 if double else pts

    # Normaali tarkka tulosveikkaus.
    ph, pa = pred.get("home_goals"), pred.get("away_goals")
    rh, ra = real.get("home_goals"), real.get("away_goals")

    if None in (ph, pa, rh, ra):
        return 0

    # Väärä 1X2 = 0 pistettä.
    if get_1x2(ph, pa) != get_1x2(rh, ra):
        return 0

    if ph == rh and pa == ra:
        pts = 10
    elif (
        (ph == rh and abs(pa - ra) == 1)
        or (pa == ra and abs(ph - rh) == 1)
    ):
        pts = 7
    elif ph == rh or pa == ra:
        pts = 6
    elif get_1x2(ph, pa) == "X":
        pts = 5
    else:
        pts = 4

    return pts * 2 if double else pts
