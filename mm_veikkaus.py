import streamlit as st
import pandas as pd
import json
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import bcrypt
import html
import zipfile
import io
import streamlit.components.v1 as components

# ====================== PERUSASETUKSET ======================
HELSINKI = ZoneInfo("Europe/Helsinki")
st.set_page_config(page_title="Haamuhanska", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

def get_secret(key, env_key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(env_key, default)

SITE_PASSWORD = get_secret("site_password", "SITE_PASSWORD")
ADMIN_PASSWORD = get_secret("admin_password", "ADMIN_PASSWORD")
DB_FILE = os.environ.get("DB_PATH", "veikkaus.db")

if not SITE_PASSWORD or not ADMIN_PASSWORD:
    st.error("SITE_PASSWORD ja ADMIN_PASSWORD pitää olla asetettu (Render environment / st.secrets).")
    st.stop()

# ====================== TYYLIT ======================
st.markdown("""
<style>
:root {
    --bg: #0b1120; --card: #111827; --card-hover: #1e293b; --border: #1e293b;
    --border-light: #334155; --accent: #22c55e; --text: #e2e8f0; --muted: #94a3b8;
}
.stApp { background-color: var(--bg) !important; color: var(--text); }
.main .block-container { max-width: 1100px !important; padding-top: 1.4rem !important; padding-bottom: 2.5rem !important; }
section[data-testid="stSidebar"] {
    background-image: linear-gradient(rgba(30,41,59,0.72), rgba(15,23,42,0.85)), url("https://i.imgur.com/gvrq6iO.jpeg") !important;
    background-size: cover !important; background-position: center bottom !important;
    background-color: #1e293b !important; border-right: 1px solid var(--border-light) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { height:0!important; min-height:0!important; padding:0!important; margin:0!important; overflow:hidden!important; }
section[data-testid="stSidebar"] .stRadio > div, section[data-testid="stSidebar"] .stAlert,
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: rgba(17,24,39,0.9) !important; border: 1px solid var(--border-light) !important; border-radius: 14px !important;
}
.page-header { background: linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #22c55e; border-radius:14px; padding:16px 20px; margin-bottom:22px; }
.page-header h2 { margin:0; color:#f1f5f9; font-size:1.45rem; font-weight:700; }
.page-header p { margin:6px 0 0; color:#94a3b8; font-size:0.95rem; }
.rank-bar-bg { height:4px; background:#1e293b; border-radius:4px; overflow:hidden; }
.rank-bar-fill { height:100%; background:linear-gradient(90deg,#16a34a,#22c55e); border-radius:4px; }
button[kind="primary"] {
    background-color: #16a34a !important; color: #ffffff !important; border: 1px solid #16a34a !important;
}
button[kind="primary"]:hover {
    background-color: #15803d !important; border-color: #15803d !important; color: #ffffff !important;
}
button[kind="primary"]:focus { box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.4) !important; }

/* ===== MOBIILIOPTIMOINTI ===== */
@media (max-width:768px) {
    .etusivu-otsikko { font-size:1.45rem !important; white-space:normal !important; letter-spacing:1px !important; }
    .main .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-top: 0.8rem !important; }
    .page-header { padding: 10px 12px; margin-bottom: 14px; }
    .page-header h2 { font-size: 1.15rem; }
    .page-header p { font-size: 0.85rem; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    .stSelectbox, .stMultiSelect, .stRadio { font-size: 0.9rem !important; }
    button { min-height: 44px !important; }
    .rank-bar-bg { height: 3px; }
}
@media (max-width:480px) {
    .etusivu-otsikko { font-size:1.25rem !important; }
    .main .block-container { padding-left: 0.4rem !important; padding-right: 0.4rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ====================== TIETOKANTA ======================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS predictions (
        username TEXT,
        match_id TEXT,
        prediction TEXT,
        is_special INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (username, match_id, is_special)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS point_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        points INTEGER NOT NULL,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS real_results (
        result_type TEXT,
        id TEXT,
        result TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (result_type, id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        edited_at TEXT,
        parent_id INTEGER DEFAULT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comment_reactions (
        comment_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        reaction TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (comment_id, username, reaction)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        list_key TEXT NOT NULL,
        list_name TEXT NOT NULL,
        home TEXT NOT NULL,
        away TEXT NOT NULL,
        aika TEXT NOT NULL,
        start_iso TEXT NOT NULL,
        is_double INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        pred_type TEXT DEFAULT 'normal'
    )''')

    try:
        c.execute("ALTER TABLE comments ADD COLUMN parent_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    c.execute("CREATE INDEX IF NOT EXISTS idx_pred_user_match ON predictions(username, match_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pred_match ON predictions(match_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_results_id ON real_results(id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_adj_user ON point_adjustments(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_comments_created ON comments(created_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_matches_list ON matches(list_key, sort_order)")

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# ====================== SEED-OTTELUT (ensimmäinen käynnistys) ======================
SEED_MATCHES = {
    "liiga": {
        "name": "Lista 1 – SM-Liiga",
        "pred_type": "normal",
        "matches": [
            {"id":"l1_1","home":"KalPa","away":"HPK","aika":"Ti 15.9. 18:30","start":"2026-09-15T18:30:00","double":False},
            {"id":"l1_2","home":"Pelicans","away":"Tappara","aika":"Ti 15.9. 18:30","start":"2026-09-15T18:30:00","double":False},
            {"id":"l1_3","home":"SaiPa","away":"K-Espoo","aika":"Ti 15.9. 18:30","start":"2026-09-15T18:30:00","double":False},
            {"id":"l1_4","home":"TPS","away":"Jukurit","aika":"Ti 15.9. 18:30","start":"2026-09-15T18:30:00","double":False},
            {"id":"l1_5","home":"Ässät","away":"Sport","aika":"Ti 15.9. 18:30","start":"2026-09-15T18:30:00","double":False},
            {"id":"l1_6","home":"HIFK","away":"Jukurit","aika":"Ke 16.9. 18:30","start":"2026-09-16T18:30:00","double":False},
            {"id":"l1_7","home":"KooKoo","away":"JYP","aika":"Ke 16.9. 18:30","start":"2026-09-16T18:30:00","double":False},
            {"id":"l1_8","home":"Kärpät","away":"Ilves","aika":"Ke 16.9. 18:30","start":"2026-09-16T18:30:00","double":True},
            {"id":"l1_9","home":"Jokerit","away":"JYP","aika":"To 17.9. 18:30","start":"2026-09-17T18:30:00","double":False},
            {"id":"l1_10","home":"Lukko","away":"Sport","aika":"To 17.9. 18:30","start":"2026-09-17T18:30:00","double":False},
            {"id":"l1_11","home":"TPS","away":"Tappara","aika":"To 17.9. 18:30","start":"2026-09-17T18:30:00","double":False},
            {"id":"l1_12","home":"Jukurit","away":"Pelicans","aika":"Pe 18.9. 18:30","start":"2026-09-18T18:30:00","double":False},
            {"id":"l1_13","home":"KalPa","away":"Ilves","aika":"Pe 18.9. 18:30","start":"2026-09-18T18:30:00","double":False},
            {"id":"l1_14","home":"KooKoo","away":"SaiPa","aika":"Pe 18.9. 19:30","start":"2026-09-18T19:30:00","double":False},
        ],
    },
    "valioliiga": {
        "name": "Lista 2 – Valioliiga",
        "pred_type": "normal",
        "matches": [
            {"id":"l2_1","home":"Brentford","away":"Chelsea","aika":"Pe 18.9. 22:00","start":"2026-09-18T22:00:00","double":False},
            {"id":"l2_2","home":"Spurs","away":"Aston Villa","aika":"La 19.9. 14:30","start":"2026-09-19T14:30:00","double":True},
            {"id":"l2_3","home":"Brighton","away":"Arsenal","aika":"La 19.9. 17:00","start":"2026-09-19T17:00:00","double":False},
            {"id":"l2_4","home":"Everton","away":"Ipswich","aika":"La 19.9. 17:00","start":"2026-09-19T17:00:00","double":False},
            {"id":"l2_5","home":"Leeds","away":"Crystal Palace","aika":"La 19.9. 17:00","start":"2026-09-19T17:00:00","double":False},
            {"id":"l2_6","home":"Man City","away":"Sunderland","aika":"La 19.9. 17:00","start":"2026-09-19T17:00:00","double":False},
            {"id":"l2_7","home":"Newcastle","away":"Hull City","aika":"La 19.9. 17:00","start":"2026-09-19T17:00:00","double":False},
            {"id":"l2_8","home":"Nott'm Forest","away":"Coventry","aika":"La 19.9. 19:30","start":"2026-09-19T19:30:00","double":False},
            {"id":"l2_9","home":"Bournemouth","away":"Liverpool","aika":"Su 20.9. 16:00","start":"2026-09-20T16:00:00","double":False},
            {"id":"l2_10","home":"Fulham","away":"Man Utd","aika":"Su 20.9. 18:30","start":"2026-09-20T18:30:00","double":False},
        ],
    },
    "euro": {
        "name": "Lista 3 – Europelien helmiä",
        "pred_type": "normal",
        "matches": [
            {"id":"l3_1","home":"Bayern","away":"Union Berlin","aika":"Pe 18.9. 21:30","start":"2026-09-18T21:30:00","double":False},
            {"id":"l3_2","home":"Roma","away":"Inter","aika":"La 19.9. 19:00","start":"2026-09-19T19:00:00","double":False},
            {"id":"l3_3","home":"Celtic","away":"Rangers","aika":"Su 20.9. 14:00","start":"2026-09-20T14:00:00","double":False},
            {"id":"l3_4","home":"Leverkusen","away":"RB Leipzig","aika":"Su 20.9. 16:30","start":"2026-09-20T16:30:00","double":False},
            {"id":"l3_5","home":"PSV","away":"Twente","aika":"Su 20.9. 17:45","start":"2026-09-20T17:45:00","double":False},
            {"id":"l3_6","home":"Porto","away":"Benfica","aika":"Su 20.9. 18:00","start":"2026-09-20T18:00:00","double":False},
            {"id":"l3_7","home":"Juventus","away":"Atalanta","aika":"Su 20.9. 19:00","start":"2026-09-20T19:00:00","double":False},
            {"id":"l3_8","home":"Marseille","away":"PSG","aika":"Su 20.9. 21:45","start":"2026-09-20T21:45:00","double":False},
            {"id":"l3_9","home":"Atlético","away":"Real Madrid","aika":"Su 20.9. 22:00","start":"2026-09-20T22:00:00","double":True},
            {"id":"l3_10","home":"Sevilla","away":"Barcelona","aika":"Su 20.9. 22:00","start":"2026-09-20T22:00:00","double":False},
        ],
    },
    "nations": {
        "name": "Lista 4 – Kansojen liiga",
        "pred_type": "normal",
        "matches": [
            {"id":"l4_1","home":"Alankomaat","away":"Saksa","aika":"To 24.9. 21:45","start":"2026-09-24T21:45:00","double":False},
            {"id":"l4_2","home":"Norja","away":"Tanska","aika":"To 24.9. 21:45","start":"2026-09-24T21:45:00","double":False},
            {"id":"l4_3","home":"Portugali","away":"Wales","aika":"To 24.9. 21:45","start":"2026-09-24T21:45:00","double":False},
            {"id":"l4_4","home":"Italia","away":"Belgia","aika":"Pe 25.9. 21:45","start":"2026-09-25T21:45:00","double":False},
            {"id":"l4_5","home":"Turkki","away":"Ranska","aika":"Pe 25.9. 21:45","start":"2026-09-25T21:45:00","double":False},
            {"id":"l4_6","home":"San Marino","away":"Suomi","aika":"La 26.9. 19:00","start":"2026-09-26T19:00:00","double":True},
            {"id":"l4_7","home":"Englanti","away":"Espanja","aika":"La 26.9. 21:45","start":"2026-09-26T21:45:00","double":False},
            {"id":"l4_8","home":"Norja","away":"Portugali","aika":"Su 27.9. 21:45","start":"2026-09-27T21:45:00","double":False},
            {"id":"l4_9","home":"Saksa","away":"Kreikka","aika":"Su 27.9. 21:45","start":"2026-09-27T21:45:00","double":False},
            {"id":"l4_10","home":"Belgia","away":"Ranska","aika":"Ma 28.9. 21:45","start":"2026-09-28T21:45:00","double":False},
        ],
    },
    "nhl": {
        "name": "Lista 5 – NHL-Tusina",
        "pred_type": "nhl",
        "matches": [
            {"id":"l5_1","home":"Florida","away":"Carolina","aika":"Ti 29.9. 00:00","start":"2026-09-29T00:00:00","double":True},
            {"id":"l5_2","home":"Toronto","away":"Montreal","aika":"Ti 29.9. 02:00","start":"2026-09-29T02:00:00","double":False},
            {"id":"l5_3","home":"Boston","away":"NY Rangers","aika":"Ti 29.9. 03:00","start":"2026-09-29T03:00:00","double":False},
            {"id":"l5_4","home":"Edmonton","away":"Vancouver","aika":"Ti 29.9. 05:00","start":"2026-09-29T05:00:00","double":False},
            {"id":"l5_5","home":"Vegas","away":"Chicago","aika":"Ti 29.9. 05:30","start":"2026-09-29T05:30:00","double":False},
            {"id":"l5_6","home":"Philadelphia","away":"Pittsburgh","aika":"Ke 30.9. 02:30","start":"2026-09-30T02:30:00","double":False},
            {"id":"l5_7","home":"Toronto","away":"NY Islanders","aika":"Ke 30.9. 02:30","start":"2026-09-30T02:30:00","double":False},
            {"id":"l5_8","home":"Colorado","away":"LA Kings","aika":"Ke 30.9. 05:00","start":"2026-09-30T05:00:00","double":False},
            {"id":"l5_9","home":"New Jersey","away":"Philadelphia","aika":"To 1.10. 02:00","start":"2026-10-01T02:00:00","double":False},
            {"id":"l5_10","home":"NY Rangers","away":"Tampa Bay","aika":"To 1.10. 02:00","start":"2026-10-01T02:00:00","double":False},
            {"id":"l5_11","home":"Columbus","away":"Buffalo","aika":"To 1.10. 02:00","start":"2026-10-01T02:00:00","double":False},
            {"id":"l5_12","home":"Nashville","away":"Minnesota","aika":"To 1.10. 03:00","start":"2026-10-01T03:00:00","double":False},
        ],
    },
}

def seed_matches_if_empty():
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM matches").fetchone()["c"]
        if cnt > 0:
            return
        order = 0
        for list_key, info in SEED_MATCHES.items():
            for m in info["matches"]:
                order += 1
                conn.execute(
                    "INSERT OR REPLACE INTO matches (id, list_key, list_name, home, away, aika, start_iso, is_double, sort_order, pred_type) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (m["id"], list_key, info["name"], m["home"], m["away"], m["aika"], m["start"],
                     1 if m.get("double") else 0, order, info["pred_type"])
                )

seed_matches_if_empty()

@st.cache_data(ttl=30)
def load_all_match_lists():
    """Palauttaa [(list_name, matches_list), ...] ja list_key-järjestyksen."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM matches ORDER BY sort_order, id"
        ).fetchall()
    lists = {}
    order_keys = []
    for r in rows:
        key = r["list_key"]
        if key not in lists:
            lists[key] = {"name": r["list_name"], "pred_type": r["pred_type"], "matches": []}
            order_keys.append(key)
        start = datetime.fromisoformat(r["start_iso"]).replace(tzinfo=HELSINKI)
        lists[key]["matches"].append({
            "id": r["id"],
            "home": r["home"],
            "away": r["away"],
            "aika": r["aika"],
            "start": start,
            "double": bool(r["is_double"]),
            "pred_type": r["pred_type"],
            "list_key": key,
        })
    return [(lists[k]["name"], lists[k]["matches"]) for k in order_keys], lists

def get_match_lists():
    all_lists, _ = load_all_match_lists()
    return all_lists

def get_matches_by_list_key(list_key):
    _, by_key = load_all_match_lists()
    return by_key.get(list_key, {}).get("matches", [])

def clear_matches_cache():
    load_all_match_lists.clear()

# ====================== APUFUNKTIOT ======================
def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()

def check_password(pw, hashed):
    if not hashed:
        return False
    try:
        if hashed.startswith("$2"):
            return bcrypt.checkpw(pw.encode(), hashed.encode())
        return hashlib.sha256(pw.encode()).hexdigest() == hashed
    except Exception:
        return False

def save_prediction(username, match_id, pred, is_special=0):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO predictions (username, match_id, prediction, is_special, created_at) VALUES (?,?,?,?,?)",
            (username, str(match_id), json.dumps(pred, ensure_ascii=False), is_special, datetime.now(HELSINKI).isoformat())
        )

def load_prediction(username, match_id, is_special=0):
    with get_db() as conn:
        row = conn.execute(
            "SELECT prediction FROM predictions WHERE username=? AND match_id=? AND is_special=?",
            (username, str(match_id), is_special)
        ).fetchone()
    return json.loads(row["prediction"]) if row else None

def load_user_predictions(username):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT match_id, prediction FROM predictions WHERE username=? AND is_special=0",
            (username,)
        ).fetchall()
    return {str(r["match_id"]): json.loads(r["prediction"]) for r in rows}

