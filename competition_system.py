"""Database and Streamlit UI for the extensible competition system.

This module deliberately uses separate tables and scoring from the legacy contest.
"""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

HELSINKI = ZoneInfo("Europe/Helsinki")
PREDICTION_TYPES = {
    "Jääkiekko – Tulosveto": "hockey_score",
    "Jalkapallo – Tulosveto": "football_score",
    "1X2": "result_1x2",
    "Jääkiekko – Moniveto": "hockey_multi",
    "Jalkapallo – Moniveto": "football_multi",
}
TYPE_LABELS = {value: key for key, value in PREDICTION_TYPES.items()}
TOKEN_TYPES = ("tuplaus", "harava", "jokeri")
TOKEN_LABELS = {"tuplaus": "Tuplaus", "harava": "Harava", "jokeri": "Jokeri"}
ALLOWED_TOKENS = {
    "hockey_score": ("tuplaus",), "football_score": ("tuplaus",),
    "result_1x2": ("harava",), "hockey_multi": ("jokeri",),
    "football_multi": ("jokeri",),
}


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


def connect(db_path):
    conn = sqlite3.connect(db_path, timeout=20, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_competition_db(db_path):
    """Add the new schema without altering or deleting legacy application data."""
    with connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','finished','archived')),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS competition_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL REFERENCES competitions(id),
            name TEXT NOT NULL,
            prediction_type TEXT NOT NULL CHECK(prediction_type IN ('hockey_score','football_score','result_1x2','hockey_multi','football_multi')),
            sort_order INTEGER NOT NULL DEFAULT 0,
            tuplaus_count INTEGER NOT NULL DEFAULT 0 CHECK(tuplaus_count >= 0),
            harava_count INTEGER NOT NULL DEFAULT 0 CHECK(harava_count >= 0),
            joker_count INTEGER NOT NULL DEFAULT 0 CHECK(joker_count >= 0)
        );
        CREATE TABLE IF NOT EXISTS competition_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id INTEGER NOT NULL REFERENCES competition_lists(id),
            home TEXT NOT NULL DEFAULT '',
            away TEXT NOT NULL DEFAULT '',
            display_name TEXT NOT NULL DEFAULT '',
            start_iso TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','cancelled')),
            cancelled_before_start INTEGER,
            result_home INTEGER,
            result_away INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            target_id INTEGER NOT NULL REFERENCES competition_targets(id),
            prediction_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(username, target_id)
        );
        CREATE TABLE IF NOT EXISTS token_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            list_id INTEGER NOT NULL REFERENCES competition_lists(id),
            token_type TEXT NOT NULL CHECK(token_type IN ('tuplaus','harava','jokeri')),
            token_slot INTEGER NOT NULL DEFAULT 0,
            target_id INTEGER NOT NULL REFERENCES competition_targets(id),
            status TEXT NOT NULL DEFAULT 'assigned' CHECK(status IN ('assigned','released','refunded','spent')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_competitions_status ON competitions(status,sort_order);
        CREATE INDEX IF NOT EXISTS idx_comp_lists_comp ON competition_lists(competition_id,sort_order);
        CREATE INDEX IF NOT EXISTS idx_comp_targets_list ON competition_targets(list_id,sort_order);
        CREATE INDEX IF NOT EXISTS idx_predictions_target ON user_predictions(target_id,username);
        CREATE TABLE IF NOT EXISTS competition_bonuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL REFERENCES competitions(id),
            list_id INTEGER NOT NULL REFERENCES competition_lists(id),
            username TEXT NOT NULL,
            points INTEGER NOT NULL CHECK(points IN (1,3,5)),
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_comp_bonus ON competition_bonuses(competition_id,username);
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_comp_bonus_user_list ON competition_bonuses(competition_id,list_id,username)")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(token_assignments)")}
        if "token_slot" not in columns:
            conn.execute("ALTER TABLE token_assignments ADD COLUMN token_slot INTEGER NOT NULL DEFAULT 0")
        conn.execute("DROP INDEX IF EXISTS idx_active_user_token")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_active_user_token ON token_assignments(username,list_id,token_type,token_slot) WHERE status='assigned'")


def _outcome(home, away):
    return "1" if home > away else "2" if home < away else "X"


def score_prediction(prediction_type, prediction, result, token_type=None):
    """Return exact spec points (before any token effect where applicable)."""
    if not prediction or result is None:
        return 0
    rh, ra = result.get("home_goals"), result.get("away_goals")
    if rh is None or ra is None:
        return 0
    actual_mark = _outcome(rh, ra)
    if prediction_type in ("hockey_score", "football_score"):
        try:
            ph, pa = int(prediction["home_goals"]), int(prediction["away_goals"])
        except (KeyError, TypeError, ValueError):
            return 0
        predicted_mark = _outcome(ph, pa)
        if predicted_mark != actual_mark:
            return 0
        if (ph, pa) == (rh, ra):
            points = 12 if prediction_type == "hockey_score" else 10
        elif predicted_mark == "X":
            points = 6 if prediction_type == "hockey_score" else 5
        elif (ph == rh) != (pa == ra):
            distance = abs((pa - ra) if ph == rh else (ph - rh))
            if prediction_type == "hockey_score":
                points = 8 if distance <= 1 else 7
            else:
                points = 7 if distance <= 1 else 6
        else:
            points = 5 if prediction_type == "hockey_score" else 4
        return points * (2 if token_type == "tuplaus" else 1)
    if prediction_type == "result_1x2":
        marks = prediction.get("marks", [])
        if token_type == "harava":
            return 4 if actual_mark in marks else 0
        return 5 if prediction.get("mark") == actual_mark else 0
    if prediction_type in ("hockey_multi", "football_multi"):
        scores = prediction.get("scores", [])
        if prediction.get("joker_score") is not None:
            scores = list(scores) + [prediction["joker_score"]]
        hit = any(s and s.get("home_goals") == rh and s.get("away_goals") == ra for s in scores)
        return (10 if hit else 0) + (1 if prediction.get("mark") == actual_mark else 0)
    return 0


def _now():
    return datetime.now(HELSINKI)


def _parse_start(value):
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=HELSINKI) if dt.tzinfo is None else dt.astimezone(HELSINKI)


def _target_open(target, now=None):
    now = now or _now()
    return target["status"] == "scheduled" and now < _parse_start(target["start_iso"])


