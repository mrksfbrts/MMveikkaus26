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

SITE_PASSWORD = get_secret("site_password", "SITE_PASSWORD", "kisa2026")
ADMIN_PASSWORD = get_secret("admin_password", "ADMIN_PASSWORD", "admin123")
DB_FILE = os.environ.get("DB_PATH", "veikkaus.db")

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
@media (max-width:768px) {
    .etusivu-otsikko { font-size:1.65rem !important; white-space:normal !important; letter-spacing:1.2px !important; }
}
button[kind="primary"] {
    background-color: #16a34a !important;
    color: #ffffff !important;
    border: 1px solid #16a34a !important;
}
button[kind="primary"]:hover {
    background-color: #15803d !important;
    border-color: #15803d !important;
    color: #ffffff !important;
}
button[kind="primary"]:focus {
    box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.4) !important;
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
        edited_at TEXT
    )''')

    # Indeksit suorituskykyä varten
    c.execute("CREATE INDEX IF NOT EXISTS idx_pred_user_match ON predictions(username, match_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pred_match ON predictions(match_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_results_id ON real_results(id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_adj_user ON point_adjustments(username)")

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

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
    except:
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

def add_comment(username, text):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (username, text, created_at) VALUES (?,?,?)",
            (username, text, datetime.now(HELSINKI).isoformat())
        )

def get_comments():
    with get_db() as conn:
        return conn.execute("SELECT * FROM comments ORDER BY created_at DESC").fetchall()

def update_comment(cid, text):
    with get_db() as conn:
        conn.execute(
            "UPDATE comments SET text=?, edited_at=? WHERE id=?",
            (text, datetime.now(HELSINKI).isoformat(), cid)
        )

def delete_comment(cid):
    with get_db() as conn:
        conn.execute("DELETE FROM comments WHERE id=?", (cid,))

def delete_all_comments():
    with get_db() as conn:
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

def calculate_match_points_only(username):
    total = 0
    for matches in [LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]:
        for m in matches:
            total += calculate_match_points(
                load_prediction(username, m["id"]),
                load_real_result("match", m["id"]),
                m["double"]
            )
    return total

def calculate_user_points(username):
    return calculate_match_points_only(username) + get_adjustment_total(username)

def calculate_list_points(username, matches):
    total = done = 0
    for m in matches:
        pred = load_prediction(username, m["id"])
        if pred:
            done += 1
        total += calculate_match_points(pred, load_real_result("match", m["id"]), m["double"])
    return total, done, len(matches)

def get_completed_percentage(username, matches):
    user_pts = max_pts = 0
    for m in matches:
        real = load_real_result("match", m["id"])
        if real is None:
            continue
        max_pts += 20 if m.get("double") else 10
        user_pts += calculate_match_points(load_prediction(username, m["id"]), real, m["double"])
    return min(100, int(user_pts / max_pts * 100)) if max_pts else 0

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
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border};border-radius:12px;padding:12px 14px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="color:#64748b;min-width:1.8rem;font-weight:700;font-size:1.05rem;">{i}.</span>
                <span style="color:{name_col};font-weight:{weight};">{html.escape(name)}</span>
            </div>
            <span style="font-weight:700;color:#22c55e;font-size:1.15rem;">{points}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:7px;">
            <div class="rank-bar-bg" style="flex:1;"><div class="rank-bar-fill" style="width:{pct}%;"></div></div>
            <span style="font-size:0.75rem;color:#94a3b8;min-width:32px;text-align:right;">{pct}%</span>
        </div>
    </div>""", unsafe_allow_html=True)

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

# ====================== OTTELULISTAT ======================
LIIGA_MATCHES = [
    {"id":"l1_1","home":"KalPa","away":"HPK","aika":"Ti 15.9. 18:30","start":datetime(2026,9,15,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_2","home":"Pelicans","away":"Tappara","aika":"Ti 15.9. 18:30","start":datetime(2026,9,15,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_3","home":"SaiPa","away":"K-Espoo","aika":"Ti 15.9. 18:30","start":datetime(2026,9,15,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_4","home":"TPS","away":"Jukurit","aika":"Ti 15.9. 18:30","start":datetime(2026,9,15,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_5","home":"Ässät","away":"Sport","aika":"Ti 15.9. 18:30","start":datetime(2026,9,15,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_6","home":"HIFK","away":"Jukurit","aika":"Ke 16.9. 18:30","start":datetime(2026,9,16,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_7","home":"KooKoo","away":"JYP","aika":"Ke 16.9. 18:30","start":datetime(2026,9,16,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_8","home":"Kärpät","away":"Ilves","aika":"Ke 16.9. 18:30","start":datetime(2026,9,16,18,30,tzinfo=HELSINKI),"double":True},
    {"id":"l1_9","home":"Jokerit","away":"JYP","aika":"To 17.9. 18:30","start":datetime(2026,9,17,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_10","home":"Lukko","away":"Sport","aika":"To 17.9. 18:30","start":datetime(2026,9,17,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_11","home":"TPS","away":"Tappara","aika":"To 17.9. 18:30","start":datetime(2026,9,17,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_12","home":"Jukurit","away":"Pelicans","aika":"Pe 18.9. 18:30","start":datetime(2026,9,18,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_13","home":"KalPa","away":"Ilves","aika":"Pe 18.9. 18:30","start":datetime(2026,9,18,18,30,tzinfo=HELSINKI),"double":False},
    {"id":"l1_14","home":"KooKoo","away":"SaiPa","aika":"Pe 18.9. 19:30","start":datetime(2026,9,18,19,30,tzinfo=HELSINKI),"double":False},
]

VALIOLIIGA_MATCHES = [
    {"id":"l2_1","home":"Brentford","away":"Chelsea","aika":"Pe 18.9. 22:00","start":datetime(2026,9,18,22,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_2","home":"Spurs","away":"Aston Villa","aika":"La 19.9. 14:30","start":datetime(2026,9,19,14,30,tzinfo=HELSINKI),"double":True},
    {"id":"l2_3","home":"Brighton","away":"Arsenal","aika":"La 19.9. 17:00","start":datetime(2026,9,19,17,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_4","home":"Everton","away":"Ipswich","aika":"La 19.9. 17:00","start":datetime(2026,9,19,17,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_5","home":"Leeds","away":"Crystal Palace","aika":"La 19.9. 17:00","start":datetime(2026,9,19,17,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_6","home":"Man City","away":"Sunderland","aika":"La 19.9. 17:00","start":datetime(2026,9,19,17,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_7","home":"Newcastle","away":"Hull City","aika":"La 19.9. 17:00","start":datetime(2026,9,19,17,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_8","home":"Nott'm Forest","away":"Coventry","aika":"La 19.9. 19:30","start":datetime(2026,9,19,19,30,tzinfo=HELSINKI),"double":False},
    {"id":"l2_9","home":"Bournemouth","away":"Liverpool","aika":"Su 20.9. 16:00","start":datetime(2026,9,20,16,0,tzinfo=HELSINKI),"double":False},
    {"id":"l2_10","home":"Fulham","away":"Man Utd","aika":"Su 20.9. 18:30","start":datetime(2026,9,20,18,30,tzinfo=HELSINKI),"double":False},
]

EURO_MATCHES = [
    {"id":"l3_1","home":"Bayern","away":"Union Berlin","aika":"Pe 18.9. 21:30","start":datetime(2026,9,18,21,30,tzinfo=HELSINKI),"double":False},
    {"id":"l3_2","home":"Roma","away":"Inter","aika":"La 19.9. 19:00","start":datetime(2026,9,19,19,0,tzinfo=HELSINKI),"double":False},
    {"id":"l3_3","home":"Celtic","away":"Rangers","aika":"Su 20.9. 14:00","start":datetime(2026,9,20,14,0,tzinfo=HELSINKI),"double":False},
    {"id":"l3_4","home":"Leverkusen","away":"RB Leipzig","aika":"Su 20.9. 16:30","start":datetime(2026,9,20,16,30,tzinfo=HELSINKI),"double":False},
    {"id":"l3_5","home":"PSV","away":"Twente","aika":"Su 20.9. 17:45","start":datetime(2026,9,20,17,45,tzinfo=HELSINKI),"double":False},
    {"id":"l3_6","home":"Porto","away":"Benfica","aika":"Su 20.9. 18:00","start":datetime(2026,9,20,18,0,tzinfo=HELSINKI),"double":False},
    {"id":"l3_7","home":"Juventus","away":"Atalanta","aika":"Su 20.9. 19:00","start":datetime(2026,9,20,19,0,tzinfo=HELSINKI),"double":False},
    {"id":"l3_8","home":"Marseille","away":"PSG","aika":"Su 20.9. 21:45","start":datetime(2026,9,20,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l3_9","home":"Atlético","away":"Real Madrid","aika":"Su 20.9. 22:00","start":datetime(2026,9,20,22,0,tzinfo=HELSINKI),"double":True},
    {"id":"l3_10","home":"Sevilla","away":"Barcelona","aika":"Su 20.9. 22:00","start":datetime(2026,9,20,22,0,tzinfo=HELSINKI),"double":False},
]

NATIONS_MATCHES = [
    {"id":"l4_1","home":"Alankomaat","away":"Saksa","aika":"To 24.9. 21:45","start":datetime(2026,9,24,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_2","home":"Norja","away":"Tanska","aika":"To 24.9. 21:45","start":datetime(2026,9,24,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_3","home":"Portugali","away":"Wales","aika":"To 24.9. 21:45","start":datetime(2026,9,24,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_4","home":"Italia","away":"Belgia","aika":"Pe 25.9. 21:45","start":datetime(2026,9,25,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_5","home":"Turkki","away":"Ranska","aika":"Pe 25.9. 21:45","start":datetime(2026,9,25,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_6","home":"San Marino","away":"Suomi","aika":"La 26.9. 19:00","start":datetime(2026,9,26,19,0,tzinfo=HELSINKI),"double":True},
    {"id":"l4_7","home":"Englanti","away":"Espanja","aika":"La 26.9. 21:45","start":datetime(2026,9,26,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_8","home":"Norja","away":"Portugali","aika":"Su 27.9. 21:45","start":datetime(2026,9,27,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_9","home":"Saksa","away":"Kreikka","aika":"Su 27.9. 21:45","start":datetime(2026,9,27,21,45,tzinfo=HELSINKI),"double":False},
    {"id":"l4_10","home":"Belgia","away":"Ranska","aika":"Ma 28.9. 21:45","start":datetime(2026,9,28,21,45,tzinfo=HELSINKI),"double":False},
]

NHL_MATCHES = [
    {"id":"l5_1","home":"Florida","away":"Carolina","aika":"Ti 29.9. 00:00","start":datetime(2026,9,29,0,0,tzinfo=HELSINKI),"double":True},
    {"id":"l5_2","home":"Toronto","away":"Montreal","aika":"Ti 29.9. 02:00","start":datetime(2026,9,29,2,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_3","home":"Boston","away":"NY Rangers","aika":"Ti 29.9. 03:00","start":datetime(2026,9,29,3,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_4","home":"Edmonton","away":"Vancouver","aika":"Ti 29.9. 05:00","start":datetime(2026,9,29,5,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_5","home":"Vegas","away":"Chicago","aika":"Ti 29.9. 05:30","start":datetime(2026,9,29,5,30,tzinfo=HELSINKI),"double":False},
    {"id":"l5_6","home":"Philadelphia","away":"Pittsburgh","aika":"Ke 30.9. 02:30","start":datetime(2026,9,30,2,30,tzinfo=HELSINKI),"double":False},
    {"id":"l5_7","home":"Toronto","away":"NY Islanders","aika":"Ke 30.9. 02:30","start":datetime(2026,9,30,2,30,tzinfo=HELSINKI),"double":False},
    {"id":"l5_8","home":"Colorado","away":"LA Kings","aika":"Ke 30.9. 05:00","start":datetime(2026,9,30,5,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_9","home":"New Jersey","away":"Philadelphia","aika":"To 1.10. 02:00","start":datetime(2026,10,1,2,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_10","home":"NY Rangers","away":"Tampa Bay","aika":"To 1.10. 02:00","start":datetime(2026,10,1,2,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_11","home":"Columbus","away":"Buffalo","aika":"To 1.10. 02:00","start":datetime(2026,10,1,2,0,tzinfo=HELSINKI),"double":False},
    {"id":"l5_12","home":"Nashville","away":"Minnesota","aika":"To 1.10. 03:00","start":datetime(2026,10,1,3,0,tzinfo=HELSINKI),"double":False},
]

ALL_MATCH_LISTS = [
    ("Lista 1 – SM-Liiga", LIIGA_MATCHES),
    ("Lista 2 – Valioliiga", VALIOLIIGA_MATCHES),
    ("Lista 3 – Europelien helmiä", EURO_MATCHES),
    ("Lista 4 – Kansojen liiga", NATIONS_MATCHES),
    ("Lista 5 – NHL-Tusina", NHL_MATCHES),
]

# ====================== VÄLIMUISTI & BULK-PISTEET ======================
@st.cache_data(ttl=60)
def get_full_points_data():
    """Hakee kaiken datan kerralla ja laskee pisteet muistissa."""
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

    match_lists = [LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]
    all_matches = [m for lst in match_lists for m in lst]

    user_stats = {}
    for u in users:
        total = adj_map.get(u, 0)
        list_pts = [0] * 5
        list_pct = [0] * 5

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

        # Kokonaisprosentti
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
        }
    return user_stats, users

@st.cache_data(ttl=60)
def get_all_standings():
    user_stats, users = get_full_points_data()
    standings = [
        {"nimi": u, "pisteet": user_stats[u]["total"], "pct": user_stats[u]["pct"]}
        for u in users
    ]
    return sorted(standings, key=lambda x: (-x["pisteet"], x["nimi"].lower()))

@st.cache_data(ttl=60)
def get_list_standings(list_index: int):
    user_stats, users = get_full_points_data()
    standings = [
        {
            "nimi": u,
            "pisteet": user_stats[u]["list_pts"][list_index],
            "pct": user_stats[u]["list_pct"][list_index],
        }
        for u in users
    ]
    return sorted(standings, key=lambda x: (-x["pisteet"], x["nimi"].lower()))

def clear_points_cache():
    get_full_points_data.clear()
    get_all_standings.clear()
    get_list_standings.clear()

def get_user_rank(username):
    standings = get_all_standings()
    if not standings:
        return 1, 1
    for i, e in enumerate(standings, 1):
        if e["nimi"] == username:
            return i, len(standings)
    return len(standings), len(standings)

def get_next_open_match():
    now = datetime.now(HELSINKI)
    candidates = [
        m for matches in [LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]
        for m in matches if now < m["start"]
    ]
    return min(candidates, key=lambda x: x["start"]) if candidates else None

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

# Scroll to top
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
        done = total_m = open_m = 0
        for matches in [LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]:
            for m in matches:
                total_m += 1
                if load_prediction(uname, m["id"]):
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

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 2.2, 1])
        with mid:
            st.markdown("#### 💬 Viimeisimmät kommentit...")
            comments = get_comments()[:3]
            if not comments:
                st.info("Ei vielä kommentteja.")
            else:
                for c in comments:
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
            standings = get_all_standings()[:3]
        if not standings:
            st.info("Ei vielä pelaajia.")
        else:
            with get_db() as conn:
                user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
            st.markdown(
                f'<div style="color:#94a3b8;margin-bottom:14px;font-size:0.85rem;">Osallistujia: <b style="color:#e2e8f0;">{user_count}</b> · Ajankohta: <b style="color:#e2e8f0;">Syyskuu 2026</b></div>',
                unsafe_allow_html=True
            )
            for i, e in enumerate(standings):
                render_hof_card(
                    ["🥇", "🥈", "🥉"][i],
                    ["#fbbf24", "#94a3b8", "#d97706"][i],
                    ["rgba(251,191,36,0.10)", "rgba(148,163,184,0.08)", "rgba(217,119,6,0.08)"][i],
                    e["nimi"], e["pisteet"], e["pct"]
                )

    for idx, contest in enumerate(PAST):
        with tabs[idx + 1]:
            st.markdown(
                f'<div style="color:#94a3b8;margin-bottom:14px;font-size:0.85rem;">Osallistujia: <b style="color:#e2e8f0;">{contest["participants"]}</b> · Ajankohta: <b style="color:#e2e8f0;">{contest["date"]}</b></div>',
                unsafe_allow_html=True
            )
            for i, e in enumerate(contest["standings"]):
                pct = min(100, int(e["pisteet"] / contest["max_points"] * 100)) if contest.get("max_points") else 0
                render_hof_card(
                    ["🥇", "🥈", "🥉"][i],
                    ["#fbbf24", "#94a3b8", "#d97706"][i],
                    ["rgba(251,191,36,0.10)", "rgba(148,163,184,0.08)", "rgba(217,119,6,0.08)"][i],
                    e["nimi"], e["pisteet"], pct
                )

# ====================== VEIKKAUSKISA ======================
if page == "VEIKKAUSKISA":
    st.subheader("Syyskuun palloilupaketti - veikkauslistat")
    st.divider()
    tabs = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_normal_list(matches, prefix):
        now = datetime.now(HELSINKI)
        for m in matches:
            if now >= m["start"]:
                continue
            tl = m["start"] - now
            countdown = f"{tl.days} pv {tl.seconds//3600:02d}:{(tl.seconds%3600)//60:02d}" if tl.days > 0 else f"{tl.seconds//3600:02d}:{(tl.seconds%3600)//60:02d}"
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = saved and "home_goals" in saved
            dbl = '<span style="background:linear-gradient(135deg,#f97316,#ef4444);color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔥 TUPLAPISTEET</span>' if m["double"] else ""
            st.markdown(
                f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:#f1f5f9;">{m["home"]} – {m["away"]}</span>{dbl}</div>'
                f'<div style="font-size:0.88rem;color:#94a3b8;margin-bottom:10px;">{m["aika"]} | Aikaa: <b style="color:#22c55e;">{countdown}</b></div>',
                unsafe_allow_html=True
            )
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

    def render_nhl_list(matches):
        now = datetime.now(HELSINKI)
        for m in matches:
            if now >= m["start"]:
                continue
            tl = m["start"] - now
            countdown = f"{tl.days} pv {tl.seconds//3600:02d}:{(tl.seconds%3600)//60:02d}" if tl.days > 0 else f"{tl.seconds//3600:02d}:{(tl.seconds%3600)//60:02d}"
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = saved and "mark" in saved
            dbl = '<span style="background:linear-gradient(135deg,#f97316,#ef4444);color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔥 TUPLAPISTEET</span>' if m["double"] else ""
            st.markdown(
                f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:#f1f5f9;">{m["home"]} – {m["away"]}</span>{dbl}</div>'
                f'<div style="font-size:0.88rem;color:#94a3b8;margin-bottom:10px;">{m["aika"]} | Aikaa: <b style="color:#22c55e;">{countdown}</b></div>',
                unsafe_allow_html=True
            )
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
                    c1, c2 = st.columns(2)
                    default_home = (saved.get("home_opts", []) if saved else [])[:hc]
                    default_away = (saved.get("away_opts", []) if saved else [])[:ac]
                    with c1:
                        home_opts = st.multiselect(f"**{m['home']}** ({hc} kpl)", range(13), default=default_home, key=f"nhl_home_{m['id']}")
                    with c2:
                        away_opts = st.multiselect(f"**{m['away']}** ({ac} kpl)", range(13), default=default_away, key=f"nhl_away_{m['id']}")
                    if st.button("Päivitä veikkaus" if has else "Tallenna veikkaus", type="secondary" if has else "primary", key=f"nhl_save_{m['id']}", use_container_width=True):
                        if len(home_opts) != hc or len(away_opts) != ac:
                            st.error(f"Valitse tasan **{hc}** kotimaalia ja **{ac}** vierasmaalia")
                        else:
                            save_prediction(
                                st.session_state.logged_in_user, m["id"],
                                {"mark": mark, "split": split, "home_opts": sorted(set(home_opts)), "away_opts": sorted(set(away_opts))}
                            )
                            clear_points_cache()
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

    with tabs[0]:
        render_normal_list(LIIGA_MATCHES, "l1")
    with tabs[1]:
        render_normal_list(VALIOLIIGA_MATCHES, "l2")
    with tabs[2]:
        render_normal_list(EURO_MATCHES, "l3")
    with tabs[3]:
        render_normal_list(NATIONS_MATCHES, "l4")
    with tabs[4]:
        render_nhl_list(NHL_MATCHES)

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    col_rank, col_chat = st.columns([1.45, 1.75], gap="large")
    with col_rank:
        st.subheader("🏆 Veikkaustilanne")
        with get_db() as conn:
            users = [r["username"] for r in conn.execute("SELECT username FROM users ORDER BY username").fetchall()]
        if not users:
            st.info("Ei vielä yhtään rekisteröitynyttä pelaajaa.")
        else:
            tabs = st.tabs(["Veikkauskisan kokonaistilanne"] + [f"Lista {i}" for i in range(1, 6)])
            with tabs[0]:
                with st.spinner("Ladataan sijoituksia..."):
                    standings = get_all_standings()
                for i, e in enumerate(standings, 1):
                    render_ranking_row(i, e["nimi"], e["pisteet"], e["pct"], e["nimi"] == st.session_state.logged_in_user)
            for ti, (name, matches) in enumerate(ALL_MATCH_LISTS):
                with tabs[ti + 1]:
                    st.markdown(
                        f'<div style="background:rgba(30,41,59,0.6);border:1px solid #334155;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:0.9rem;color:#94a3b8;">'
                        f'<b style="color:#e2e8f0;">{name}</b><br>Bonuspisteet jaetaan, kun lista on pelattu!</div>',
                        unsafe_allow_html=True
                    )
                    with st.spinner("Ladataan listan sijoituksia..."):
                        standings = get_list_standings(ti)
                    for i, e in enumerate(standings, 1):
                        render_ranking_row(i, e["nimi"], e["pisteet"], e["pct"], e["nimi"] == st.session_state.logged_in_user)

    with col_chat:
        st.subheader("📣 Sana on vapaa!")
        comments = get_comments()
        per_page = 5
        total_pages = max(1, (len(comments) + per_page - 1) // per_page)
        if "comment_page" not in st.session_state:
            st.session_state.comment_page = 1
        st.session_state.comment_page = max(1, min(st.session_state.comment_page, total_pages))
        page_c = st.session_state.comment_page
        displayed = comments[(page_c - 1) * per_page : page_c * per_page]

        if displayed:
            for c in displayed:
                is_own = c["username"] == st.session_state.get("logged_in_user")
                t = c["created_at"][8:10] + "." + c["created_at"][5:7] + ". " + c["created_at"][11:16]
                if c["edited_at"]:
                    t += " (muokattu)"
                col_m, col_b = st.columns([34, 3])
                with col_m:
                    st.markdown(f"""
                    <div style="background:{"rgba(34,197,94,0.08)" if is_own else "#1e293b"};padding:14px 16px;border-radius:12px;margin-bottom:8px;border-left:4px solid {"#22c55e" if is_own else "#334155"};">
                        <strong style="color:#f1f5f9;">{html.escape(c['username'])}</strong>
                        <span style="color:#64748b;font-size:0.85rem;margin-left:18px;">{t}</span><br>
                        <div style="margin-top:6px;color:#cbd5e1;line-height:1.45;">{html.escape(c['text'])}</div>
                    </div>""", unsafe_allow_html=True)
                with col_b:
                    if is_own:
                        st.write("")
                        if st.button("✏️", key=f"edit_{c['id']}", help="Muokkaa"):
                            st.session_state.editing_comment = c["id"]
                            st.rerun()
        else:
            st.info("Ei vielä kommentteja. Ole ensimmäinen!")

        if total_pages > 1:
            c1, c2, c3, c4 = st.columns([2, 1, 2, 0.5])
            with c1:
                if st.button("← Edellinen", disabled=page_c <= 1, use_container_width=True):
                    st.session_state.comment_page -= 1
                    st.rerun()
            with c2:
                st.markdown(f"<div style='text-align:center;padding-top:8px;color:#94a3b8;'>Sivu {page_c} / {total_pages}</div>", unsafe_allow_html=True)
            with c3:
                if st.button("Seuraava →", disabled=page_c >= total_pages, use_container_width=True):
                    st.session_state.comment_page += 1
                    st.rerun()

        if st.session_state.get("editing_comment") is not None:
            cid = st.session_state.editing_comment
            cur = next((c for c in comments if c["id"] == cid), None)
            if cur:
                st.write("**Muokkaa kommenttiasi:**")
                nt = st.text_area("Kommentti", value=cur["text"], height=100, key="edit_text")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Tallenna", type="primary", key="save_edit") and nt.strip():
                        update_comment(cid, nt.strip())
                        st.session_state.editing_comment = None
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
                            st.rerun()
                    else:
                        if st.button("🗑️ Poista viesti", key=f"delete_{cid}"):
                            st.session_state[f"confirm_delete_{cid}"] = True
                            st.rerun()

        if st.session_state.get("logged_in_user"):
            with st.form("comment_form", clear_on_submit=True):
                nc = st.text_area("Kirjoita kommentti...", height=100, placeholder="Anna palaa.... 🔥", max_chars=600, label_visibility="collapsed")
                if st.form_submit_button("💥 Julkaise", use_container_width=True) and nc.strip():
                    add_comment(st.session_state.logged_in_user, nc.strip())
                    st.session_state.comment_page = 1
                    st.rerun()
        else:
            st.warning("Kirjaudu sisään kirjoittaaksesi kommentteja.")

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    st.subheader("Omat veikkaukset")
    st.divider()
    tabs = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_own(matches):
        uname = st.session_state.logged_in_user
        pts, done, total = calculate_list_points(uname, matches)
        summary_card("Yhteensä", f"{pts} pistettä", f"{done}/{total} veikkausta tallennettu")
        found = False
        for m in matches:
            saved = load_prediction(uname, m["id"])
            if not saved:
                continue
            found = True
            real = load_real_result("match", m["id"])
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

    for i, matches in enumerate([LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]):
        with tabs[i]:
            render_own(matches)

# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("Kaikkien veikkaukset")
    st.divider()
    tabs = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_all(matches, list_name):
        now = datetime.now(HELSINKI)
        closed = sum(1 for m in matches if now >= m["start"] or load_real_result("match", m["id"]))
        summary_card(list_name, f"{closed}/{len(matches)}", "Näkymässä vain sulkeutuneet veikkauskohteet")
        shown = False
        me = st.session_state.logged_in_user
        for m in matches:
            real = load_real_result("match", m["id"])
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
                    score = (
                        f"1X2:{p.get('mark')} | {', '.join(f'{h}–{a}' for h in p.get('home_opts', []) for a in p.get('away_opts', []))}"
                        if "mark" in p else f"{p.get('home_goals')}–{p.get('away_goals')}"
                    )
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

    for i, (name, matches) in enumerate(ALL_MATCH_LISTS):
        with tabs[i]:
            render_all(matches, f"Lista {i+1}")

# ====================== KISAINFON ======================
if page == "Kisainfo":
    page_header(
        "Tervetuloa veikkaamaan!",
        "Syyskuun palloilupaketti- veikkauskisa sisältää viisi erillistä veikkauslistaa ja yhteensä 56 peliä. Veikattavana on jääkiekkoa Suomesta ja rapakon takaa sekä jalkapalloa ympäri Eurooppaa niin seura- kuin maajoukkuetasolta. Yksittäisen listan kärkikolmikolle on luvassa bonuspisteitä, mutta koko kisan kuittaa itselleen tietenkin pärjäämällä parhaiten kaikissa viidessä listassa yhteensä. Onnea veikkauksiin!"
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
        ["Käyttäjien hallinta", "Tulosten syöttö", "Pistekorjaukset", "Varmuuskopiointi & palautus", "Tulevan kisan asetukset"],
        horizontal=True
    )

    if admin_tab == "Käyttäjien hallinta":
        st.write("### 👥 Käyttäjien hallinta")
        with get_db() as conn:
            users = conn.execute("SELECT username, created_at FROM users ORDER BY username").fetchall()
        if not users:
            st.info("Ei käyttäjiä.")
        else:
            for u in users:
                uname = u["username"]
                match_pts = calculate_match_points_only(uname)
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
                                st.rerun()
                        with n:
                            if st.button("Peruuta", key=f"del_no_{uname}"):
                                st.session_state[key] = False
                                st.rerun()
                st.markdown("---")

    elif admin_tab == "Tulosten syöttö":
        st.write("### 📊 Tulosten syöttö")
        now = datetime.now(HELSINKI)
        total = missing = started_missing = 0
        for _, matches in ALL_MATCH_LISTS:
            for m in matches:
                total += 1
                if load_real_result("match", m["id"]) is None:
                    missing += 1
                    if now >= m["start"]:
                        started_missing += 1
        st.info(f"**Otteluita:** {total} · **Syöttämättä:** {missing} · **Alkaneet ilman tulosta:** {started_missing}")
        c1, c2, c3 = st.columns(3)
        with c1:
            status = st.radio("Näytä", ["Vain puuttuvat", "Kaikki", "Vain syötetyt"], horizontal=True, key="result_status_filter")
        with c2:
            list_f = st.selectbox("Lista", ["Kaikki listat"] + [n for n, _ in ALL_MATCH_LISTS], key="result_list_filter")
        with c3:
            search = st.text_input("Haku (joukkue)", key="result_search")
        st.markdown("---")

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
            except:
                return None

        shown = False
        for lname, matches in ALL_MATCH_LISTS:
            if list_f != "Kaikki listat" and list_f != lname:
                continue
            to_show = []
            for m in matches:
                real = load_real_result("match", m["id"])
                has = real is not None
                if status == "Vain puuttuvat" and has:
                    continue
                if status == "Vain syötetyt" and not has:
                    continue
                if search and search.lower() not in m["home"].lower() and search.lower() not in m["away"].lower():
                    continue
                to_show.append((m, real, has))
            if not to_show:
                continue
            shown = True
            with st.expander(f"**{lname}** ({len(to_show)} ottelua)", expanded=(status == "Vain puuttuvat")):
                for m, real, has in to_show:
                    pred_c = count_predictions_for_match(m["id"])
                    started = now >= m["start"]
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
                                            st.rerun()
                                    with o2:
                                        if st.button("Peruuta", key=f"ow_no_{m['id']}"):
                                            st.session_state[ow] = False
                                            st.rerun()
                            else:
                                save_real_result("match", m["id"], {"home_goals": h, "away_goals": a, "score": f"{h}-{a}"})
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
                                st.rerun()
                    st.markdown("---")

    elif admin_tab == "Varmuuskopiointi & palautus":
        st.subheader("💾 Varmuuskopiointi ja palautus")
        with get_db() as conn:
            uc = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            pc = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            rc = conn.execute("SELECT COUNT(*) FROM real_results").fetchone()[0]
            ac = conn.execute("SELECT COUNT(*) FROM point_adjustments").fetchone()[0]
            cc = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        st.info(f"**Nykyinen tila:**  \n• Käyttäjiä: **{uc}**  \n• Veikkauksia: **{pc}**  \n• Tuloksia: **{rc}**  \n• Korjauksia: **{ac}**  \n• Kommentteja: **{cc}**")
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
                            st.session_state[rk] = False
                            st.success("✅ Palautettu!")
                            st.rerun()
                        except Exception as e:
                            st.session_state[rk] = False
                            st.error(f"Virhe: {e}")
                with r2:
                    if st.button("Peruuta", use_container_width=True):
                        st.session_state[rk] = False
                        st.rerun()

    elif admin_tab == "Tulevan kisan asetukset":
        st.info("Tänne lisätään seuraavan kisan asetukset myöhemmin.")
        st.markdown("---")
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
                    st.success("✅ Tyhjennetty!")
                    st.rerun()
            with cc2:
                if st.button("Peruuta"):
                    st.session_state[ck] = False
                    st.rerun()