def load_all_predictions_for_match(match_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, prediction FROM predictions WHERE match_id=? AND is_special=0",
            (str(match_id),)
        ).fetchall()
    return {r["username"]: json.loads(r["prediction"]) for r in rows}

def count_predictions_for_match(match_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT COUNT(*) as cnt FROM predictions WHERE match_id=? AND is_special=0",
            (str(match_id),)
        ).fetchone()["cnt"]

def save_real_result(result_type, result_id, result):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO real_results (result_type, id, result, updated_at) VALUES (?,?,?,?)",
            (result_type, str(result_id), json.dumps(result, ensure_ascii=False), datetime.now(HELSINKI).isoformat())
        )
    clear_points_cache()

def load_real_result(result_type, result_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT result FROM real_results WHERE result_type=? AND id=?",
            (result_type, str(result_id))
        ).fetchone()
    return json.loads(row["result"]) if row else None

def delete_real_result(result_type, result_id):
    with get_db() as conn:
        conn.execute("DELETE FROM real_results WHERE result_type=? AND id=?", (result_type, str(result_id)))
    clear_points_cache()

def add_point_adjustment(username, points, reason, created_by):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO point_adjustments (username, points, reason, created_at, created_by) VALUES (?,?,?,?,?)",
            (username, int(points), reason or "", datetime.now(HELSINKI).isoformat(), created_by)
        )
    clear_points_cache()

def get_adjustment_total(username):
    with get_db() as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(points),0) as total FROM point_adjustments WHERE username=?",
            (username,)
        ).fetchone()["total"]

def get_user_adjustments(username):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM point_adjustments WHERE username=? ORDER BY created_at DESC",
            (username,)
        ).fetchall()

def delete_point_adjustment(adj_id):
    with get_db() as conn:
        conn.execute("DELETE FROM point_adjustments WHERE id=?", (adj_id,))
    clear_points_cache()

def add_comment(username, text, parent_id=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (username, text, created_at, parent_id) VALUES (?,?,?,?)",
            (username, text, datetime.now(HELSINKI).isoformat(), parent_id)
        )

def count_root_comments():
    with get_db() as conn:
        return conn.execute(
            "SELECT COUNT(*) as c FROM comments WHERE parent_id IS NULL"
        ).fetchone()["c"]

def get_root_comments_page(page=1, per_page=5):
    offset = (page - 1) * per_page
    with get_db() as conn:
        roots = conn.execute(
            "SELECT * FROM comments WHERE parent_id IS NULL ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        if not roots:
            return []
        root_ids = [r["id"] for r in roots]
        placeholders = ",".join("?" * len(root_ids))
        replies = conn.execute(
            f"SELECT * FROM comments WHERE parent_id IN ({placeholders}) ORDER BY created_at ASC",
            root_ids
        ).fetchall()
    by_id = {c["id"]: dict(c) for c in roots}
    for c in by_id.values():
        c["replies"] = []
    for r in replies:
        pid = r["parent_id"]
        if pid in by_id:
            by_id[pid]["replies"].append(dict(r))
    return [by_id[r["id"]] for r in roots]

def get_comments_latest(limit=3):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM comments WHERE parent_id IS NULL ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

def update_comment(cid, text):
    with get_db() as conn:
        conn.execute(
            "UPDATE comments SET text=?, edited_at=? WHERE id=?",
            (text, datetime.now(HELSINKI).isoformat(), cid)
        )

def delete_comment(cid):
    with get_db() as conn:
        conn.execute("DELETE FROM comment_reactions WHERE comment_id=?", (cid,))
        replies = conn.execute("SELECT id FROM comments WHERE parent_id=?", (cid,)).fetchall()
        for r in replies:
            conn.execute("DELETE FROM comment_reactions WHERE comment_id=?", (r["id"],))
            conn.execute("DELETE FROM comments WHERE id=?", (r["id"],))
        conn.execute("DELETE FROM comments WHERE id=?", (cid,))

def delete_all_comments():
    with get_db() as conn:
        conn.execute("DELETE FROM comment_reactions")
        conn.execute("DELETE FROM comments")

def get_1x2(h, a):
    return "1" if h > a else "2" if h < a else "X"

def calculate_match_points(pred, real, double=False):
    if not pred or not real:
        return 0
    if "mark" in pred:
        rh, ra = real.get("home_goals"), real.get("away_goals")
        if rh is None or ra is None:
            return 0
        pts = 7 if rh in pred.get("home_opts", []) and ra in pred.get("away_opts", []) else 0
        if pred.get("mark") == get_1x2(rh, ra):
            pts += 3
        return pts * 2 if double else pts
    ph, pa = pred.get("home_goals"), pred.get("away_goals")
    rh, ra = real.get("home_goals"), real.get("away_goals")
    if None in (ph, pa, rh, ra):
        return 0
    if get_1x2(ph, pa) != get_1x2(rh, ra):
        return 0
    if ph == rh and pa == ra:
        pts = 10
    elif (ph == rh and abs(pa - ra) == 1) or (pa == ra and abs(ph - rh) == 1):
        pts = 7
    elif ph == rh or pa == ra:
        pts = 6
    elif get_1x2(ph, pa) == "X":
        pts = 5
    else:
        pts = 4
    return pts * 2 if double else pts

def page_header(title, subtitle=None):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="page-header"><h2>{title}</h2>{sub}</div>', unsafe_allow_html=True)

def summary_card(title, value, subtitle=""):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #22c55e;border-radius:14px;padding:18px 20px;margin-bottom:18px;text-align:center;">
        <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:4px;">{title}</div>
        <div style="font-size:1.7rem;font-weight:700;color:#22c55e;">{value}</div>
        <div style="font-size:0.85rem;color:#64748b;margin-top:4px;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def render_ranking_row(i, name, points, pct, is_me=False):
    bg = "rgba(34,197,94,0.14)" if is_me else "rgba(30,41,59,0.55)"
    border = "#22c55e" if is_me else "#1e293b"
    name_col = "#22c55e" if is_me else "#e2e8f0"
    weight = "700" if is_me else "500"
    safe_name = html.escape(str(name))
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border};border-radius:12px;'
        f'padding:12px 14px;margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="color:#64748b;min-width:1.8rem;font-weight:700;font-size:1.05rem;">{i}.</span>'
        f'<span style="color:{name_col};font-weight:{weight};">{safe_name}</span>'
        f'</div>'
        f'<span style="font-weight:700;color:#22c55e;font-size:1.15rem;">{points}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:7px;">'
        f'<div class="rank-bar-bg" style="flex:1;">'
        f'<div class="rank-bar-fill" style="width:{int(pct)}%;"></div></div>'
        f'<span style="font-size:0.75rem;color:#94a3b8;min-width:32px;text-align:right;">{int(pct)}%</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def render_hof_card(medal, color, bg, name, points, pct):
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {color};border-radius:14px;padding:16px 20px;margin-bottom:12px;max-width:480px;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:14px;">
                <span style="font-size:1.7rem;">{medal}</span>
                <div style="font-size:1.2rem;font-weight:700;color:#f1f5f9;">{html.escape(name)}</div>
            </div>
            <div style="font-size:1.35rem;font-weight:700;color:#22c55e;">{points} p</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:10px;">
            <div class="rank-bar-bg" style="flex:1;"><div class="rank-bar-fill" style="width:{pct}%;"></div></div>
            <span style="font-size:0.75rem;color:#94a3b8;min-width:32px;text-align:right;">{pct}%</span>
        </div>
    </div>""", unsafe_allow_html=True)

def big_title(text, size="2.9rem"):
    st.markdown(f"""
    <div class="etusivu-container" style="height:18vh;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;text-align:center;">
        <h1 class="etusivu-otsikko" style="font-family:'Cinzel',serif;font-size:{size};font-weight:700;color:#f1f5f9;letter-spacing:2px;
            text-shadow:0 0 12px rgba(34,197,94,0.35),0 0 28px rgba(34,197,94,0.15);margin:0;white-space:nowrap;">{text}</h1>
    </div>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