def _target_ready(target):
    home, away = target["home"].strip(), target["away"].strip()
    return bool(home and away and home.upper() != "TBD" and away.upper() != "TBD")


def _stamp():
    return _now().isoformat()


def _list_token_counts(row):
    return {"tuplaus": row["tuplaus_count"], "harava": row["harava_count"], "jokeri": row["joker_count"]}


def _available_tokens(conn, username, list_row):
    counts = _list_token_counts(list_row)
    result = {}
    for kind in ALLOWED_TOKENS[list_row["prediction_type"]]:
        used_slots = {r[0] for r in conn.execute("SELECT token_slot FROM token_assignments WHERE username=? AND list_id=? AND token_type=? AND status IN ('assigned','spent')",
                                                  (username, list_row["id"], kind)).fetchall()}
        result[kind] = max(0, counts[kind] - len(used_slots))
    return result


def _prediction_text(prediction_type, prediction, token_type=None):
    if not prediction:
        return "Ei veikkausta"
    if prediction_type in ("hockey_score", "football_score"):
        return f"{prediction.get('home_goals','?')}–{prediction.get('away_goals','?')}"
    if prediction_type == "result_1x2":
        return "/".join(prediction.get("marks", [])) if token_type == "harava" else prediction.get("mark", "?")
    base = ", ".join(f"{s.get('home_goals')}–{s.get('away_goals')}" for s in prediction.get("scores", []))
    if prediction.get("joker_score"):
        base += f" + Jokeri {prediction['joker_score'].get('home_goals')}–{prediction['joker_score'].get('away_goals')}"
    return f"{base} · 1X2 {prediction.get('mark','?')}"


def _competition_data(conn, competition_id):
    comp = conn.execute("SELECT * FROM competitions WHERE id=?", (competition_id,)).fetchone()
    lists = conn.execute("SELECT * FROM competition_lists WHERE competition_id=? ORDER BY sort_order,id", (competition_id,)).fetchall()
    return comp, lists


def _all_competitions(conn, status=None):
    if status:
        return conn.execute("SELECT * FROM competitions WHERE status=? ORDER BY sort_order DESC,id DESC", (status,)).fetchall()
    return conn.execute("SELECT * FROM competitions ORDER BY sort_order DESC,id DESC").fetchall()


def _create_competition(db_path, name, description, lists):
    if not name.strip() or not 1 <= len(lists) <= 5:
        raise ValueError("Anna kilpailulle nimi ja 1–5 listaa.")
    stamp = _stamp()
    with connect(db_path) as conn:
        cursor = conn.execute("INSERT INTO competitions(name,description,status,created_at,updated_at) VALUES(?,?,'draft',?,?)",
                              (name.strip(), description.strip(), stamp, stamp))
        cid = cursor.lastrowid
        for index, item in enumerate(lists):
            ptype = item["prediction_type"]
            allowed = set(ALLOWED_TOKENS[ptype])
            counts = {kind: int(item.get(kind, 0)) if kind in allowed else 0 for kind in TOKEN_TYPES}
            if any(value < 0 or value > 99 for value in counts.values()):
                raise ValueError("Pelimerkkien määrän pitää olla välillä 0–99.")
            conn.execute("""INSERT INTO competition_lists(competition_id,name,prediction_type,sort_order,tuplaus_count,harava_count,joker_count)
                            VALUES(?,?,?,?,?,?,?)""", (cid,item["name"].strip(),ptype,index,*[counts[k] for k in TOKEN_TYPES]))
    return cid


def _update_competition_list(db_path, list_id, name, prediction_type, order, counts):
    if prediction_type not in PREDICTION_TYPES.values() or not name.strip():
        raise ValueError("Tarkista listan nimi ja veikkausmuoto.")
    with connect(db_path) as conn:
        row=conn.execute("SELECT l.*,c.status comp_status FROM competition_lists l JOIN competitions c ON c.id=l.competition_id WHERE l.id=?",(list_id,)).fetchone()
        if not row or row["comp_status"]!="draft":
            raise ValueError("Listan rakennetta voi muuttaa vain luonnoksessa.")
        allowed=set(ALLOWED_TOKENS[prediction_type])
        values={k:(int(counts.get(k,0)) if k in allowed else 0) for k in TOKEN_TYPES}
        if any(v<0 or v>99 for v in values.values()): raise ValueError("Pelimerkkimäärän tulee olla välillä 0–99.")
        conn.execute("UPDATE competition_lists SET name=?,prediction_type=?,sort_order=?,tuplaus_count=?,harava_count=?,joker_count=? WHERE id=?",
                     (name.strip(),prediction_type,int(order),values["tuplaus"],values["harava"],values["jokeri"],list_id))