def format_pred_text(pred):
    if not pred:
        return "—"
    if "mark" in pred:
        combos = ", ".join(f"{h}–{a}" for h in pred.get("home_opts", []) for a in pred.get("away_opts", [])) or "–"
        return f"1X2:{pred.get('mark')} | {combos}"
    return f"{pred.get('home_goals')}–{pred.get('away_goals')}"

def render_countdown(match_id, start_dt):
    """Reaaliaikainen countdown JS:llä."""
    ts = int(start_dt.timestamp() * 1000)
    components.html(f"""
    <div id="cd_{match_id}" style="font-size:0.88rem;color:#94a3b8;margin-bottom:4px;"></div>
    <script>
    (function(){{
        const el = document.getElementById("cd_{match_id}");
        const target = {ts};
        function pad(n){{ return n < 10 ? "0"+n : n; }}
        function tick(){{
            const now = Date.now();
            let diff = Math.max(0, target - now);
            if(diff <= 0){{ el.innerHTML = "Aikaa: <b style='color:#f87171;'>SULJETTU</b>"; return; }}
            const d = Math.floor(diff / 86400000);
            diff %= 86400000;
            const h = Math.floor(diff / 3600000);
            diff %= 3600000;
            const m = Math.floor(diff / 60000);
            const s = Math.floor((diff % 60000) / 1000);
            const txt = d > 0
                ? d + " pv " + pad(h) + ":" + pad(m) + ":" + pad(s)
                : pad(h) + ":" + pad(m) + ":" + pad(s);
            el.innerHTML = "Aikaa: <b style='color:#22c55e;'>" + txt + "</b>";
            setTimeout(tick, 1000);
        }}
        tick();
    }})();
    </script>
    """, height=28)

# ====================== VÄLIMUISTI & BULK-PISTEET ======================
@st.cache_data(ttl=60)
def get_full_points_data():
    all_lists, _ = load_all_match_lists()
    match_lists = [matches for _, matches in all_lists]
    all_matches = [m for lst in match_lists for m in lst]

    with get_db() as conn:
        users = [r["username"] for r in conn.execute("SELECT username FROM users").fetchall()]
        pred_rows = conn.execute(
            "SELECT username, match_id, prediction FROM predictions WHERE is_special=0"
        ).fetchall()
        result_rows = conn.execute(
            "SELECT id, result FROM real_results WHERE result_type='match'"
        ).fetchall()
        adj_rows = conn.execute(
            "SELECT username, COALESCE(SUM(points),0) as total FROM point_adjustments GROUP BY username"
        ).fetchall()

    pred_map = {(r["username"], str(r["match_id"])): json.loads(r["prediction"]) for r in pred_rows}
    result_map = {str(r["id"]): json.loads(r["result"]) for r in result_rows}
    adj_map = {r["username"]: r["total"] for r in adj_rows}

    user_stats = {}
    for u in users:
        total = adj_map.get(u, 0)
        list_pts = [0] * len(match_lists)
        list_pct = [0] * len(match_lists)

        for li, matches in enumerate(match_lists):
            up = mp = 0
            for m in matches:
                pred = pred_map.get((u, m["id"]))
                real = result_map.get(m["id"])
                pts = calculate_match_points(pred, real, m.get("double", False))
                total += pts
                list_pts[li] += pts
                if real is not None:
                    mp += 20 if m.get("double") else 10
                    up += pts
            list_pct[li] = min(100, int(up / mp * 100)) if mp else 0

        up_all = mp_all = 0
        for m in all_matches:
            real = result_map.get(m["id"])
            if real is None:
                continue
            mp_all += 20 if m.get("double") else 10
            pred = pred_map.get((u, m["id"]))
            up_all += calculate_match_points(pred, real, m.get("double", False))
        pct_all = min(100, int(up_all / mp_all * 100)) if mp_all else 0

        user_stats[u] = {
            "total": total,
            "list_pts": list_pts,
            "pct": pct_all,
            "list_pct": list_pct,
            "match_only": total - adj_map.get(u, 0),
        }
    return user_stats, users, pred_map, result_map, all_matches, match_lists

@st.cache_data(ttl=60)
def get_all_standings():
    user_stats, users, *_ = get_full_points_data()
    standings = [
        {"nimi": u, "pisteet": user_stats[u]["total"], "pct": user_stats[u]["pct"]}
        for u in users
    ]
    standings = sorted(standings, key=lambda x: (-x["pisteet"], x["nimi"].lower()))
    if standings:
        rank = 1
        for i, e in enumerate(standings):
            if i > 0 and e["pisteet"] < standings[i - 1]["pisteet"]:
                rank = i + 1
            e["rank"] = rank
    return standings

@st.cache_data(ttl=60)
def get_list_standings(list_index: int):
    user_stats, users, *_ = get_full_points_data()
    standings = [
        {
            "nimi": u,
            "pisteet": user_stats[u]["list_pts"][list_index] if list_index < len(user_stats[u]["list_pts"]) else 0,
            "pct": user_stats[u]["list_pct"][list_index] if list_index < len(user_stats[u]["list_pct"]) else 0,
        }
        for u in users
    ]
    standings = sorted(standings, key=lambda x: (-x["pisteet"], x["nimi"].lower()))
    if standings:
        rank = 1
        for i, e in enumerate(standings):
            if i > 0 and e["pisteet"] < standings[i - 1]["pisteet"]:
                rank = i + 1
            e["rank"] = rank
    return standings

@st.cache_data(ttl=60)
def get_contest_stats():
    user_stats, users, pred_map, result_map, all_matches, match_lists = get_full_points_data()
    match_by_id = {m["id"]: m for m in all_matches}

    preds_by_match = {}
    for (user, mid), pred in pred_map.items():
        preds_by_match.setdefault(mid, []).append((user, pred))

    perfect_count = 0
    for (user, mid), pred in pred_map.items():
        real = result_map.get(mid)
        m = match_by_id.get(mid)
        if not real or not m:
            continue
        pts = calculate_match_points(pred, real, m.get("double", False))
        max_pts = 20 if m.get("double") else 10
        if pts == max_pts:
            perfect_count += 1

    double_points = {}
    for m in all_matches:
        if not m.get("double"):
            continue
        real = result_map.get(m["id"])
        if not real:
            continue
        for user, pred in preds_by_match.get(m["id"], []):
            pts = calculate_match_points(pred, real, True)
            double_points[user] = double_points.get(user, 0) + pts

    best_double_user, best_double_pts = None, -1
    if double_points:
        best_double_user, best_double_pts = max(double_points.items(), key=lambda x: (x[1], -len(x[0]), x[0]))

    hardest = None
    for m in all_matches:
        real = result_map.get(m["id"])
        if not real:
            continue
        preds = preds_by_match.get(m["id"], [])
        if not preds:
            continue
        total_pts = sum(calculate_match_points(pred, real, m.get("double", False)) for _, pred in preds)
        avg = total_pts / len(preds)
        if hardest is None or avg < hardest[0]:
            hardest = (avg, m, len(preds))

    return {
        "perfect_count": perfect_count,
        "best_double_user": best_double_user,
        "best_double_pts": best_double_pts if best_double_pts >= 0 else 0,
        "hardest_match": hardest[1] if hardest else None,
        "hardest_avg": round(hardest[0], 1) if hardest else None,
        "hardest_n": hardest[2] if hardest else None,
    }

def clear_points_cache():
    get_full_points_data.clear()
    get_all_standings.clear()
    get_list_standings.clear()
    get_contest_stats.clear()

def calculate_user_points(username):
    user_stats, *_ = get_full_points_data()
    return user_stats.get(username, {}).get("total", 0)

def calculate_match_points_only(username):
    user_stats, *_ = get_full_points_data()
    return user_stats.get(username, {}).get("match_only", 0)

def calculate_list_points(username, matches):
    user_preds = load_user_predictions(username)
    _, _, _, result_map, *_ = get_full_points_data()
    total = done = 0
    for m in matches:
        pred = user_preds.get(m["id"])
        if pred:
            done += 1
        total += calculate_match_points(pred, result_map.get(m["id"]), m.get("double", False))
    return total, done, len(matches)

def get_user_rank(username):
    standings = get_all_standings()
    if not standings:
        return 1, 1
    for e in standings:
        if e["nimi"] == username:
            return e["rank"], len(standings)
    return len(standings), len(standings)

def get_next_open_match():
    now = datetime.now(HELSINKI)
    all_lists, _ = load_all_match_lists()
    candidates = [m for _, matches in all_lists for m in matches if now < m["start"]]
    return min(candidates, key=lambda x: x["start"]) if candidates else None

def get_open_unpredicted(username):
    now = datetime.now(HELSINKI)
    user_preds = load_user_predictions(username)
    result = []
    for list_name, matches in get_match_lists():
        open_missing = [m for m in matches if now < m["start"] and m["id"] not in user_preds]
        if open_missing:
            result.append((list_name, open_missing))
    return result

def get_last_results_update():
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(updated_at) as last FROM real_results WHERE result_type='match'"
        ).fetchone()
    return row["last"] if row and row["last"] else None

# ====================== SIVUPALKKI ======================
if "site_access" not in st.session_state:
    st.session_state.site_access = False
if "page" not in st.session_state:
    st.session_state.page = "Etusivu"

if not st.session_state.site_access:
    st.sidebar.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    page = "Etusivu"

elif not st.session_state.get("logged_in_user"):
    st.sidebar.markdown("<div style='height:130px;'></div>", unsafe_allow_html=True)

    with st.sidebar.expander("KIRJAUDU SISÄÄN", expanded=False):
        u = st.text_input("Käyttäjänimi", key="login_user")
        p = st.text_input("Salasana", type="password", key="login_pass")
        if st.button("Kirjaudu sisään", type="primary", use_container_width=True):
            with get_db() as conn:
                row = conn.execute("SELECT password_hash FROM users WHERE username=?", (u,)).fetchone()
            if row and check_password(p, row["password_hash"]):
                if not row["password_hash"].startswith("$2"):
                    with get_db() as conn:
                        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_password(p), u))
                st.session_state.logged_in_user = u
                st.rerun()
            else:
                st.error("Väärä käyttäjänimi tai salasana")

    with st.sidebar.expander("VAIHDA SALASANA", expanded=False):
        pu = st.text_input("Käyttäjänimi", key="pwchange_user")
        pc = st.text_input("Nykyinen salasana", type="password", key="pwchange_current")
        pn = st.text_input("Uusi salasana", type="password", key="pwchange_new")
        pn2 = st.text_input("Toista uusi salasana", type="password", key="pwchange_new2")
        if st.button("Tallenna uusi salasana", type="primary", use_container_width=True, key="pwchange_save"):
            if not all([pu, pc, pn]):
                st.error("Täytä kaikki kentät")
            elif pn != pn2:
                st.error("Uudet salasanat eivät täsmää")
            elif len(pn) < 6:
                st.error("Uuden salasanan tulee olla vähintään 6 merkkiä")
            else:
                with get_db() as conn:
                    row = conn.execute("SELECT password_hash FROM users WHERE username=?", (pu,)).fetchone()
                    if row and check_password(pc, row["password_hash"]):
                        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_password(pn), pu))
                        st.success("Salasana vaihdettu!")
                        st.toast("Salasana vaihdettu!")
                    else:
                        st.error("Väärä käyttäjänimi tai nykyinen salasana")

    with st.sidebar.expander("LUO UUSI TILI", expanded=False):
        nu = st.text_input("Käyttäjänimi", key="reg_user")
        np = st.text_input("Salasana", type="password", key="reg_pass")
        np2 = st.text_input("Toista salasana", type="password", key="reg_pass2")
        if st.button("Rekisteröidy", type="primary", use_container_width=True):
            if not nu or not np:
                st.error("Käyttäjänimi ja salasana pakollisia")
            elif np != np2:
                st.error("Salasanat eivät täsmää")
            elif len(np) < 6:
                st.error("Salasanan tulee olla vähintään 6 merkkiä")
            else:
                with get_db() as conn:
                    if conn.execute("SELECT username FROM users WHERE username=?", (nu,)).fetchone():
                        st.error("Käyttäjänimi on jo käytössä")
                    else:
                        conn.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", (nu, hash_password(np)))
                        st.success("✅ Tili luotu! Voit nyt kirjautua sisään.")
                        st.toast("Tili luotu!")

    page = "Etusivu"

else:
    st.sidebar.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    menu = ["Etusivu", "Kisainfo", "VEIKKAUSKISA", "Veikkaustilanne", "Omat veikkaukset", "Kaikkien veikkaukset", "Hall Of Fame"]

    if st.session_state.page == "Admin":
        page = "Admin"
        st.sidebar.info("Olet Admin-paneelissa")
        if st.sidebar.button("← Palaa valikkoon", use_container_width=True):
            st.session_state.page = "Etusivu"
            st.rerun()
    else:
        if st.session_state.page not in menu:
            st.session_state.page = "Etusivu"
        selected = st.sidebar.radio("", menu, index=menu.index(st.session_state.page), key="menu_radio")
        if selected != st.session_state.page:
            st.session_state.page = selected
            st.rerun()
        page = selected

    rank, total = get_user_rank(st.session_state.logged_in_user)
    uname = st.session_state.logged_in_user
    st.sidebar.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;background:rgba(17,24,39,0.95);border:1px solid #334155;border-radius:12px;padding:11px 14px;margin-bottom:10px;gap:10px;">
        <span style="color:#e2e8f0;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">👤 {html.escape(uname)}</span>
        <span style="color:#22c55e;font-weight:700;flex-shrink:0;">{rank}/{total}</span>
    </div>""", unsafe_allow_html=True)

    if st.sidebar.button("Kirjaudu ulos", use_container_width=True, key="logout_btn"):
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.session_state.page = "Etusivu"
        st.rerun()

    with st.sidebar.expander("Admin"):
        if not st.session_state.get("is_admin"):
            pw = st.text_input("Admin-salasana", type="password", key="admin_pw_sidebar")
            if st.button("Kirjaudu adminiksi", use_container_width=True):
                if pw == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Väärä salasana")
        else:
            st.success("Olet admin-tilassa")
            if st.button("Siirry Admin-paneeliin", type="primary", use_container_width=True):
                st.session_state.page = "Admin"
                st.rerun()

components.html("""<script>
(function(){function s(){try{['section[data-testid="stMain"]','[data-testid="stAppViewContainer"]','.main','.stApp',document.body].forEach(el=>{if(el=window.parent.document.querySelector(el)||el){el.scrollTop=0;el.scrollTo(0,0);}});window.parent.scrollTo(0,0);}catch(e){}}s();let c=0;const i=setInterval(()=>{s();if(++c>30)clearInterval(i);},50);})();
</script>""", height=0)

# ====================== ETUSIVU ======================
if page == "Etusivu":
    if not st.session_state.site_access:
        big_title("Haamuhanskan veikkauskisoja")
        st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.1, 1])
        with c2:
            st.markdown("<h3 style='text-align:center;color:#e2e8f0;'> 🔐 Salasanalla sisään!  </h3>", unsafe_allow_html=True)
            pw = st.text_input("Salasana", type="password", key="site_pw_main", label_visibility="collapsed", placeholder="")
            if st.button(" Avaa sivusto", type="primary", use_container_width=True):
                if pw == SITE_PASSWORD:
                    st.session_state.site_access = True
                    st.rerun()
                else:
                    st.error("Väärä kutsusalasana")

    elif not st.session_state.get("logged_in_user"):
        big_title("Haamuhanskan veikkauskisoja")
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    else:
        big_title("Syyskuun palloilupaketti", "2.55rem")
        uname = st.session_state.logged_in_user
        pts = calculate_user_points(uname)
        rank, total = get_user_rank(uname)
        next_m = get_next_open_match()
        now = datetime.now(HELSINKI)

        user_preds = load_user_predictions(uname)
        all_lists, _ = load_all_match_lists()
        done = total_m = open_m = 0
        for _, matches in all_lists:
            for m in matches:
                total_m += 1
                if m["id"] in user_preds:
                    done += 1
                if now < m["start"]:
                    open_m += 1

        next_txt = f"{next_m['home']} – {next_m['away']}" if next_m else "Ei avoimia"
        next_time = next_m["aika"] if next_m else "—"

        c1, c2, c3 = st.columns(3)
        for col, title, value, sub in [
            (c1, "Omat pisteet", pts, f"Sijoitus {rank}/{total}"),
            (c2, "Tallennetut veikkaukset", f"{done} / {total_m}", f"{open_m} veikkauskohdetta vielä avoinna"),
            (c3, "Seuraava kohde", next_txt, next_time)
        ]:
            with col:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #22c55e;border-radius:14px;padding:20px 16px;text-align:center;min-height:170px;display:flex;flex-direction:column;justify-content:center;">
                    <div style="font-size:1rem;color:#94a3b8;margin-bottom:8px;">{title}</div>
                    <div style="font-size:1.6rem;font-weight:700;color:#22c55e;line-height:1.2;">{value}</div>
                    <div style="font-size:0.95rem;color:#94a3b8;margin-top:10px;">{sub}</div>
                </div>""", unsafe_allow_html=True)

        # --- Kisan tilastolaatikot ---
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        stats = get_contest_stats()
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;border-radius:14px;padding:18px 14px;text-align:center;min-height:140px;display:flex;flex-direction:column;justify-content:center;">
                <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:6px;">🎯 Täysosumat</div>
                <div style="font-size:1.7rem;font-weight:700;color:#22c55e;">{stats['perfect_count']}</div>
                <div style="font-size:0.85rem;color:#64748b;margin-top:6px;">kpl koko kisassa</div>
            </div>""", unsafe_allow_html=True)
        with s2:
            if stats["best_double_user"]:
                d_val = html.escape(stats["best_double_user"])
                d_sub = f"{stats['best_double_pts']} p tuplakohteista"
            else:
                d_val, d_sub = "—", "Ei vielä tuplatuloksia"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;border-radius:14px;padding:18px 14px;text-align:center;min-height:140px;display:flex;flex-direction:column;justify-content:center;">
                <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:6px;">🔥 Paras tuplaaja</div>
                <div style="font-size:1.35rem;font-weight:700;color:#22c55e;">{d_val}</div>
                <div style="font-size:0.85rem;color:#64748b;margin-top:6px;">{d_sub}</div>
            </div>""", unsafe_allow_html=True)
        with s3:
            if stats["hardest_match"]:
                hm = stats["hardest_match"]
                h_val = f"{hm['home']} – {hm['away']}"
                h_sub = f"{stats['hardest_avg']} p / veikkaaja"
            else:
                h_val, h_sub = "—", "Ei vielä tuloksia"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;border-radius:14px;padding:18px 14px;text-align:center;min-height:140px;display:flex;flex-direction:column;justify-content:center;">
                <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:6px;">💀 Vaikein kohde</div>
                <div style="font-size:1.15rem;font-weight:700;color:#f87171;line-height:1.25;">{html.escape(h_val)}</div>
                <div style="font-size:0.85rem;color:#64748b;margin-top:6px;">{h_sub}</div>
            </div>""", unsafe_allow_html=True)

        open_missing = get_open_unpredicted(uname)
        st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

        _, mid, _ = st.columns([1, 2.2, 1])
        with mid:
            st.markdown("#### Tallennusta vailla olevat veikkauskohteet...")
            if not open_missing:
                st.success("Kaikki avoimet kohteet on veikattu! 🎉")
            else:
                total_missing = sum(len(ms) for _, ms in open_missing)
                st.caption(f"{total_missing} kpl")
                for list_name, matches in open_missing:
                    with st.expander(f"{list_name} ({len(matches)} kohdetta)", expanded=len(open_missing) <= 2):
                        for m in matches:
                            dbl = " 🔥" if m.get("double") else ""
                            st.markdown(
                                f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e293b;">'
                                f'<span style="color:#e2e8f0;">{m["home"]} – {m["away"]}{dbl}</span>'
                                f'<span style="color:#94a3b8;font-size:0.85rem;">{m["aika"]}</span></div>',
                                unsafe_allow_html=True
                            )

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 2.2, 1])
        with mid:
            st.markdown("#### 💬 Viimeisimmät kommentit...")
            top_level = get_comments_latest(3)
            if not top_level:
                st.info("Ei vielä kommentteja.")
            else:
                for c in top_level:
                    t = c["created_at"][8:10] + "." + c["created_at"][5:7] + ". " + c["created_at"][11:16]
                    st.markdown(f"""
                    <div style="background:#1e293b;padding:12px 14px;border-radius:10px;margin-bottom:8px;border-left:3px solid #22c55e;">
                        <strong style="color:#f1f5f9;">{html.escape(c['username'])}</strong>
                        <span style="color:#64748b;font-size:0.85rem;margin-left:8px;">{t}</span><br>
                        <div style="margin-top:4px;color:#cbd5e1;">{html.escape(c['text'][:180])}{'…' if len(c['text'])>180 else ''}</div>
                    </div>""", unsafe_allow_html=True)

# ====================== HALL OF FAME ======================
if page == "Hall Of Fame":
    st.subheader("Hall Of Fame - veikkauskisojen kärkikolmikot")
    st.divider()
    PAST = [{
        "name": "MM26 -testikisa", "date": "Kesä 2026", "participants": 7, "max_points": 1048,
        "standings": [{"nimi":"Markus","pisteet":386},{"nimi":"Tommi","pisteet":354},{"nimi":"Tekoäly","pisteet":346}]
    }]
    tabs = st.tabs(["Syyskuun palloilupaketti"] + [c["name"] for c in PAST])

    with tabs[0]:
        with st.spinner("Ladataan sijoituksia..."):
            all_standings = get_all_standings()
            standings = [e for e in all_standings if e.get("rank", 99) <= 3]
        if not standings:
            st.info("Ei vielä pelaajia.")
        else:
            with get_db() as conn:
                user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
            st.markdown(
                f'<div style="color:#94a3b8;margin-bottom:14px;font-size:0.85rem;">Osallistujia: <b style="color:#e2e8f0;">{user_count}</b> · Ajankohta: <b style="color:#e2e8f0;">Syyskuu 2026</b></div>',
                unsafe_allow_html=True
            )
            medal_map = {1: "🥇", 2: "🥈", 3: "🥉"}
            color_map = {1: "#fbbf24", 2: "#94a3b8", 3: "#d97706"}
            bg_map = {1: "rgba(251,191,36,0.10)", 2: "rgba(148,163,184,0.08)", 3: "rgba(217,119,6,0.08)"}
            for e in standings:
                r = e["rank"]
                render_hof_card(medal_map.get(r, ""), color_map.get(r, "#94a3b8"), bg_map.get(r, "rgba(148,163,184,0.08)"),
                                e["nimi"], e["pisteet"], e["pct"])

    for idx, contest in enumerate(PAST):
        with tabs[idx + 1]:
            st.markdown(
                f'<div style="color:#94a3b8;margin-bottom:14px;font-size:0.85rem;">Osallistujia: <b style="color:#e2e8f0;">{contest["participants"]}</b> · Ajankohta: <b style="color:#e2e8f0;">{contest["date"]}</b></div>',
                unsafe_allow_html=True
            )
            for i, e in enumerate(contest["standings"]):
                pct = min(100, int(e["pisteet"] / contest["max_points"] * 100)) if contest.get("max_points") else 0
                render_hof_card(["🥇", "🥈", "🥉"][i], ["#fbbf24", "#94a3b8", "#d97706"][i],
                                ["rgba(251,191,36,0.10)", "rgba(148,163,184,0.08)", "rgba(217,119,6,0.08)"][i],
                                e["nimi"], e["pisteet"], pct)

# ====================== VEIKKAUSKISA ======================
if page == "VEIKKAUSKISA":
    st.subheader("Syyskuun palloilupaketti - veikkauslistat")
    st.divider()
    all_lists, lists_by_key = load_all_match_lists()
    if not all_lists:
        st.warning("Ei otteluita. Lisää otteluita admin-paneelista.")
    else:
        tab_labels = [name for name, _ in all_lists]
        tabs = st.tabs(tab_labels)

        def render_normal_match(m, prefix):
            now = datetime.now(HELSINKI)
            if now >= m["start"]:
                return
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = saved and "home_goals" in saved
            dbl = '<span style="background:linear-gradient(135deg,#f97316,#ef4444);color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔥 TUPLAPISTEET</span>' if m["double"] else ""
            st.markdown(
                f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:#f1f5f9;">{m["home"]} – {m["away"]}</span>{dbl}</div>'
                f'<div style="font-size:0.88rem;color:#94a3b8;margin-bottom:2px;">{m["aika"]}</div>',
                unsafe_allow_html=True
            )
            render_countdown(m["id"], m["start"])
            with st.container(border=True):
                left, right = st.columns([1.5, 1])
                with left:
                    c1, c2 = st.columns(2)
                    with c1:
                        h = st.selectbox(f"**{m['home']}**", range(13), index=saved["home_goals"] if has else 0, key=f"{prefix}_{m['id']}_h")
                    with c2:
                        a = st.selectbox(f"**{m['away']}**", range(13), index=saved["away_goals"] if has else 0, key=f"{prefix}_{m['id']}_a")
                    if st.button("Päivitä veikkaus" if has else "Tallenna veikkaus", type="secondary" if has else "primary", key=f"{prefix}_save_{m['id']}", use_container_width=True):
                        save_prediction(st.session_state.logged_in_user, m["id"], {"home_goals": h, "away_goals": a})
                        clear_points_cache()
                        st.toast("Veikkaus tallennettu!")
                        st.success("Veikkaus tallennettu!")
                        st.rerun()
                with right:
                    if has:
                        st.markdown(
                            f'<div style="background:linear-gradient(145deg,#1e293b,#0f172a);border:1px solid #22c55e;border-radius:12px;padding:14px 12px;text-align:center;">'
                            f'<div style="font-size:0.72rem;color:#94a3b8;">TALLENNETTU</div>'
                            f'<div style="font-size:1.55rem;font-weight:700;color:#f1f5f9;">{saved["home_goals"]} – {saved["away_goals"]}</div></div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="background:#0f172a;border:1px dashed #334155;border-radius:12px;padding:18px 12px;text-align:center;color:#64748b;font-size:0.85rem;">Ei vielä<br>tallennettua veikkausta</div>',
                            unsafe_allow_html=True
                        )
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        def render_nhl_match(m):
            now = datetime.now(HELSINKI)
            if now >= m["start"]:
                return
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = saved and "mark" in saved
            dbl = '<span style="background:linear-gradient(135deg,#f97316,#ef4444);color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔥 TUPLAPISTEET</span>' if m["double"] else ""
            st.markdown(
                f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:#f1f5f9;">{m["home"]} – {m["away"]}</span>{dbl}</div>'
                f'<div style="font-size:0.88rem;color:#94a3b8;margin-bottom:2px;">{m["aika"]}</div>',
                unsafe_allow_html=True
            )
            render_countdown(m["id"], m["start"])
            with st.container(border=True):
                left, right = st.columns([1.4, 1])
                with left:
                    st.markdown("##### 1X2")
                    mark = st.radio(
                        "1X2", ["1", "X", "2"],
                        index=["1", "X", "2"].index(saved.get("mark", "X") if saved else "X"),
                        horizontal=True, key=f"nhl_mark_{m['id']}", label_visibility="collapsed"
                    )
                    st.markdown("##### Moniveto")
                    split = st.radio(
                        "Jakotapa", ["4-1", "2-2", "1-4"],
                        index=["4-1", "2-2", "1-4"].index(saved.get("split", "2-2") if saved else "2-2"),
                        horizontal=True, key=f"nhl_split_{m['id']}", label_visibility="collapsed"
                    )
                    hc, ac = int(split[0]), int(split[-1])
                    home_key = f"nhl_home_{m['id']}"
                    away_key = f"nhl_away_{m['id']}"

                    if home_key not in st.session_state:
                        st.session_state[home_key] = (saved.get("home_opts", []) if saved else [])[:hc]
                    if away_key not in st.session_state:
                        st.session_state[away_key] = (saved.get("away_opts", []) if saved else [])[:ac]

                    if len(st.session_state.get(home_key, [])) > hc:
                        st.session_state[home_key] = st.session_state[home_key][:hc]
                    if len(st.session_state.get(away_key, [])) > ac:
                        st.session_state[away_key] = st.session_state[away_key][:ac]

                    c1, c2 = st.columns(2)
                    with c1:
                        try:
                            home_opts = st.multiselect(
                                f"**{m['home']}** ({hc} kpl)", list(range(13)),
                                key=home_key, max_selections=hc
                            )
                        except TypeError:
                            home_opts = st.multiselect(
                                f"**{m['home']}** ({hc} kpl)", list(range(13)), key=home_key
                            )
                    with c2:
                        try:
                            away_opts = st.multiselect(
                                f"**{m['away']}** ({ac} kpl)", list(range(13)),
                                key=away_key, max_selections=ac
                            )
                        except TypeError:
                            away_opts = st.multiselect(
                                f"**{m['away']}** ({ac} kpl)", list(range(13)), key=away_key
                            )

                    if st.button("Päivitä veikkaus" if has else "Tallenna veikkaus",
                                 type="secondary" if has else "primary",
                                 key=f"nhl_save_{m['id']}", use_container_width=True):
                        if len(home_opts) != hc or len(away_opts) != ac:
                            st.error(f"Valitse tasan **{hc}** kotimaalia ja **{ac}** vierasmaalia")
                        else:
                            save_prediction(
                                st.session_state.logged_in_user, m["id"],
                                {"mark": mark, "split": split,
                                 "home_opts": sorted(set(home_opts)),
                                 "away_opts": sorted(set(away_opts))}
                            )
                            clear_points_cache()
                            st.toast("Veikkaus tallennettu!")
                            st.success("Veikkaus tallennettu!")
                            st.rerun()
                with right:
                    if has:
                        combos = ", ".join(f"{h}–{a}" for h in saved.get("home_opts", []) for a in saved.get("away_opts", [])) or "–"
                        st.markdown(
                            f'<div style="background:linear-gradient(145deg,#1e293b,#0f172a);border:1px solid #22c55e;border-radius:12px;padding:14px 12px;text-align:center;">'
                            f'<div style="font-size:0.72rem;color:#94a3b8;margin-bottom:8px;">TALLENNETTU</div>'
                            f'<div style="margin-bottom:8px;"><div style="font-size:0.72rem;color:#94a3b8;">1X2</div>'
                            f'<div style="font-size:1.35rem;font-weight:700;color:#f1f5f9;">{saved.get("mark", "-")}</div></div>'
                            f'<div><div style="font-size:0.72rem;color:#94a3b8;">Moniveto ({saved.get("split", "-")})</div>'
                            f'<div style="font-size:0.9rem;color:#22c55e;margin-top:2px;">{combos}</div></div></div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div style="background:#0f172a;border:1px dashed #334155;border-radius:12px;padding:18px 12px;text-align:center;color:#64748b;font-size:0.85rem;">Ei vielä<br>tallennettua veikkausta</div>',
                            unsafe_allow_html=True
                        )
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        for ti, (name, matches) in enumerate(all_lists):
            with tabs[ti]:
                pred_type = matches[0]["pred_type"] if matches else "normal"
                if pred_type == "nhl":
                    for m in matches:
                        render_nhl_match(m)
                else:
                    for m in matches:
                        render_normal_match(m, f"l{ti}")

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    col_rank, col_chat = st.columns([1.45, 1.75], gap="large")

    with col_rank:
        st.subheader("🏆 Veikkaustilanne")
        last_update = get_last_results_update()
        if last_update:
            try:
                dt = datetime.fromisoformat(last_update)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=HELSINKI)
                formatted = dt.astimezone(HELSINKI).strftime("%d.%m.%Y %H:%M")
                st.caption(f"Tulokset viimeksi päivitetty: {formatted}")
            except Exception:
                pass

        all_lists, _ = load_all_match_lists()
        with get_db() as conn:
            users = [r["username"] for r in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]

        if not users:
            st.info("Ei vielä yhtään rekisteröitynyttä pelaajaa.")
        else:
            tabs = st.tabs(["Veikkauskisan kokonaistilanne"] + [name for name, _ in all_lists])
            with tabs[0]:
                with st.spinner("Ladataan sijoituksia..."):
                    standings = get_all_standings()
                for e in standings:
                    render_ranking_row(e["rank"], e["nimi"], e["pisteet"], e["pct"],
                                       e["nimi"] == st.session_state.logged_in_user)
            for ti, (name, matches) in enumerate(all_lists):
                with tabs[ti + 1]:
                    st.markdown(
                        f'<div style="background:rgba(30,41,59,0.6);border:1px solid #334155;'
                        f'border-radius:10px;padding:10px 14px;margin-bottom:14px;'
                        f'font-size:0.9rem;color:#94a3b8;">'
                        f'<b style="color:#e2e8f0;">{name}</b><br>'
                        f'Bonuspisteet jaetaan, kun lista on pelattu!</div>',
                        unsafe_allow_html=True,
                    )
                    with st.spinner("Ladataan listan sijoituksia..."):
                        standings = get_list_standings(ti)
                    for e in standings:
                        render_ranking_row(e["rank"], e["nimi"], e["pisteet"], e["pct"],
                                           e["nimi"] == st.session_state.logged_in_user)

    with col_chat:
        st.subheader("📣 Sana on vapaa!")
        per_page = 5
        total_roots = count_root_comments()
        total_pages = max(1, (total_roots + per_page - 1) // per_page)
        if "comment_page" not in st.session_state:
            st.session_state.comment_page = 1
        st.session_state.comment_page = max(1, min(st.session_state.comment_page, total_pages))
        page_c = st.session_state.comment_page
        displayed = get_root_comments_page(page_c, per_page)
        me = st.session_state.get("logged_in_user")

        def render_comment_row(c, is_reply=False):
            is_own = c["username"] == me
            t = c["created_at"][8:10] + "." + c["created_at"][5:7] + ". " + c["created_at"][11:16]
            if c.get("edited_at"):
                t += " (muokattu)"
            pad = "margin-left:38px;" if is_reply else ""
            border_col = "#22c55e" if is_own else ("#475569" if is_reply else "#334155")
            bg = "rgba(34,197,94,0.08)" if is_own else ("#0f172a" if is_reply else "#1e293b")
            col_m, col_b, col_c = st.columns([15, 2, 2])
            with col_m:
                st.markdown(
                    f'<div style="background:{bg};padding:10px 16px;border-radius:12px;'
                    f'margin-bottom:10px;border-left:4px solid {border_col};{pad}">'
                    f'<strong style="color:#f1f5f9;">{html.escape(c["username"])}</strong>'
                    f'<span style="color:#64748b;font-size:0.85rem;margin-left:12px;">{t}</span><br>'
                    f'<div style="margin-top:10px;color:#cbd5e1;line-height:1.45;">'
                    f'{html.escape(c["text"])}</div></div>',
                    unsafe_allow_html=True,
                )
            with col_b:
                if me and not is_reply:
                    if st.button("💬", key=f"reply_{c['id']}", help="Vastaa", use_container_width=True):
                        st.session_state.replying_to = c["id"]
                        st.session_state.editing_comment = None
                        st.rerun()
            with col_c:
                if is_own:
                    if st.button("✏️", key=f"edit_{c['id']}", help="Muokkaa", use_container_width=True):
                        st.session_state.editing_comment = c["id"]
                        st.session_state.replying_to = None
                        st.rerun()

        if displayed:
            for c in displayed:
                render_comment_row(c, is_reply=False)
                for reply in c.get("replies", []):
                    render_comment_row(reply, is_reply=True)
                if me and st.session_state.get("replying_to") == c["id"]:
                    with st.form(f"reply_form_{c['id']}", clear_on_submit=True):
                        st.caption(f"Vastaus käyttäjälle **{c['username']}**")
                        rt = st.text_area("Vastaus", height=80, max_chars=400, key=f"reply_text_{c['id']}",
                                          label_visibility="collapsed", placeholder="Kirjoita vastaus...")
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.form_submit_button("Lähetä", type="primary", use_container_width=True) and rt.strip():
                                add_comment(me, rt.strip(), parent_id=c["id"])
                                st.session_state.replying_to = None
                                st.toast("Vastaus lähetetty!")
                                st.rerun()
                        with b2:
                            if st.form_submit_button("Peruuta", use_container_width=True):
                                st.session_state.replying_to = None
                                st.rerun()
        else:
            st.info("Ei vielä kommentteja. Ole ensimmäinen!")

        if total_pages > 1:
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1.43])
            with c1:
                if st.button("← Edellinen", disabled=page_c <= 1, use_container_width=True, key="cmt_prev"):
                    st.session_state.comment_page -= 1
                    st.rerun()
            with c2:
                st.markdown(f"<div style='text-align:center;padding-top:8px;color:#94a3b8;'>Sivu {page_c} / {total_pages}</div>", unsafe_allow_html=True)
            with c3:
                if st.button("Seuraava →", disabled=page_c >= total_pages, use_container_width=True, key="cmt_next"):
                    st.session_state.comment_page += 1
                    st.rerun()

        if me and st.session_state.get("editing_comment") is not None:
            cid = st.session_state.editing_comment
            with get_db() as conn:
                cur = conn.execute("SELECT * FROM comments WHERE id=?", (cid,)).fetchone()
            if cur and cur["username"] == me:
                st.markdown("---")
                st.write("**Muokkaa kommenttiasi:**")
                nt = st.text_area("Kommentti", value=cur["text"], height=100, key="edit_text")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Tallenna", type="primary", key="save_edit") and nt.strip():
                        update_comment(cid, nt.strip())
                        st.session_state.editing_comment = None
                        st.toast("Kommentti päivitetty!")
                        st.rerun()
                with c2:
                    if st.button("Peruuta", key="cancel_edit"):
                        st.session_state.editing_comment = None
                        st.rerun()
                with c3:
                    if st.session_state.get(f"confirm_delete_{cid}"):
                        if st.button("Vahvista poisto", type="primary", key=f"confirm_del_{cid}"):
                            delete_comment(cid)
                            st.session_state.editing_comment = None
                            st.session_state[f"confirm_delete_{cid}"] = False
                            st.toast("Kommentti poistettu")
                            st.rerun()
                    else:
                        if st.button("🗑️ Poista", key=f"delete_{cid}"):
                            st.session_state[f"confirm_delete_{cid}"] = True
                            st.rerun()

        if me:
            with st.form("comment_form", clear_on_submit=True):
                nc = st.text_area("Kirjoita kommentti...", height=100, placeholder="Anna palaa.... 🔥",
                                  max_chars=600, label_visibility="collapsed")
                if st.form_submit_button("💥 Julkaise", use_container_width=True) and nc.strip():
                    add_comment(me, nc.strip())
                    st.session_state.comment_page = 1
                    st.toast("Kommentti julkaistu!")
                    st.rerun()
        else:
            st.warning("Kirjaudu sisään kirjoittaaksesi kommentteja.")

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    st.subheader("Omat veikkaukset")
    st.divider()
    all_lists, _ = load_all_match_lists()
    if not all_lists:
        st.info("Ei otteluita.")
    else:
        tabs = st.tabs([name for name, _ in all_lists])

        def render_own(matches):
            uname = st.session_state.logged_in_user
            pts, done, total = calculate_list_points(uname, matches)
            summary_card("Yhteensä", f"{pts} pistettä", f"{done}/{total} veikkausta tallennettu")
            user_preds = load_user_predictions(uname)
            _, _, _, result_map, *_ = get_full_points_data()
            found = False
            for m in matches:
                saved = user_preds.get(m["id"])
                if not saved:
                    continue
                found = True
                real = result_map.get(m["id"])
                points = calculate_match_points(saved, real, m["double"])
                dbl = " 🔥 " if m["double"] else ""
                st.markdown(f"### {m['home']} – {m['away']}{dbl}")
                st.markdown(f"<p style='font-size:0.9rem;color:#94a3b8;margin-top:-6px;margin-bottom:10px;'>{m['aika']}</p>", unsafe_allow_html=True)
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.4, 1.4, 1])
                    with c1:
                        if "mark" in saved:
                            combos = ", ".join(f"{h}–{a}" for h in saved.get("home_opts", []) for a in saved.get("away_opts", [])) or "–"
                            st.markdown(
                                f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:6px;">Oma veikkaus</div>'
                                f'<div style="font-size:1rem;color:#e2e8f0;"><b>1X2:</b> {saved.get("mark")}<br><b>Moniveto:</b> {combos}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:6px;">Oma veikkaus</div>'
                                f'<div style="font-size:1.45rem;font-weight:700;color:#f1f5f9;">{saved.get("home_goals")} – {saved.get("away_goals")}</div>',
                                unsafe_allow_html=True
                            )
                    with c2:
                        if real:
                            st.markdown(
                                f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:6px;">Oikea tulos</div>'
                                f'<div style="font-size:1.45rem;font-weight:700;color:#22c55e;">{real["home_goals"]} – {real["away_goals"]}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                '<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:6px;">Oikea tulos</div>'
                                '<div style="font-size:1.1rem;color:#64748b;">Tulosta odotellessa...</div>',
                                unsafe_allow_html=True
                            )
                    with c3:
                        col = "#22c55e" if points >= 8 else "#fbbf24" if points >= 4 else "#94a3b8" if points > 0 else "#64748b"
                        st.markdown(
                            f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:6px;">Pisteet</div>'
                            f'<div style="font-size:1.55rem;font-weight:700;color:{col};">{points}</div>',
                            unsafe_allow_html=True
                        )
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            if not found:
                st.info("Et ole vielä tallentanut yhtään veikkausta tälle listalle.")

        for i, (_, matches) in enumerate(all_lists):
            with tabs[i]:
                render_own(matches)

# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("Kaikkien veikkaukset")
    st.divider()
    all_lists, _ = load_all_match_lists()
    if not all_lists:
        st.info("Ei otteluita.")
    else:
        tabs = st.tabs([name for name, _ in all_lists])

        def render_all(matches, list_name):
            now = datetime.now(HELSINKI)
            _, _, _, result_map, *_ = get_full_points_data()
            closed = sum(1 for m in matches if now >= m["start"] or result_map.get(m["id"]))
            summary_card(list_name, f"{closed}/{len(matches)}", "Näkymässä vain sulkeutuneet veikkauskohteet")
            shown = False
            me = st.session_state.logged_in_user
            for m in matches:
                real = result_map.get(m["id"])
                if not (now >= m["start"] or real):
                    continue
                shown = True
                preds = load_all_predictions_for_match(m["id"])
                dbl = " 🔥 " if m["double"] else ""
                st.markdown(f"### {m['home']} – {m['away']}{dbl}")
                st.markdown(f"<p style='font-size:0.9rem;color:#94a3b8;margin-top:-6px;margin-bottom:10px;'>{m['aika']}</p>", unsafe_allow_html=True)
                if real:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #22c55e;border-radius:10px;padding:7px 16px;margin-bottom:12px;display:inline-block;font-size:1.2rem;font-weight:700;color:#22c55e;">'
                        f'{real["home_goals"]} – {real["away_goals"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div style="background:#0f172a;border:1px dashed #334155;border-radius:10px;padding:7px 16px;margin-bottom:12px;display:inline-block;font-size:1.15rem;color:#64748b;">–</div>',
                        unsafe_allow_html=True
                    )
                if not preds:
                    st.info("Ei vielä yhtään veikkausta tälle ottelulle.")
                else:
                    rows = []
                    for u, p in preds.items():
                        score = format_pred_text(p)
                        pts = calculate_match_points(p, real, m["double"]) if real else -1
                        rows.append({"username": u, "score": score, "points": pts})
                    rows.sort(key=lambda x: (-x["points"], x["username"].lower()) if real else x["username"].lower())
                    with st.expander(f"Veikkaukset ja pisteet ({len(rows)})", expanded=False):
                        for r in rows:
                            is_me = r["username"] == me
                            pc = "#22c55e" if r["points"] >= 8 else "#fbbf24" if r["points"] >= 4 else "#94a3b8" if r["points"] > 0 else "#64748b"
                            pts_html = f"<span style='color:{pc};font-weight:700;'>{r['points']} p</span>" if real else "<span style='color:#64748b;'>—</span>"
                            st.markdown(f"""
                            <div style="display:flex;align-items:center;background:#0f172a;padding:9px 12px;border-radius:8px;margin-bottom:5px;border:1px solid #1e293b;gap:14px;">
                                <span style="color:{"#22c55e" if is_me else "#e2e8f0"};font-weight:{"700" if is_me else "400"};min-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{html.escape(r['username'])}</span>
                                <span style="color:#cbd5e1;flex:1;">{html.escape(r['score'])}</span>
                                <div style="min-width:48px;text-align:right;">{pts_html}</div>
                            </div>""", unsafe_allow_html=True)
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            if not shown:
                st.info(f"Ei vielä yhtään suljettua ottelua listalla {list_name}.")

        for i, (name, matches) in enumerate(all_lists):
            with tabs[i]:
                render_all(matches, f"Lista {i+1}")

# ====================== KISAINFON ======================
if page == "Kisainfo":
    page_header(
        "Tervetuloa veikkaamaan!",
        "Syyskuun palloilupaketti- veikkauskisa sisältää viisi erillistä veikkauslistaa. Veikattavana on jääkiekkoa Suomesta ja rapakon takaa sekä jalkapalloa ympäri Eurooppaa niin seura- kuin maajoukkuetasolta. Yksittäisen listan kärkikolmikolle on luvassa bonuspisteitä, mutta koko kisan kuittaa itselleen tietenkin pärjäämällä parhaiten kaikissa listoissa yhteensä. Onnea veikkauksiin!"
    )
    st.subheader("Pisteytysjärjestelmä - Listat 1-4")
    st.caption("SM-Liiga • Valioliiga • Eurofutis • Nations League")
    pcols = st.columns(6)
    for col, (pts, desc, color) in zip(pcols, [
        ("10 p", "Täysin oikea veikkaus", "#22c55e"),
        ("7 p", "Oikea voittaja\n(Toisen joukkueen maalimäärä oikein ja toisen korkeintaan yhdellä väärin)", "#22c55e"),
        ("6 p", "Oikea voittaja\n(Toisen joukkueen maalimäärä oikein ja toisen yli yhdellä väärin)", "#22c55e"),
        ("5 p", "Oikea tasapeli\n(Maalimäärät väärin)", "#22c55e"),
        ("4 p", "Oikea voittaja\n(Molempien joukkueiden maalimäärä väärin)", "#22c55e"),
        ("0 p", "Väärä 1X2", "#64748b")
    ]):
        with col:
            st.markdown(
                f'<div style="background:#0f172a;border:1px solid {color};border-radius:12px;padding:14px 10px;text-align:center;min-height:110px;">'
                f'<div style="font-size:1.35rem;font-weight:700;color:{color};">{pts}</div>'
                f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:6px;white-space:pre-line;">{desc}</div></div>',
                unsafe_allow_html=True
            )
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.subheader("Lista 5")
    st.caption("NHL 1X2 + Moniveto")
    n1, n2, _, _, _, _ = st.columns(6)
    with n1:
        st.markdown(
            '<div style="background:#0f172a;border:1px solid #22c55e;border-radius:12px;padding:14px 12px;text-align:center;">'
            '<div style="font-size:1.35rem;font-weight:700;color:#22c55e;">7 p</div>'
            '<div style="font-size:0.8rem;color:#94a3b8;margin-top:6px;">Täysin oikea veikkaus</div></div>',
            unsafe_allow_html=True
        )
    with n2:
        st.markdown(
            '<div style="background:#0f172a;border:1px solid #22c55e;border-radius:12px;padding:14px 12px;text-align:center;">'
            '<div style="font-size:1.35rem;font-weight:700;color:#22c55e;">3 p</div>'
            '<div style="font-size:0.8rem;color:#94a3b8;margin-top:6px;">Oikea 1X2</div></div>',
            unsafe_allow_html=True
        )
    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    st.subheader("Listakohtaiset bonuspisteet")
    b1, b2, b3, _, _ = st.columns(5)
    with b1:
        st.markdown("### 🥇 +5 p")
    with b2:
        st.markdown("### 🥈 +3 p")
    with b3:
        st.markdown("### 🥉 +1 p")
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.subheader("Muuta huomioitavaa")
    with st.container(border=True):
        st.markdown("""