def _save_target(db_path, target_id, list_id, home, away, display_name, start_iso, order):
    start = _parse_start(start_iso)
    stamp = _stamp()
    with connect(db_path) as conn:
        list_row = conn.execute("SELECT l.*,c.status comp_status FROM competition_lists l JOIN competitions c ON c.id=l.competition_id WHERE l.id=?", (list_id,)).fetchone()
        if not list_row:
            raise ValueError("Listaa ei löytynyt.")
        if list_row["comp_status"] in ("finished", "archived"):
            raise ValueError("Päättynyttä tai arkistoitua kilpailua ei voi muokata.")
        if target_id:
            target = conn.execute("SELECT * FROM competition_targets WHERE id=? AND list_id=?",(target_id,list_id)).fetchone()
            if not target or not _target_open(target):
                raise ValueError("Kohdetta voi muokata vain ennen sen alkamista.")
            conn.execute("UPDATE competition_targets SET home=?,away=?,display_name=?,start_iso=?,sort_order=?,updated_at=? WHERE id=?",
                         (home.strip(),away.strip(),display_name.strip(),start.isoformat(),int(order),stamp,target_id))
        else:
            conn.execute("INSERT INTO competition_targets(list_id,home,away,display_name,start_iso,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                         (list_id,home.strip(),away.strip(),display_name.strip(),start.isoformat(),int(order),stamp,stamp))


def _publish(db_path, competition_id):
    with connect(db_path) as conn:
        comp, lists = _competition_data(conn, competition_id)
        if not comp or comp["status"] != "draft" or not 1 <= len(lists) <= 5:
            raise ValueError("Vain 1–5 listaa sisältävän luonnoksen voi julkaista.")
        targets = conn.execute("SELECT t.* FROM competition_targets t JOIN competition_lists l ON l.id=t.list_id WHERE l.competition_id=?",(competition_id,)).fetchall()
        if not targets:
            raise ValueError("Lisää kilpailuun vähintään yksi kohde ennen julkaisua.")
        if any(t["status"] != "scheduled" for t in targets):
            raise ValueError("Peruttua kohdetta ei voi julkaista osana kilpailua.")
        conn.execute("UPDATE competitions SET status='published',updated_at=? WHERE id=?",(_stamp(),competition_id))


def _save_prediction(db_path, username, target_id, prediction):
    stamp = _stamp()
    with connect(db_path) as conn:
        target = conn.execute("SELECT t.*,l.prediction_type,l.id list_id,c.status comp_status FROM competition_targets t JOIN competition_lists l ON l.id=t.list_id JOIN competitions c ON c.id=l.competition_id WHERE t.id=?",(target_id,)).fetchone()
        if not target or target["comp_status"] != "published" or not _target_open(target) or not _target_ready(target):
            raise ValueError("Tähän kohteeseen ei voi enää veikata.")
        ptype = target["prediction_type"]
        token = conn.execute("SELECT token_type FROM token_assignments WHERE username=? AND target_id=? AND status='assigned'",(username,target_id)).fetchone()
        token_type = token["token_type"] if token else None
        if ptype in ("hockey_score","football_score"):
            for key in ("home_goals","away_goals"):
                if not isinstance(prediction.get(key),int) or prediction[key] < 0:
                    raise ValueError("Anna kelvolliset maalimäärät.")
        elif ptype == "result_1x2":
            marks = prediction.get("marks", []) if token_type == "harava" else [prediction.get("mark")]
            if (len(marks) != (2 if token_type == "harava" else 1) or len(set(marks)) != len(marks)
                    or any(mark not in ("1","X","2") for mark in marks)):
                raise ValueError("Valitse yksi merkki tai Haravalla kaksi eri merkkiä.")
            prediction = {"marks": marks} if token_type == "harava" else {"mark": marks[0]}
        else:
            base_count = 4 if ptype == "hockey_multi" else 2
            scores = prediction.get("scores", [])
            if len(scores) != base_count or any(not isinstance(s.get("home_goals"),int) or not isinstance(s.get("away_goals"),int) or min(s["home_goals"],s["away_goals"]) < 0 for s in scores):
                raise ValueError(f"Anna täsmälleen {base_count} kelvollista tarkkaa tulosta.")
            if prediction.get("mark") not in ("1","X","2"):
                raise ValueError("Valitse myös Monivedon 1X2-merkki.")
            joker = prediction.get("joker_score")
            if token_type == "jokeri" and (not joker or not isinstance(joker.get("home_goals"),int) or not isinstance(joker.get("away_goals"),int) or min(joker["home_goals"],joker["away_goals"]) < 0):
                raise ValueError("Anna Jokerin ylimääräinen tarkka tulos.")
            if token_type != "jokeri":
                prediction.pop("joker_score",None)
        encoded = json.dumps(prediction,ensure_ascii=False)
        conn.execute("""INSERT INTO user_predictions(username,target_id,prediction_data,created_at,updated_at) VALUES(?,?,?,?,?)
                        ON CONFLICT(username,target_id) DO UPDATE SET prediction_data=excluded.prediction_data,updated_at=excluded.updated_at""",
                     (username,target_id,encoded,stamp,stamp))


def _assign_token(db_path, username, target_id, token_type):
    stamp = _stamp()
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        target = conn.execute("SELECT t.*,l.prediction_type,l.id list_id,l.tuplaus_count,l.harava_count,l.joker_count,c.status comp_status FROM competition_targets t JOIN competition_lists l ON l.id=t.list_id JOIN competitions c ON c.id=l.competition_id WHERE t.id=?",(target_id,)).fetchone()
        if not target or target["comp_status"] != "published" or not _target_open(target) or not _target_ready(target):
            raise ValueError("Pelimerkin voi käyttää vain avoimeen, pelattavaan kohteeseen.")
        if token_type not in ALLOWED_TOKENS[target["prediction_type"]]:
            raise ValueError("Tämä pelimerkki ei sovi listan veikkausmuotoon.")
        if conn.execute("SELECT 1 FROM token_assignments WHERE username=? AND target_id=? AND status='assigned'",(username,target_id)).fetchone():
            raise ValueError("Kohteessa on jo pelimerkki.")
        counts = _list_token_counts(target)
        used_slots = {r[0] for r in conn.execute("SELECT token_slot FROM token_assignments WHERE username=? AND list_id=? AND token_type=? AND status IN ('assigned','spent')",(username,target["list_id"],token_type)).fetchall()}
        slot = next((i for i in range(counts[token_type]) if i not in used_slots),None)
        if slot is None:
            raise ValueError("Kaikki tämän listan pelimerkit ovat jo käytössä.")
        conn.execute("INSERT INTO token_assignments(username,list_id,token_type,token_slot,target_id,status,created_at,updated_at) VALUES(?,?,?,?,?,'assigned',?,?)",(username,target["list_id"],token_type,slot,target_id,stamp,stamp))


def _remove_token(db_path, username, target_id):
    stamp = _stamp()
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT a.*,t.start_iso,t.status target_status FROM token_assignments a JOIN competition_targets t ON t.id=a.target_id WHERE a.username=? AND a.target_id=? AND a.status='assigned'",(username,target_id)).fetchone()
        if not row or row["target_status"] != "scheduled" or _now() >= _parse_start(row["start_iso"]):
            raise ValueError("Pelimerkin voi poistaa vain ennen kohteen alkamista.")
        conn.execute("UPDATE token_assignments SET status='released',updated_at=? WHERE id=?",(stamp,row["id"]))


def _cancel_target(db_path, target_id):
    stamp = _stamp()
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        target = conn.execute("SELECT * FROM competition_targets WHERE id=?",(target_id,)).fetchone()
        if not target or target["status"] != "scheduled":
            raise ValueError("Kohdetta ei voi perua tässä tilassa.")
        before = _now() < _parse_start(target["start_iso"])
        conn.execute("UPDATE competition_targets SET status='cancelled',cancelled_before_start=?,updated_at=? WHERE id=?",(1 if before else 0,stamp,target_id))
        if before:
            conn.execute("UPDATE token_assignments SET status='refunded',updated_at=? WHERE target_id=? AND status='assigned'",(stamp,target_id))
        else:
            conn.execute("UPDATE token_assignments SET status='spent',updated_at=? WHERE target_id=? AND status='assigned'",(stamp,target_id))


def _save_result(db_path, target_id, home, away):
    stamp = _stamp()
    with connect(db_path) as conn:
        target = conn.execute("SELECT * FROM competition_targets WHERE id=?",(target_id,)).fetchone()
        if not target or target["status"] != "scheduled" or _now() < _parse_start(target["start_iso"]):
            raise ValueError("Tuloksen voi tallentaa vasta kohteen alettua.")
        conn.execute("UPDATE competition_targets SET result_home=?,result_away=?,updated_at=? WHERE id=?",(home,away,stamp,target_id))
        conn.execute("UPDATE token_assignments SET status='spent',updated_at=? WHERE target_id=? AND status='assigned'",(stamp,target_id))


def _competition_standings(conn, competition_id):
    comp, lists = _competition_data(conn,competition_id)
    totals = {}
    by_list = {}
    for lst in lists:
        scores = {}
        targets = conn.execute("SELECT * FROM competition_targets WHERE list_id=? ORDER BY sort_order,id",(lst["id"],)).fetchall()
        for target in targets:
            if target["result_home"] is None or target["result_away"] is None or target["status"] == "cancelled":
                continue
            result = {"home_goals":target["result_home"],"away_goals":target["result_away"]}
            preds = conn.execute("SELECT username,prediction_data FROM user_predictions WHERE target_id=?",(target["id"],)).fetchall()
            for row in preds:
                assignment = conn.execute("SELECT token_type FROM token_assignments WHERE username=? AND target_id=? AND status IN ('assigned','spent')",(row["username"],target["id"])).fetchone()
                points = score_prediction(lst["prediction_type"],json.loads(row["prediction_data"]),result,assignment["token_type"] if assignment else None)
                scores[row["username"]] = scores.get(row["username"],0)+points
        by_list[lst["id"]] = scores
        for username,points in scores.items():
            totals[username] = totals.get(username,0)+points
    bonuses = conn.execute("SELECT username,SUM(points) points FROM competition_bonuses WHERE competition_id=? GROUP BY username",(competition_id,)).fetchall()
    bonus_map={row["username"]:row["points"] for row in bonuses}
    for row in bonuses:
        totals[row["username"]] = totals.get(row["username"],0)+row["points"]
    users = [r["username"] for r in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]
    for username in users:
        totals.setdefault(username,0)
    rankings = sorted(({"username":u,"points":p,"bonus_points":bonus_map.get(u,0)} for u,p in totals.items()),key=lambda e:(-e["points"],e["username"].casefold()))
    rank = 0
    previous = None
    for i,row in enumerate(rankings,1):
        if previous is None or row["points"] != previous:
            rank=i
        row["rank"]=rank
        previous=row["points"]
    return lists,by_list,rankings


def _maximum_prediction_points(prediction_type, token_type=None):
    if prediction_type == "hockey_score":
        return 24 if token_type == "tuplaus" else 12
    if prediction_type == "football_score":
        return 20 if token_type == "tuplaus" else 10
    if prediction_type == "result_1x2":
        return 4 if token_type == "harava" else 5
    if prediction_type in ("hockey_multi", "football_multi"):
        return 11
    return 0


def _competition_performance(conn, competition_id):
    """Raw points and attainable maximum from resolved, non-cancelled targets only."""
    _, lists = _competition_data(conn, competition_id)
    users = [row["username"] for row in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]
    overall = {username: {"points": 0, "max_points": 0} for username in users}
    by_list = {}
    for lst in lists:
        per_list = {username: {"points": 0, "max_points": 0} for username in users}
        targets = conn.execute(
            """SELECT * FROM competition_targets
               WHERE list_id=? AND status!='cancelled'
                 AND result_home IS NOT NULL AND result_away IS NOT NULL
               ORDER BY sort_order,id""",
            (lst["id"],),
        ).fetchall()
        for target in targets:
            result = {"home_goals": target["result_home"], "away_goals": target["result_away"]}
            for username in users:
                token_row = conn.execute(
                    """SELECT token_type FROM token_assignments
                       WHERE username=? AND target_id=? AND status IN ('assigned','spent')""",
                    (username, target["id"]),
                ).fetchone()
                token = token_row["token_type"] if token_row else None
                maximum = _maximum_prediction_points(lst["prediction_type"], token)
                prediction_row = conn.execute(
                    "SELECT prediction_data FROM user_predictions WHERE username=? AND target_id=?",
                    (username, target["id"]),
                ).fetchone()
                points = score_prediction(
                    lst["prediction_type"], json.loads(prediction_row["prediction_data"]), result, token
                ) if prediction_row else 0
                per_list[username]["points"] += points
                per_list[username]["max_points"] += maximum
                overall[username]["points"] += points
                overall[username]["max_points"] += maximum
        by_list[lst["id"]] = per_list
    return {"overall": overall, "lists": by_list}


def get_competition_standings(db_path, competition_id):
    """Return the selected competition and its overall/per-list scoreboards."""
    with connect(db_path) as conn:
        competition, lists = _competition_data(conn, competition_id)
        _, list_points, standings = _competition_standings(conn, competition_id)
        performance = _competition_performance(conn, competition_id)
    return {
        "competition": dict(competition),
        "lists": [dict(lst) for lst in lists],
        "list_points": list_points,
        "standings": standings,
        "performance": performance,
    }


def get_rankable_competitions(db_path):
    """List competitions visible on the user-facing ranking page."""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id,name,status FROM competitions "
            "WHERE status IN ('published','finished','archived') ORDER BY sort_order,id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def _target_label(target):
    if _target_ready(target):
        return f"{target['home']} – {target['away']}"
    return target["display_name"] or "Turnausottelu (osallistujat TBD)"


def render_user_competitions(db_path, username):
    import streamlit as st
    with connect(db_path) as conn:
        competitions = _all_competitions(conn,"published")
    if not competitions:
        st.info("Julkaistuja kilpailuja ei vielä ole.")
        return

    selected_index = 0
    if len(competitions) > 1:
        selected_index = st.selectbox(
            "Kilpailu",
            list(range(len(competitions))),
            format_func=lambda index: competitions[index]["name"],
            key="user_competition_selection",
        )
    comp = competitions[selected_index]
    st.markdown(f"### {comp['name']}")
    if comp["description"]:
        st.caption(comp["description"])

    with connect(db_path) as conn:
        _, lists = _competition_data(conn, comp["id"])
    if not lists:
        st.info("Kilpailussa ei ole listoja.")
        return

    tabs = st.tabs([lst["name"] for lst in lists])
    for idx, lst in enumerate(lists):
        with tabs[idx]:
            token_counts = _list_token_counts(lst)
            list_tokens = " · ".join(
                f"{TOKEN_LABELS[k]} {v}" for k, v in token_counts.items() if v
            ) or "Ei pelimerkkejä"
            st.caption(TYPE_LABELS[lst["prediction_type"]] + " · Pelimerkkimäärät: " + list_tokens)
            with connect(db_path) as conn:
                available = _available_tokens(conn, username, lst)
                targets = conn.execute(
                    "SELECT * FROM competition_targets WHERE list_id=? ORDER BY sort_order,id",
                    (lst["id"],),
                ).fetchall()
            if available:
                remaining_labels = {"tuplaus": "Tuplauksia", "harava": "Haravoita", "jokeri": "Jokereita"}
                st.caption(" · ".join(
                    f"{remaining_labels[k]} jäljellä: {v}" for k, v in available.items()
                ))
            if not targets:
                st.info("Listalla ei ole vielä kohteita.")
            for target in targets:
                open_now = comp["status"] == "published" and _target_open(target)
                start = _parse_start(target["start_iso"]).strftime("%d.%m.%Y %H:%M")
                title = _target_label(target)
                if target["status"] == "cancelled":
                    title += " · Peruttu"
                elif not _target_ready(target):
                    title += " · Osallistujat vahvistamatta"
                with st.container(border=True):
                    title_col, status_col = st.columns([5, 1])
                    with title_col:
                        st.markdown(f"**{title}**")
                        st.caption(f"{start} (Helsinki)")
                    with status_col:
                        st.markdown("🟢 **AVOINNA**" if open_now else "🔒 **SULJETTU**")

                    with connect(db_path) as conn:
                        pred_row = conn.execute(
                            "SELECT prediction_data FROM user_predictions WHERE username=? AND target_id=?",
                            (username, target["id"]),
                        ).fetchone()
                        token_row = conn.execute(
                            "SELECT token_type,status FROM token_assignments WHERE username=? AND target_id=? AND status IN ('assigned','spent')",
                            (username, target["id"]),
                        ).fetchone()
                    list_type = lst["prediction_type"]
                    saved = json.loads(pred_row["prediction_data"]) if pred_row else {}
                    token = token_row["token_type"] if token_row else None
                    token_status = token_row["status"] if token_row else None

                    summary_col, token_col = st.columns([3, 2])
                    with summary_col:
                        st.markdown(f"**Oma veikkaus:** {_prediction_text(list_type, saved, token)}")
                    with token_col:
                        if token:
                            st.markdown(f"🎟️ **Pelimerkki tässä kohteessa: {TOKEN_LABELS[token]}**")
                        elif any(token_counts.values()):
                            st.caption("Pelimerkkiä ei ole käytetty tähän kohteeseen.")

                    if target["result_home"] is not None:
                        real = {"home_goals": target["result_home"], "away_goals": target["result_away"]}
                        own = score_prediction(list_type, saved, real, token) if saved else 0
                        st.caption(f"Tulos {real['home_goals']}–{real['away_goals']} · Oma pistemäärä: {own}")

                    allowed_token = ALLOWED_TOKENS[list_type][0] if ALLOWED_TOKENS[list_type] else None
                    if allowed_token:
                        token_names = {
                            "tuplaus": "Käytä tuplausta",
                            "harava": "Käytä haravaa",
                            "jokeri": "Käytä jokeria",
                        }
                        token_selected = token == allowed_token
                        token_available = available.get(allowed_token, 0) > 0
                        can_change_token = open_now and _target_ready(target) and token_status != "spent"
                        token_choice = st.checkbox(
                            token_names[allowed_token],
                            value=token_selected,
                            key=f"token_checkbox_{target['id']}",
                            disabled=not can_change_token or (not token_selected and not token_available),
                        )
                        if can_change_token and token_choice != token_selected:
                            try:
                                if token_choice:
                                    _assign_token(db_path, username, target["id"], allowed_token)
                                else:
                                    _remove_token(db_path, username, target["id"])
                                st.rerun()
                            except (ValueError, sqlite3.IntegrityError) as exc:
                                st.error(str(exc))

                    if not open_now:
                        continue
                    if not _target_ready(target):
                        st.info("Veikkauksen voi tehdä, kun osapuolet ovat tiedossa.")
                        continue

                    if list_type in ("hockey_score", "football_score"):
                        score_cols = st.columns([1, 0.18, 1])
                        with score_cols[0]:
                            home_goals = st.number_input("Kotimaalit", 0, 30, int(saved.get("home_goals", 0)), key=f"pred_h_{target['id']}")
                        with score_cols[1]:
                            st.markdown("## –")
                        with score_cols[2]:
                            away_goals = st.number_input("Vier maalit", 0, 30, int(saved.get("away_goals", 0)), key=f"pred_a_{target['id']}")
                        prediction = {"home_goals": int(home_goals), "away_goals": int(away_goals)}
                    elif list_type == "result_1x2":
                        options = ["1", "X", "2"]
                        if token == "harava":
                            prediction = {"marks": st.multiselect(
                                "Valitse kaksi merkkiä", options, default=saved.get("marks", ["1", "X"]),
                                key=f"marks_{target['id']}", max_selections=2,
                            )}
                        else:
                            mark = st.radio(
                                "1X2", options, index=options.index(saved.get("mark", "1")),
                                horizontal=True, key=f"mark_{target['id']}",
                            )
                            prediction = {"mark": mark}
                    else:
                        score_count = 4 if list_type == "hockey_multi" else 2
                        scores = []
                        for score_idx in range(score_count):
                            old_scores = saved.get("scores", [])
                            old_score = old_scores[score_idx] if score_idx < len(old_scores) else {}
                            score_cols = st.columns(2)
                            with score_cols[0]:
                                home_goals = st.number_input(
                                    f"Tulos {score_idx + 1} · koti", 0, 30, int(old_score.get("home_goals", 0)),
                                    key=f"mh_{target['id']}_{score_idx}",
                                )
                            with score_cols[1]:
                                away_goals = st.number_input(
                                    f"Tulos {score_idx + 1} · vieras", 0, 30, int(old_score.get("away_goals", 0)),
                                    key=f"ma_{target['id']}_{score_idx}",
                                )
                            scores.append({"home_goals": int(home_goals), "away_goals": int(away_goals)})
                        mark = st.radio(
                            "Monivedon 1X2", ["1", "X", "2"], index=["1", "X", "2"].index(saved.get("mark", "1")),
                            horizontal=True, key=f"mmark_{target['id']}",
                        )
                        prediction = {"scores": scores, "mark": mark}
                        if token == "jokeri":
                            joker = saved.get("joker_score", {})
                            joker_cols = st.columns(2)
                            with joker_cols[0]:
                                joker_home = st.number_input("Jokeri · koti", 0, 30, int(joker.get("home_goals", 0)), key=f"jh_{target['id']}")
                            with joker_cols[1]:
                                joker_away = st.number_input("Jokeri · vieras", 0, 30, int(joker.get("away_goals", 0)), key=f"ja_{target['id']}")
                            prediction["joker_score"] = {"home_goals": int(joker_home), "away_goals": int(joker_away)}
                    if st.button("Tallenna veikkaus", key=f"save_prediction_{target['id']}", type="primary"):
                        try:
                            _save_prediction(db_path, username, target["id"], prediction)
                            st.toast("Veikkaus tallennettu.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))


def render_user_predictions(db_path, username):
    """Show this user's predictions from the new competition system."""
    import streamlit as st
    with connect(db_path) as conn:
        competitions = _all_competitions(conn, "published")
    if not competitions:
        st.info("Julkaistuja kilpailuja ei vielä ole.")
        return

    selected_index = 0
    if len(competitions) > 1:
        selected_index = st.selectbox(
            "Kilpailu",
            list(range(len(competitions))),
            format_func=lambda index: competitions[index]["name"],
            key="my_predictions_competition_selection",
        )
    comp = competitions[selected_index]
    st.markdown(f"### {comp['name']}")
    if comp["description"]:
        st.caption(comp["description"])

    with connect(db_path) as conn:
        _, lists = _competition_data(conn, comp["id"])
    if not lists:
        st.info("Kilpailussa ei ole listoja.")
        return

    tabs = st.tabs([lst["name"] for lst in lists])
    for index, lst in enumerate(lists):
        with tabs[index]:
            with connect(db_path) as conn:
                rows = conn.execute(
                    """SELECT t.*,p.prediction_data,a.token_type,a.status token_status
                       FROM competition_targets t
                       JOIN user_predictions p ON p.target_id=t.id AND p.username=?
                       LEFT JOIN token_assignments a ON a.target_id=t.id AND a.username=?
                            AND a.status IN ('assigned','spent')
                       WHERE t.list_id=? ORDER BY t.sort_order,t.id""",
                    (username, username, lst["id"]),
                ).fetchall()
            if not rows:
                st.info("Et ole vielä tallentanut veikkauksia tälle listalle.")
                continue
            for row in rows:
                target = dict(row)
                prediction = json.loads(target["prediction_data"])
                token = target["token_type"]
                is_open = target["status"] == "scheduled" and _target_open(target)
                status = "🟢 AVOINNA" if is_open else "🔒 SULJETTU"
                if target["status"] == "cancelled":
                    status = "⛔ PERUTTU"
                with st.container(border=True):
                    title_col, status_col = st.columns([5, 1])
                    with title_col:
                        st.markdown(f"**{_target_label(target)}**")
                        st.caption(f"{_parse_start(target['start_iso']).strftime('%d.%m.%Y %H:%M')} (Helsinki)")
                    with status_col:
                        st.markdown(status)
                    st.markdown(f"**Oma veikkaus:** {_prediction_text(lst['prediction_type'], prediction, token)}")
                    if token:
                        st.caption(f"Pelimerkki: {TOKEN_LABELS[token]}")
                    if target["result_home"] is not None and target["status"] != "cancelled":
                        result = {"home_goals": target["result_home"], "away_goals": target["result_away"]}
                        points = score_prediction(lst["prediction_type"], prediction, result, token)
                        if lst["prediction_type"] == "result_1x2":
                            shown_result = _outcome(result["home_goals"], result["away_goals"])
                        else:
                            shown_result = f"{result['home_goals']}–{result['away_goals']}"
                        st.caption(f"Tulos: {shown_result} · Pisteet: {points}")


def render_admin_competitions(db_path, admin_username="admin"):
    import streamlit as st
    st.subheader("Veikkauskisat")
    create, manage = st.tabs(["+ Luo uusi kisa","Kilpailujen hallinta"])
    with create:
        count=st.selectbox("Listojen määrä",[1,2,3,4,5],index=0,key="new_competition_list_count")
        name=st.text_input("Kilpailun nimi",key="new_competition_name")
        description=st.text_area("Kuvaus",key="new_competition_description")
        configured=[]
        for i in range(count):
            st.markdown(f"**Lista {i+1}**")
            c1,c2=st.columns(2)
            lname=c1.text_input("Listan nimi",key=f"new_list_name_{i}",value=f"Lista {i+1}")
            label=c2.selectbox("Veikkausmuoto",list(PREDICTION_TYPES),key=f"new_list_type_{i}")
            ptype=PREDICTION_TYPES[label]
            counts={kind:0 for kind in TOKEN_TYPES}
            for kind in ALLOWED_TOKENS[ptype]:
                counts[kind]=st.number_input(f"{TOKEN_LABELS[kind]}-pelimerkkejä",0,99,0,key=f"new_list_{kind}_{i}")
            configured.append({"name":lname,"prediction_type":ptype,**counts})
        submitted=st.button("Luo luonnos",type="primary",key="create_competition_draft")
        if submitted:
            try:
                cid=_create_competition(db_path,name,description,configured)
                st.success(f"Luonnos luotu. Kilpailun tunniste: {cid}")
            except (ValueError,sqlite3.IntegrityError) as e: st.error(str(e))
    with manage:
        sections=(("draft","Luonnokset"),("published","Julkaistut"),("finished","Päättyneet"),("archived","Arkistoidut"))
        for status,label in sections:
            with connect(db_path) as conn: comps=_all_competitions(conn,status)
            st.markdown(f"### {label}")
            if not comps: st.caption("Ei kilpailuja.")
            for comp in comps:
                with st.expander(f"{comp['name']} · #{comp['id']}"):
                    st.write(comp["description"] or "Ei kuvausta")
                    with connect(db_path) as conn: _,lists=_competition_data(conn,comp["id"])
                    for lst in lists:
                        st.markdown(f"**{lst['sort_order']+1}. {lst['name']}** · {TYPE_LABELS[lst['prediction_type']]} · "+" · ".join(f"{TOKEN_LABELS[k]} {v}" for k,v in _list_token_counts(lst).items()))
                        if status=="draft":
                            with st.form(f"edit_list_{lst['id']}"):
                                c1,c2=st.columns(2)
                                list_name=c1.text_input("Listan nimi",value=lst["name"],key=f"edit_name_{lst['id']}")
                                type_label=c2.selectbox("Veikkausmuoto",list(PREDICTION_TYPES),index=list(PREDICTION_TYPES.values()).index(lst["prediction_type"]),key=f"edit_type_{lst['id']}")
                                new_type=PREDICTION_TYPES[type_label]
                                counts={kind:0 for kind in TOKEN_TYPES}
                                for kind in ALLOWED_TOKENS[new_type]:
                                    counts[kind]=st.number_input(f"{TOKEN_LABELS[kind]}-pelimerkkejä",0,99,int(_list_token_counts(lst)[kind]),key=f"edit_{kind}_{lst['id']}")
                                order=st.number_input("Listan järjestysnumero",0,4,int(lst["sort_order"]),key=f"edit_order_{lst['id']}")
                                save_list=st.form_submit_button("Tallenna listan asetukset")
                            if save_list:
                                try: _update_competition_list(db_path,lst["id"],list_name,new_type,int(order),counts); st.success("Listan asetukset tallennettu."); st.rerun()
                                except ValueError as e: st.error(str(e))
                        with connect(db_path) as conn: targets=conn.execute("SELECT * FROM competition_targets WHERE list_id=? ORDER BY sort_order,id",(lst["id"],)).fetchall()
                        for target in targets:
                            st.caption(f"#{target['sort_order']} {_target_label(target)} · {_parse_start(target['start_iso']).strftime('%d.%m.%Y %H:%M')} · {target['status']}")
                            if status=="published":
                                cols=st.columns([1,1,2])
                                with cols[0]:
                                    rh=st.number_input("Koti",0,30,value=int(target["result_home"] or 0),key=f"result_h_{target['id']}")
                                with cols[1]:
                                    ra=st.number_input("Vieras",0,30,value=int(target["result_away"] or 0),key=f"result_a_{target['id']}")
                                with cols[2]:
                                    if st.button("Tallenna tulos",key=f"save_result_{target['id']}"):
                                        try: _save_result(db_path,target["id"],int(rh),int(ra)); st.rerun()
                                        except ValueError as e: st.error(str(e))
                                if target["status"]=="scheduled" and st.button("Merkitse perutuksi",key=f"cancel_target_{target['id']}"):
                                    try: _cancel_target(db_path,target["id"]); st.rerun()
                                    except ValueError as e: st.error(str(e))
                        if status in ("draft","published"):
                            st.markdown("#### Lisää kohde / TBD-ottelu")
                            with st.form(f"target_form_{lst['id']}"):
                                target_options=[("Uusi kohde",0)]+[(f"Muokkaa: #{t['id']} {_target_label(t)}",t["id"]) for t in targets if _target_open(t)]
                                selected=st.selectbox("Avaa olemassa oleva kohde muokattavaksi tai lisää uusi",target_options,key=f"edit_target_{lst['id']}",format_func=lambda x:x[0])
                                chosen=next((t for t in targets if t["id"]==selected[1]),None)
                                home=st.text_input("Koti / osallistuja 1",value=chosen["home"] if chosen else "")
                                away=st.text_input("Vieras / osallistuja 2",value=chosen["away"] if chosen else "")
                                display=st.text_input("Näyttönimi (esim. Turnausottelu)",value=chosen["display_name"] if chosen else "")
                                start_default=chosen["start_iso"] if chosen else _now().replace(second=0,microsecond=0).isoformat()
                                start=st.text_input("Alkamisaika (Europe/Helsinki, ISO YYYY-MM-DDTHH:MM)",value=start_default)
                                order=st.number_input("Järjestysnumero",0,10000,int(chosen["sort_order"] if chosen else 0),key=f"target_order_{lst['id']}")
                                submitted=st.form_submit_button("Tallenna kohde")
                            if submitted:
                                try:
                                    _save_target(db_path,selected[1] or None,lst["id"],home,away,display,start,int(order))
                                    st.success("Kohde tallennettu.")
                                except (ValueError,sqlite3.IntegrityError) as e: st.error(str(e))
                    with connect(db_path) as conn:
                        preview_lists,_,standings=_competition_standings(conn,comp["id"])
                    with st.expander("Esikatselu / pisteet",expanded=False):
                        for lst in preview_lists:
                            st.write(f"**{lst['name']}** · {TYPE_LABELS[lst['prediction_type']]} · pelimerkit "+", ".join(f"{TOKEN_LABELS[k]} {v}" for k,v in _list_token_counts(lst).items()))
                            with connect(db_path) as conn: rows=conn.execute("SELECT * FROM competition_targets WHERE list_id=? ORDER BY sort_order,id",(lst["id"],)).fetchall()
                            for target in rows:
                                st.write(f"{_target_label(target)} · {_parse_start(target['start_iso']).strftime('%d.%m.%Y %H:%M')} (Helsinki)")
                        for row in standings:
                            bonus=f" (sis. {row['bonus_points']:+d} bonus)" if row["bonus_points"] else ""
                            st.write(f"{row['rank']}. {row['username']} · {row['points']} p{bonus}")
                    if status=="draft" and st.button("✅ Vahvista julkaisu",key=f"publish_{comp['id']}",type="primary"):
                        try: _publish(db_path,comp["id"]); st.success("Kilpailu julkaistu."); st.rerun()
                        except ValueError as e: st.error(str(e))
                    if status=="published":
                        with connect(db_path) as conn: users=[r["username"] for r in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]
                        if lists and users:
                            st.markdown("#### Listabonukset")
                            with st.form(f"bonus_form_{comp['id']}"):
                                list_choice=st.selectbox("Lista",[(l["name"],l["id"]) for l in lists],format_func=lambda x:x[0],key=f"bonus_list_{comp['id']}")
                                first=st.selectbox("1. sija · +5",[""]+users,key=f"bonus1_{comp['id']}")
                                second=st.selectbox("2. sija · +3",[""]+users,key=f"bonus2_{comp['id']}")
                                third=st.selectbox("3. sija · +1",[""]+users,key=f"bonus3_{comp['id']}")
                                ok=st.form_submit_button("Tallenna valitut bonukset")
                            if ok:
                                assignments=[(first,5),(second,3),(third,1)]
                                chosen=[u for u,_ in assignments if u]
                                if len(chosen)!=len(set(chosen)): st.error("Sama käyttäjä voi saada vain yhden sijoituksen tällä listalla.")
                                elif chosen:
                                    with connect(db_path) as conn:
                                        conn.executemany("""INSERT INTO competition_bonuses(competition_id,list_id,username,points,reason,created_at,created_by)
                                            VALUES(?,?,?,?,?,?,?) ON CONFLICT(competition_id,list_id,username) DO UPDATE SET
                                            points=excluded.points,reason=excluded.reason,created_at=excluded.created_at,created_by=excluded.created_by""",
                                            [(comp['id'],list_choice[1],u,p,f"{p} pisteen sijoitusbonus · {list_choice[0]}",_stamp(),admin_username) for u,p in assignments if u])
                                    st.success("Bonukset tallennettu."); st.rerun()
                        if st.button("Päätä kilpailu",key=f"finish_{comp['id']}"):
                            with connect(db_path) as conn: conn.execute("UPDATE competitions SET status='finished',updated_at=? WHERE id=?",(_stamp(),comp['id']))
                            st.rerun()
                    if status=="finished" and st.button("Arkistoi kilpailu",key=f"archive_{comp['id']}"):
                        with connect(db_path) as conn: conn.execute("UPDATE competitions SET status='archived',updated_at=? WHERE id=?",(_stamp(),comp['id']))
                        st.rerun()


def render_admin_competition_results(db_path):
    """Enter/correct results and cancel targets for the new competition system."""
    import streamlit as st
    with connect(db_path) as conn:
        competitions = conn.execute(
            "SELECT * FROM competitions WHERE status IN ('published','finished','archived') ORDER BY sort_order DESC,id DESC"
        ).fetchall()
    if not competitions:
        st.info("Julkaistuja kilpailuja ei vielä ole.")
        return

    comp_index = st.selectbox(
        "Kilpailu",
        list(range(len(competitions))),
        format_func=lambda index: f"{competitions[index]['name']} · {competitions[index]['status']}",
        key="competition_result_competition",
    )
    comp = competitions[comp_index]
    with connect(db_path) as conn:
        _, lists = _competition_data(conn, comp["id"])
    if not lists:
        st.info("Kilpailussa ei ole listoja.")
        return

    list_index = st.selectbox(
        "Lista",
        list(range(len(lists))),
        format_func=lambda index: lists[index]["name"],
        key=f"competition_result_list_{comp['id']}",
    )
    lst = lists[list_index]
    with connect(db_path) as conn:
        targets = conn.execute(
            "SELECT * FROM competition_targets WHERE list_id=? ORDER BY sort_order,id",
            (lst["id"],),
        ).fetchall()
    if not targets:
        st.info("Listalla ei ole kohteita.")
        return

    st.markdown(f"### {comp['name']} · {lst['name']}")
    st.caption(TYPE_LABELS[lst["prediction_type"]])
    for target in targets:
        target = dict(target)
        starts_at = _parse_start(target["start_iso"])
        if target["status"] == "cancelled":
            status_label = "Peruttu ennen alkua" if target["cancelled_before_start"] else "Peruttu alkamisen jälkeen"
        elif _now() >= starts_at:
            status_label = "Suljettu"
        else:
            status_label = "Avoinna"

        with st.container(border=True):
            st.markdown(f"**{_target_label(target)}**")
            st.caption(f"{starts_at.strftime('%d.%m.%Y %H:%M')} (Helsinki) · {status_label}")
            if target["result_home"] is not None:
                if lst["prediction_type"] == "result_1x2":
                    current_result = _outcome(target["result_home"], target["result_away"])
                    st.caption(f"Tallennettu tulos: {current_result}")
                else:
                    st.caption(f"Tallennettu tulos: {target['result_home']}–{target['result_away']}")
            elif target["status"] != "cancelled":
                st.caption("Tulosta ei ole vielä syötetty.")

            if target["status"] != "scheduled":
                continue

            can_enter_result = _now() >= starts_at
            if lst["prediction_type"] == "result_1x2":
                current = _outcome(target["result_home"], target["result_away"]) if target["result_home"] is not None else "1"
                choice = st.selectbox(
                    "Tulos (1X2)", ["1", "X", "2"],
                    index=["1", "X", "2"].index(current),
                    key=f"result_outcome_{target['id']}", disabled=not can_enter_result,
                )
                # The existing common result fields store a representative score whose 1X2 outcome matches.
                result_scores = {"1": (1, 0), "X": (0, 0), "2": (0, 1)}
                home, away = result_scores[choice]
            else:
                if lst["prediction_type"] in ("hockey_multi", "football_multi"):
                    st.caption("Syötä ottelun lopullinen tulos; Monivedon useat veikkaukset pisteytetään sitä vasten.")
                result_cols = st.columns(2)
                with result_cols[0]:
                    home = st.number_input(
                        "Kotijoukkueen maalit", 0, 99,
                        value=int(target["result_home"] or 0), key=f"competition_result_home_{target['id']}",
                        disabled=not can_enter_result,
                    )
                with result_cols[1]:
                    away = st.number_input(
                        "Vierasjoukkueen maalit", 0, 99,
                        value=int(target["result_away"] or 0), key=f"competition_result_away_{target['id']}",
                        disabled=not can_enter_result,
                    )

            if not can_enter_result:
                st.caption("Tuloksen voi tallentaa kohteen alkamisen jälkeen.")
            elif st.button("Tallenna tulos", key=f"competition_save_result_{target['id']}", type="primary"):
                try:
                    _save_result(db_path, target["id"], int(home), int(away))
                    st.success("Tulos tallennettu. Kilpailun pisteet ja ranking päivittyvät.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

            if comp["status"] == "published" and st.button("Merkitse kohde perutuksi", key=f"competition_cancel_target_{target['id']}"):
                try:
                    _cancel_target(db_path, target["id"])
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