- Veikkauskohteen veikkaaminen ja päivittäminen on mahdollista aina ottelun alkamiseen asti. Tämän jälkeen kohde sulkeutuu ja poistuu veikkauslistalta. Kun kohde on suljettu, voit vertailla kanssakilpailijoiden tekemiä veikkauksia "Kaikkien veikkaukset"-sivulta.   
- Huomioi monivetoa tehdessäsi, että valitset ensin oman pelistrategiasi. Täppää siis haluatko asettaa kotijoukkueelle neljä maalia ja vierasjoukkueelle yhden (4-1), molemmille kaksi maalia (2-2) vai yhden maalin kotijoukkueelle ja neljä maalia vierasjoukkueelle (1-4).   
- Jokaisessa listassa on yksi ennalta päätetty ja kaikille sama veikkauskohde, josta jaetaan tuplapisteet. 
- Tulokset kirjataan manuaalisesti adminin toimesta, saattaa siis välillä olla hieman viivettä. NHL-ottelut kirjataan järjestelmään vasta aamulla adminin herätessä.   
        """)

# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")
    if not st.session_state.get("is_admin"):
        pw = st.text_input("Syötä admin-salasana", type="password", key="admin_pw")
        if st.button("Kirjaudu adminiksi"):
            if pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Väärä salasana")
        st.stop()

    st.success("✅ Olet admin-tilassa")
    admin_tab = st.radio(
        "Valitse toiminto",
        ["Käyttäjien hallinta", "Tulosten syöttö", "Pistekorjaukset", "Listabonukset",
         "Otteluiden hallinta", "Varmuuskopiointi & palautus", "Keskustelu"],
        horizontal=True
    )

    if admin_tab == "Käyttäjien hallinta":
        st.write("### 👥 Käyttäjien hallinta")
        user_stats, *_ = get_full_points_data()
        with get_db() as conn:
            users = conn.execute("SELECT username, created_at FROM users ORDER BY username").fetchall()
        if not users:
            st.info("Ei käyttäjiä.")
        else:
            for u in users:
                uname = u["username"]
                match_pts = user_stats.get(uname, {}).get("match_only", 0)
                bonus = get_adjustment_total(uname)
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.write(f"**{uname}**")
                    st.caption(f"Luotu: {u['created_at'][:10] if u['created_at'] else '-'} · Ottelupisteet: {match_pts} · Korjaukset: {bonus:+d} · Yhteensä: {match_pts+bonus}")
                with c2:
                    with st.popover("Nollaa salasana"):
                        np = st.text_input("Uusi salasana", type="password", key=f"new_pw_{uname}")
                        np2 = st.text_input("Toista", type="password", key=f"new_pw2_{uname}")
                        if st.button("Tallenna", key=f"save_pw_{uname}"):
                            if not np:
                                st.error("Salasana ei voi olla tyhjä")
                            elif np != np2:
                                st.error("Salasanat eivät täsmää")
                            elif len(np) < 6:
                                st.error("Vähintään 6 merkkiä")
                            else:
                                with get_db() as conn:
                                    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (hash_password(np), uname))
                                st.toast(f"Salasana päivitetty: {uname}")
                                st.success(f"Salasana päivitetty: {uname}")
                                st.rerun()
                with c3:
                    key = f"confirm_del_user_{uname}"
                    if not st.session_state.get(key):
                        if st.button("Poista", key=f"del_{uname}"):
                            st.session_state[key] = True
                            st.rerun()
                    else:
                        st.warning(f"Poistetaanko **{uname}**?")
                        y, n = st.columns(2)
                        with y:
                            if st.button("Kyllä", key=f"del_yes_{uname}", type="primary"):
                                with get_db() as conn:
                                    conn.execute("DELETE FROM users WHERE username=?", (uname,))
                                    conn.execute("DELETE FROM predictions WHERE username=?", (uname,))
                                    conn.execute("DELETE FROM point_adjustments WHERE username=?", (uname,))
                                clear_points_cache()
                                st.session_state[key] = False
                                st.toast(f"Käyttäjä {uname} poistettu")
                                st.rerun()
                        with n:
                            if st.button("Peruuta", key=f"del_no_{uname}"):
                                st.session_state[key] = False
                                st.rerun()
                st.markdown("---")

    elif admin_tab == "Tulosten syöttö":
        st.write("### 📊 Tulosten syöttö")
        now = datetime.now(HELSINKI)
        all_lists, _ = load_all_match_lists()
        total = missing = started_missing = 0
        urgent = []
        for lname, matches in all_lists:
            for m in matches:
                total += 1
                real = load_real_result("match", m["id"])
                if real is None:
                    missing += 1
                    if now >= m["start"]:
                        started_missing += 1
                        urgent.append((lname, m))

        st.info(f"**Otteluita:** {total} · **Syöttämättä:** {missing} · **Alkaneet ilman tulosta:** {started_missing}")

        def parse_score(t):
            if not t:
                return None
            t = t.strip().replace("–", "-").replace(":", "-").replace(" ", "-")
            parts = t.split("-")
            if len(parts) != 2:
                return None
            try:
                h, a = int(parts[0]), int(parts[1])
                return (h, a) if h >= 0 and a >= 0 else None
            except Exception:
                return None

        if urgent:
            st.markdown("#### 🚨 Kiireelliset – alkaneet ilman tulosta")
            with st.container(border=True):
                for lname, m in urgent:
                    pred_c = count_predictions_for_match(m["id"])
                    dbl = " 🔥" if m["double"] else ""
                    st.markdown(
                        f"**{m['home']} – {m['away']}{dbl}**  \n"
                        f"<span style='color:#94a3b8;font-size:0.9rem;'>{lname} · {m['aika']}</span> · Veikkauksia: **{pred_c}**",
                        unsafe_allow_html=True
                    )
                    uc1, uc2 = st.columns([3, 1])
                    with uc1:
                        score_in = st.text_input("Tulos", key=f"urgent_score_{m['id']}", label_visibility="collapsed", placeholder="esim. 2-1")
                    with uc2:
                        if st.button("Tallenna", key=f"urgent_save_{m['id']}", type="primary", use_container_width=True):
                            parsed = parse_score(score_in)
                            if not parsed:
                                st.error("Virheellinen muoto. Käytä esim. 2-1")
                            else:
                                h, a = parsed
                                save_real_result("match", m["id"], {"home_goals": h, "away_goals": a, "score": f"{h}-{a}"})
                                st.toast(f"Tulos tallennettu: {h}–{a}")
                                st.success(f"Tallennettu: {m['home']} {h}–{a} {m['away']}")
                                st.rerun()
                    st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            status = st.radio("Näytä", ["Kiireelliset + puuttuvat", "Vain puuttuvat", "Kaikki", "Vain syötetyt"],
                              horizontal=True, key="result_status_filter", index=0)
        with c2:
            list_f = st.selectbox("Lista", ["Kaikki listat"] + [n for n, _ in all_lists], key="result_list_filter")
        with c3:
            search = st.text_input("Haku (joukkue)", key="result_search")
        st.markdown("---")

        shown = False
        for lname, matches in all_lists:
            if list_f != "Kaikki listat" and list_f != lname:
                continue
            to_show = []
            for m in matches:
                real = load_real_result("match", m["id"])
                has = real is not None
                started = now >= m["start"]
                if status == "Vain puuttuvat" and has:
                    continue
                if status == "Vain syötetyt" and not has:
                    continue
                if status == "Kiireelliset + puuttuvat" and has:
                    continue
                if search and search.lower() not in m["home"].lower() and search.lower() not in m["away"].lower():
                    continue
                to_show.append((m, real, has, started))
            if not to_show:
                continue
            shown = True
            with st.expander(f"**{lname}** ({len(to_show)} ottelua)", expanded=(status in ("Vain puuttuvat", "Kiireelliset + puuttuvat"))):
                for m, real, has, started in to_show:
                    pred_c = count_predictions_for_match(m["id"])
                    dbl = " 🔥 TUPLAPISTEET" if m["double"] else ""
                    status_txt = f"Tallennettu: {real['home_goals']}–{real['away_goals']}" if has else ("Peli alkanut – tulos puuttuu!" if started else "Ei vielä tulosta")
                    status_col = "#22c55e" if has else ("#f87171" if started else "#64748b")
                    st.markdown(
                        f"**{m['home']} – {m['away']}{dbl}**  \n"
                        f"<span style='color:#94a3b8;font-size:0.9rem;'>{m['aika']}</span> · Veikkauksia: **{pred_c}** · "
                        f"<span style='color:{status_col};'>{status_txt}</span>",
                        unsafe_allow_html=True
                    )
                    def_score = f"{real['home_goals']}-{real['away_goals']}" if has else ""
                    cc1, cc2, cc3 = st.columns([2, 1, 1])
                    with cc1:
                        score_in = st.text_input("Tulos", value=def_score, key=f"score_in_{m['id']}", label_visibility="collapsed", placeholder="esim. 2-1")
                    with cc2:
                        save = st.button("Tallenna", key=f"save_res_{m['id']}", use_container_width=True)
                    with cc3:
                        if has:
                            dk = f"confirm_del_res_{m['id']}"
                            if not st.session_state.get(dk):
                                if st.button("Poista tulos", key=f"del_res_{m['id']}", use_container_width=True):
                                    st.session_state[dk] = True
                                    st.rerun()
                            else:
                                if st.button("Vahvista poisto", key=f"del_res_yes_{m['id']}", type="primary", use_container_width=True):
                                    delete_real_result("match", m["id"])
                                    st.session_state[dk] = False
                                    st.toast("Tulos poistettu")
                                    st.rerun()
                    if save:
                        parsed = parse_score(score_in)
                        if not parsed:
                            st.error("Virheellinen muoto. Käytä esim. 2-1")
                        else:
                            h, a = parsed
                            ow = f"confirm_overwrite_{m['id']}"
                            if has and (real["home_goals"] != h or real["away_goals"] != a):
                                if not st.session_state.get(ow):
                                    st.session_state[ow] = True
                                    st.warning(f"Tulos on jo {real['home_goals']}–{real['away_goals']}. Korvataanko {h}–{a}?")
                                    o1, o2 = st.columns(2)
                                    with o1:
                                        if st.button("Kyllä, korvaa", key=f"ow_yes_{m['id']}", type="primary"):
                                            save_real_result("match", m["id"], {"home_goals": h, "away_goals": a, "score": f"{h}-{a}"})
                                            st.session_state[ow] = False
                                            st.toast("Tulos päivitetty")
                                            st.rerun()
                                    with o2:
                                        if st.button("Peruuta", key=f"ow_no_{m['id']}"):
                                            st.session_state[ow] = False
                                            st.rerun()
                            else:
                                save_real_result("match", m["id"], {"home_goals": h, "away_goals": a, "score": f"{h}-{a}"})
                                st.toast(f"Tulos tallennettu: {h}–{a}")
                                st.success(f"Tulos tallennettu: {m['home']} {h}–{a} {m['away']}")
                                st.rerun()
                    st.markdown("---")
        if not shown:
            st.info("Ei otteluita valituilla suodattimilla.")

    elif admin_tab == "Pistekorjaukset":
        st.write("### ✏️ Manuaaliset pistekorjaukset")
        with get_db() as conn:
            usernames = [r["username"] for r in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]
        if not usernames:
            st.info("Ei käyttäjiä.")
        else:
            sel = st.selectbox("Valitse pelaaja", usernames, key="adj_user")
            mp = calculate_match_points_only(sel)
            bonus = get_adjustment_total(sel)
            st.markdown(f"**Ottelupisteet:** {mp} · **Korjaukset:** {bonus:+d} · **Yhteensä:** **{mp+bonus}**")
            st.write("#### Lisää korjaus")
            ac1, ac2 = st.columns([1, 3])
            with ac1:
                ap = st.number_input("Pisteet (+/-)", value=0, step=1, key="adj_pts")
            with ac2:
                ar = st.text_input("Syy", placeholder="esim. hyvitys / bonus", key="adj_reason")
            if st.button("Tallenna korjaus", type="primary"):
                if ap == 0:
                    st.error("Pisteiden määrä ei voi olla 0")
                else:
                    add_point_adjustment(sel, ap, ar, st.session_state.logged_in_user or "admin")
                    st.toast(f"Korjaus {ap:+d} p → {sel}")
                    st.success(f"Korjaus tallennettu: {ap:+d} p → {sel}")
                    st.rerun()
            st.markdown("---")
            st.write("#### Korjaushistoria")
            adjs = get_user_adjustments(sel)
            if not adjs:
                st.info("Ei korjauksia.")
            else:
                for adj in adjs:
                    created = adj["created_at"][:16].replace("T", " ") if adj["created_at"] else "-"
                    dc1, dc2 = st.columns([5, 1])
                    with dc1:
                        st.markdown(
                            f"**{adj['points']:+d} p** · {adj['reason'] or '—'}  \n"
                            f"<span style='color:#64748b;font-size:0.85rem;'>{created} · {adj['created_by'] or 'admin'}</span>",
                            unsafe_allow_html=True
                        )
                    with dc2:
                        dk = f"confirm_del_adj_{adj['id']}"
                        if not st.session_state.get(dk):
                            if st.button("Poista", key=f"del_adj_{adj['id']}"):
                                st.session_state[dk] = True
                                st.rerun()
                        else:
                            if st.button("Vahvista", key=f"del_adj_yes_{adj['id']}", type="primary"):
                                delete_point_adjustment(adj["id"])
                                st.session_state[dk] = False
                                st.toast("Korjaus poistettu")
                                st.rerun()
                    st.markdown("---")

    elif admin_tab == "Listabonukset":
        st.write("### 🏅 Listakohtaisten bonuspisteiden jako")
        st.caption("Valitse lista → katso sijoitukset → jaa bonukset valituille (tasapelit voit hoitaa vapaasti).")
        all_lists, _ = load_all_match_lists()
        if not all_lists:
            st.info("Ei listoja.")
        else:
            list_names = [n for n, _ in all_lists]
            sel_list = st.selectbox("Lista", list_names, key="bonus_list")
            list_idx = list_names.index(sel_list)
            standings = get_list_standings(list_idx)
            if not standings:
                st.info("Ei pelaajia.")
            else:
                st.markdown(f"**{sel_list} – sijoitukset**")
                for e in standings:
                    st.markdown(f"{e['rank']}. **{e['nimi']}** — {e['pisteet']} p")

                st.markdown("---")
                st.write("#### Jaa bonukset")
                st.caption("Oletus: 1. = +5, 2. = +3, 3. = +1. Tasapelissä valitse itse kenelle annat.")
                usernames = [e["nimi"] for e in standings]
                b1 = st.multiselect("🥇 +5 pistettä", usernames, key="bonus_gold")
                b2 = st.multiselect("🥈 +3 pistettä", usernames, key="bonus_silver")
                b3 = st.multiselect("🥉 +1 piste", usernames, key="bonus_bronze")

                if st.button("Jaa valitut bonukset", type="primary"):
                    admin_user = st.session_state.logged_in_user or "admin"
                    count = 0
                    for u in b1:
                        add_point_adjustment(u, 5, f"Listabonus 1. sija: {sel_list}", admin_user)
                        count += 1
                    for u in b2:
                        add_point_adjustment(u, 3, f"Listabonus 2. sija: {sel_list}", admin_user)
                        count += 1
                    for u in b3:
                        add_point_adjustment(u, 1, f"Listabonus 3. sija: {sel_list}", admin_user)
                        count += 1
                    if count:
                        st.toast(f"Jaettu {count} bonusta")
                        st.success(f"Jaettu {count} bonusmerkintää listalle {sel_list}")
                        st.rerun()
                    else:
                        st.warning("Valitse vähintään yksi pelaaja.")

    elif admin_tab == "Otteluiden hallinta":
        st.write("### 📅 Otteluiden hallinta")
        all_lists, lists_by_key = load_all_match_lists()
        st.caption("Ottelut tallennetaan tietokantaan. Voit lisätä, muokata ja poistaa ilman koodimuutoksia.")

        with st.expander("➕ Lisää uusi ottelu", expanded=False):
            existing_keys = list(lists_by_key.keys()) if lists_by_key else list(SEED_MATCHES.keys())
            list_key = st.selectbox("Lista (avain)", existing_keys + ["__new__"], key="new_match_list")
            if list_key == "__new__":
                list_key = st.text_input("Uusi listan avain (esim. liiga2)", key="new_list_key")
                list_name = st.text_input("Listan näyttönimi", key="new_list_name")
                pred_type = st.selectbox("Veikkaustyyppi", ["normal", "nhl"], key="new_pred_type")
            else:
                list_name = lists_by_key.get(list_key, {}).get("name") or SEED_MATCHES.get(list_key, {}).get("name", list_key)
                pred_type = lists_by_key.get(list_key, {}).get("pred_type") or SEED_MATCHES.get(list_key, {}).get("pred_type", "normal")
                st.text(f"Lista: {list_name} · Tyyppi: {pred_type}")

            mid = st.text_input("Ottelun ID (uniikki, esim. l1_15)", key="new_mid")
            home = st.text_input("Koti", key="new_home")
            away = st.text_input("Vieras", key="new_away")
            aika = st.text_input("Aika-teksti (esim. Pe 18.9. 18:30)", key="new_aika")
            start_str = st.text_input("Alku (ISO, esim. 2026-09-18T18:30:00)", key="new_start")
            is_double = st.checkbox("Tuplapisteet", key="new_double")
            sort_order = st.number_input("Järjestysnumero", value=100, step=1, key="new_order")

            if st.button("Tallenna ottelu", type="primary"):
                if not all([list_key, list_name, mid, home, away, aika, start_str]):
                    st.error("Täytä kaikki kentät")
                else:
                    try:
                        datetime.fromisoformat(start_str)
                        with get_db() as conn:
                            conn.execute(
                                "INSERT OR REPLACE INTO matches (id, list_key, list_name, home, away, aika, start_iso, is_double, sort_order, pred_type) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (mid, list_key, list_name, home, away, aika, start_str, 1 if is_double else 0, int(sort_order), pred_type)
                            )
                        clear_matches_cache()
                        clear_points_cache()
                        st.toast("Ottelu tallennettu")
                        st.success("Ottelu tallennettu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Virhe: {e}")

        st.markdown("---")
        st.write("#### Nykyiset ottelut")
        for lname, matches in all_lists:
            with st.expander(f"{lname} ({len(matches)})"):
                for m in matches:
                    dbl = " 🔥" if m["double"] else ""
                    st.markdown(f"**{m['id']}** · {m['home']} – {m['away']}{dbl} · {m['aika']} · `{m['start'].isoformat()}`")
                    cols = st.columns([1, 1, 3])
                    with cols[0]:
                        if st.button("Poista", key=f"del_match_{m['id']}"):
                            with get_db() as conn:
                                conn.execute("DELETE FROM matches WHERE id=?", (m["id"],))
                            clear_matches_cache()
                            clear_points_cache()
                            st.toast(f"Poistettu {m['id']}")
                            st.rerun()
                    with cols[1]:
                        new_dbl = st.checkbox("Tupla", value=m["double"], key=f"dbl_{m['id']}")
                        if new_dbl != m["double"]:
                            with get_db() as conn:
                                conn.execute("UPDATE matches SET is_double=? WHERE id=?", (1 if new_dbl else 0, m["id"]))
                            clear_matches_cache()
                            clear_points_cache()
                            st.rerun()

        st.markdown("---")
        st.write("#### Vie / tuo JSON")
        export_data = {}
        for key, info in (lists_by_key or {}).items():
            export_data[key] = {
                "name": info["name"],
                "pred_type": info["pred_type"],
                "matches": [
                    {
                        "id": m["id"], "home": m["home"], "away": m["away"],
                        "aika": m["aika"], "start": m["start"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "double": m["double"]
                    }
                    for m in info["matches"]
                ]
            }
        st.download_button(
            "⬇️ Lataa ottelut JSON",
            json.dumps(export_data, ensure_ascii=False, indent=2),
            f"matches_{datetime.now(HELSINKI).strftime('%Y%m%d')}.json",
            "application/json"
        )

    elif admin_tab == "Varmuuskopiointi & palautus":
        st.subheader("💾 Varmuuskopiointi ja palautus")
        with get_db() as conn:
            uc = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            pc = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            rc = conn.execute("SELECT COUNT(*) FROM real_results").fetchone()[0]
            ac = conn.execute("SELECT COUNT(*) FROM point_adjustments").fetchone()[0]
            cc = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
            mc = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        st.info(f"**Nykyinen tila:**  \n• Käyttäjiä: **{uc}**  \n• Veikkauksia: **{pc}**  \n• Tuloksia: **{rc}**  \n• Korjauksia: **{ac}**  \n• Kommentteja: **{cc}**  \n• Otteluita: **{mc}**")
        st.write("#### Lataa varmuuskopio")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            if os.path.exists(DB_FILE):
                z.write(DB_FILE, arcname="veikkaus.db")
        buf.seek(0)
        st.download_button(
            "⬇️ Lataa varmuuskopio (.zip)",
            buf,
            f"haamuhanska_backup_{datetime.now(HELSINKI).strftime('%Y-%m-%d_%H-%M')}.zip",
            "application/zip",
            type="primary",
            use_container_width=True
        )
        st.markdown("---")
        st.write("#### Palauta varmuuskopio")
        st.warning("Palautus korvaa nykyisen datan.")
        up = st.file_uploader("Valitse .zip", type=["zip"])
        if up:
            rk = "confirm_restore_backup"
            if not st.session_state.get(rk):
                if st.button("🔄 Palauta", type="primary", use_container_width=True):
                    st.session_state[rk] = True
                    st.rerun()
            else:
                st.error("Haluatko varmasti palauttaa? Nykyinen data ylikirjoitetaan.")
                r1, r2 = st.columns(2)
                with r1:
                    if st.button("Kyllä, palauta", type="primary", use_container_width=True):
                        try:
                            with zipfile.ZipFile(up) as z:
                                if "veikkaus.db" in z.namelist():
                                    with open(DB_FILE, "wb") as f:
                                        f.write(z.read("veikkaus.db"))
                                else:
                                    st.error("veikkaus.db puuttuu")
                                    st.stop()
                            clear_points_cache()
                            clear_matches_cache()
                            st.session_state[rk] = False
                            st.toast("Palautettu!")
                            st.success("✅ Palautettu!")
                            st.rerun()
                        except Exception as e:
                            st.session_state[rk] = False
                            st.error(f"Virhe: {e}")
                with r2:
                    if st.button("Peruuta", use_container_width=True):
                        st.session_state[rk] = False
                        st.rerun()

    elif admin_tab == "Keskustelu":
        st.subheader("💬 Keskustelun tyhjennys")
        st.warning("Poistaa **kaikki** kommentit pysyvästi.")
        ck = "confirm_clear_comments"
        if not st.session_state.get(ck):
            if st.button("Tyhjennä koko keskustelu", type="primary"):
                st.session_state[ck] = True
                st.rerun()
        else:
            st.error("Haluatko varmasti tyhjentää?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Kyllä, tyhjennä", type="primary"):
                    delete_all_comments()
                    st.session_state[ck] = False
                    st.toast("Keskustelu tyhjennetty")
                    st.success("✅ Tyhjennetty!")
                    st.rerun()
            with cc2:
                if st.button("Peruuta"):
                    st.session_state[ck] = False
                    st.rerun()
