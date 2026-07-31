import streamlit as st
import pandas as pd
import json
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta
import bcrypt

st.set_page_config(
    page_title="Haamuhanska",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== SALASANAT (älä jätä oletusarvoja tuotantoon) ======================
def get_secret(key, env_key, default):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(env_key, default)

SITE_PASSWORD = get_secret("site_password", "SITE_PASSWORD", "kisa2026")
ADMIN_PASSWORD = get_secret("admin_password", "ADMIN_PASSWORD", "admin123")

# ====================== GLOBAALI TYYLITTELY ======================
st.markdown("""
<style>
    /* Pääsivun tausta – sama kaikilla sivuilla */
    .stApp {
        background-color: #0a0f1c !important;
        background-image: none !important;
    }

    /* Sivupalkki */
    section[data-testid="stSidebar"] {
        background-image: url("https://i.imgur.com/gvrq6iO.jpeg") !important;
        background-size: contain !important;
        background-position: center bottom !important;
        background-repeat: no-repeat !important;
        background-color: #000000 !important;
        border-right: 1px solid #ffffff !important;
        padding-top: 0 !important;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 0 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0.3rem !important;
        padding-bottom: 0.5rem !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.3rem !important;
        padding-bottom: 0.5rem !important;
    }

    .stTabs [data-testid="stTabList"] {
        position: relative;
    }
    .stTabs [data-testid="stTabList"]::after {
        content: "";
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100% !important;
        height: 3px;
        background: linear-gradient(to right, transparent, #ffffff, transparent);
        z-index: 1;
    }

    .stTextInput, .stButton {
        max-width: 340px !important;
        margin: 0 auto !important;
    }

    section[data-testid="stSidebar"] .stRadio > div {
        background-color: rgba(13, 19, 33, 0.85) !important;
        border: 1px solid #ffffff !important;
        border-radius: 18px !important;
        padding: 17px !important;
    }

    section[data-testid="stSidebar"] .stAlert {
        background-color: rgba(13, 19, 33, 0.85) !important;
        border: 1px solid #ffffff !important;
        border-radius: 18px !important;
        color: #00ff9d !important;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid #ffffff !important;
        border-radius: 18px !important;
        background-color: rgba(13, 19, 33, 0.85) !important;
        margin-bottom: 8px !important;
        width: 100% !important;
        max-width: 100% !important;
    }

    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #ffffff !important;
        border: none !important;
    }

    section[data-testid="stSidebar"] .streamlit-expanderContent {
        background-color: transparent !important;
        border: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background-color: rgba(13, 19, 33, 0.85) !important;
        border: 1px solid #ffffff !important;
        border-radius: 18px !important;
        color: #ffffff !important;
        margin-top: 0 !important;
        margin-bottom: 18px !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1a253a !important;
        border-color: #ffffff !important;
        color: #ffffff !important;
    }  

    section[data-testid="stSidebar"] .stTextInput > div > div {
        border: 1px solid #ffffff !important;
        border-radius: 18px !important;
    }
    section[data-testid="stSidebar"] .stTextInput > div > div:focus-within {
        border: 1px solid #ffffff !important;
        box-shadow: 0 0 0 1px #ffffff !important;
    }
    section[data-testid="stSidebar"] .stRadio,
    section[data-testid="stSidebar"] .stRadio > div {
        width: 108% !important;
        max-width: 108% !important;
    }
</style>
""", unsafe_allow_html=True)

# ====================== SQLITE TIETOKANTA ======================
DB_FILE = "veikkaus.db"

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
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# ====================== APUFUNKTIOT ======================
def hash_password(password: str) -> str:
    """Hashaa salasana bcryptillä (sisältää suolan)."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    """Tarkista salasana. Tukee sekä bcryptiä että vanhaa SHA-256:ta."""
    if not hashed:
        return False
    try:
        # bcrypt-hashit alkavat yleensä $2a$, $2b$ tai $2y$
        if hashed.startswith("$2"):
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        # Legacy SHA-256 (vanhat käyttäjät)
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed
    except Exception:
        return False

def load_json(filename, default=None):
    if default is None:
        default = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_prediction(username, match_id, prediction_dict, is_special=0):
    conn = get_db_connection()
    c = conn.cursor()
    pred_json = json.dumps(prediction_dict, ensure_ascii=False)
    c.execute("""
        INSERT OR REPLACE INTO predictions (username, match_id, prediction, is_special, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (username, str(match_id), pred_json, is_special, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_prediction(username, match_id, is_special=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT prediction FROM predictions 
        WHERE username = ? AND match_id = ? AND is_special = ?
    """, (username, str(match_id), is_special))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row["prediction"])
    return None

def load_all_user_predictions(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT match_id, prediction, is_special FROM predictions WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        key = row["match_id"] if row["is_special"] == 0 else f"special_{row['match_id']}"
        result[key] = json.loads(row["prediction"])
    return result

def save_real_result(result_type, result_id, result_dict):
    conn = get_db_connection()
    c = conn.cursor()
    result_json = json.dumps(result_dict, ensure_ascii=False)
    c.execute("""
        INSERT OR REPLACE INTO real_results (result_type, id, result, updated_at)
        VALUES (?, ?, ?, ?)
    """, (result_type, str(result_id), result_json, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_real_result(result_type, result_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT result FROM real_results 
        WHERE result_type = ? AND id = ?
    """, (result_type, str(result_id)))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row["result"])
    return None

def load_all_predictions_for_match(match_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT username, prediction FROM predictions 
        WHERE match_id = ? AND is_special = 0
    """, (str(match_id),))
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row["username"]] = json.loads(row["prediction"])
    return result

def count_predictions_for_match(match_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as cnt FROM predictions
        WHERE match_id = ? AND is_special = 0
    """, (str(match_id),))
    row = c.fetchone()
    conn.close()
    return row["cnt"] if row else 0

def delete_real_result(result_type, result_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM real_results WHERE result_type = ? AND id = ?",
              (result_type, str(result_id)))
    conn.commit()
    conn.close()

def add_point_adjustment(username, points, reason, created_by):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO point_adjustments (username, points, reason, created_at, created_by)
        VALUES (?, ?, ?, ?, ?)
    """, (username, int(points), reason or "", datetime.now().isoformat(), created_by))
    conn.commit()
    conn.close()

def get_adjustment_total(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(points), 0) as total FROM point_adjustments WHERE username = ?",
              (username,))
    row = c.fetchone()
    conn.close()
    return row["total"] if row else 0

def get_user_adjustments(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, points, reason, created_at, created_by
        FROM point_adjustments
        WHERE username = ?
        ORDER BY created_at DESC
    """, (username,))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_point_adjustment(adj_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM point_adjustments WHERE id = ?", (adj_id,))
    conn.commit()
    conn.close()

def get_1x2(home, away):
    if home > away: return "1"
    if home < away: return "2"
    return "X"

def calculate_match_points(pred, real, double=False):
    if not pred or not real:
        return 0

    # ----- NHL-moniveto -----
    if "mark" in pred:
        pts = 0
        rh = real.get("home_goals")
        ra = real.get("away_goals")

        if rh is None or ra is None:
            return 0

        # Moniveto: 8 p jos tarkka yhdistelmä osuu
        home_opts = pred.get("home_opts", [])
        away_opts = pred.get("away_opts", [])
        if rh in home_opts and ra in away_opts:
            pts += 8

        # 1X2: 3 p
        real_mark = get_1x2(rh, ra)
        if pred.get("mark") == real_mark:
            pts += 3

        if double:
            pts *= 2
        return pts

    # ----- Normaali veikkaus (muut listat) -----
    ph = pred.get("home_goals")
    pa = pred.get("away_goals")
    rh = real.get("home_goals")
    ra = real.get("away_goals")

    if ph is None or pa is None or rh is None or ra is None:
        return 0

    pred_res = get_1x2(ph, pa)
    real_res = get_1x2(rh, ra)

    if pred_res != real_res:
        return 0

    if ph == rh and pa == ra:
        pts = 10
    elif (ph == rh and abs(pa - ra) == 1) or (pa == ra and abs(ph - rh) == 1):
        pts = 7
    elif (ph == rh) or (pa == ra) or (pred_res == "X"):
        pts = 6
    else:
        pts = 4

    if double:
        pts *= 2
    return pts

# ====================== LISTAT ======================
LIIGA_MATCHES = [
    {"id": "l1_1", "home": "KalPa", "away": "HPK", "aika": "Ti 15.9. 18:30", "start": datetime(2026, 9, 15, 18, 30), "double": False},
    {"id": "l1_2", "home": "Pelicans", "away": "Tappara", "aika": "Ti 15.9. 18:30", "start": datetime(2026, 9, 15, 18, 30), "double": False},
    {"id": "l1_3", "home": "SaiPa", "away": "K-Espoo", "aika": "Ti 15.9. 18:30", "start": datetime(2026, 9, 15, 18, 30), "double": False},
    {"id": "l1_4", "home": "TPS", "away": "Jukurit", "aika": "Ti 15.9. 18:30", "start": datetime(2026, 9, 15, 18, 30), "double": False},
    {"id": "l1_5", "home": "Ässät", "away": "Sport", "aika": "Ti 15.9. 18:30", "start": datetime(2026, 9, 15, 18, 30), "double": False},
    {"id": "l1_6", "home": "HIFK", "away": "Jukurit", "aika": "Ke 16.9. 18:30", "start": datetime(2026, 9, 16, 18, 30), "double": False},
    {"id": "l1_7", "home": "KooKoo", "away": "JYP", "aika": "Ke 16.9. 18:30", "start": datetime(2026, 9, 16, 18, 30), "double": False},
    {"id": "l1_8", "home": "Kärpät", "away": "Ilves", "aika": "Ke 16.9. 18:30", "start": datetime(2026, 9, 16, 18, 30), "double": True},
    {"id": "l1_9", "home": "Jokerit", "away": "JYP", "aika": "To 17.9. 18:30", "start": datetime(2026, 9, 17, 18, 30), "double": False},
    {"id": "l1_10", "home": "Lukko", "away": "Sport", "aika": "To 17.9. 18:30", "start": datetime(2026, 9, 17, 18, 30), "double": False},
    {"id": "l1_11", "home": "TPS", "away": "Tappara", "aika": "To 17.9. 18:30", "start": datetime(2026, 9, 17, 18, 30), "double": False},
    {"id": "l1_12", "home": "Jukurit", "away": "Pelicans", "aika": "Pe 18.9. 18:30", "start": datetime(2026, 9, 18, 18, 30), "double": False},
    {"id": "l1_13", "home": "KalPa", "away": "Ilves", "aika": "Pe 18.9. 18:30", "start": datetime(2026, 9, 18, 18, 30), "double": False},
    {"id": "l1_14", "home": "KooKoo", "away": "SaiPa", "aika": "Pe 18.9. 19:30", "start": datetime(2026, 9, 18, 19, 30), "double": False},
]

VALIOLIIGA_MATCHES = [
    {"id": "l2_1", "home": "Brentford", "away": "Chelsea", "aika": "Pe 18.9. 22:00", "start": datetime(2026, 9, 18, 22, 0), "double": False},
    {"id": "l2_2", "home": "Spurs", "away": "Aston Villa", "aika": "La 19.9. 14:30", "start": datetime(2026, 9, 19, 14, 30), "double": True},
    {"id": "l2_3", "home": "Brighton", "away": "Arsenal", "aika": "La 19.9. 17:00", "start": datetime(2026, 9, 19, 17, 0), "double": False},
    {"id": "l2_4", "home": "Everton", "away": "Ipswich", "aika": "La 19.9. 17:00", "start": datetime(2026, 9, 19, 17, 0), "double": False},
    {"id": "l2_5", "home": "Leeds", "away": "Crystal Palace", "aika": "La 19.9. 17:00", "start": datetime(2026, 9, 19, 17, 0), "double": False},
    {"id": "l2_6", "home": "Man City", "away": "Sunderland", "aika": "La 19.9. 17:00", "start": datetime(2026, 9, 19, 17, 0), "double": False},
    {"id": "l2_7", "home": "Newcastle", "away": "Hull City", "aika": "La 19.9. 17:00", "start": datetime(2026, 9, 19, 17, 0), "double": False},
    {"id": "l2_8", "home": "Nott'm Forest", "away": "Coventry", "aika": "La 19.9. 19:30", "start": datetime(2026, 9, 19, 19, 30), "double": False},
    {"id": "l2_9", "home": "Bournemouth", "away": "Liverpool", "aika": "Su 20.9. 16:00", "start": datetime(2026, 9, 20, 16, 0), "double": False},
    {"id": "l2_10", "home": "Fulham", "away": "Man Utd", "aika": "Su 20.9. 18:30", "start": datetime(2026, 9, 20, 18, 30), "double": False},
]

EURO_MATCHES = [
    {"id": "l3_1", "home": "Bayern", "away": "Union Berlin", "aika": "Pe 18.9. 21:30", "start": datetime(2026, 9, 18, 21, 30), "double": False},
    {"id": "l3_2", "home": "Roma", "away": "Inter", "aika": "La 19.9. 19:00", "start": datetime(2026, 9, 19, 19, 0), "double": False},
    {"id": "l3_3", "home": "Celtic", "away": "Rangers", "aika": "Su 20.9. 14:00", "start": datetime(2026, 9, 20, 14, 0), "double": False},
    {"id": "l3_4", "home": "Leverkusen", "away": "RB Leipzig", "aika": "Su 20.9. 16:30", "start": datetime(2026, 9, 20, 16, 30), "double": False},
    {"id": "l3_5", "home": "PSV", "away": "Twente", "aika": "Su 20.9. 17:45", "start": datetime(2026, 9, 20, 17, 45), "double": False},
    {"id": "l3_6", "home": "Porto", "away": "Benfica", "aika": "Su 20.9. 18:00", "start": datetime(2026, 9, 20, 18, 0), "double": False},
    {"id": "l3_7", "home": "Juventus", "away": "Atalanta", "aika": "Su 20.9. 19:00", "start": datetime(2026, 9, 20, 19, 0), "double": False},
    {"id": "l3_8", "home": "Marseille", "away": "PSG", "aika": "Su 20.9. 21:45", "start": datetime(2026, 9, 20, 21, 45), "double": False},
    {"id": "l3_9", "home": "Atlético", "away": "Real Madrid", "aika": "Su 20.9. 22:00", "start": datetime(2026, 9, 20, 22, 0), "double": True},
    {"id": "l3_10", "home": "Sevilla", "away": "Barcelona", "aika": "Su 20.9. 22:00", "start": datetime(2026, 9, 20, 22, 0), "double": False},
]

NATIONS_MATCHES = [
    {"id": "l4_1", "home": "Alankomaat", "away": "Saksa", "aika": "To 24.9. 21:45", "start": datetime(2026, 9, 24, 21, 45), "double": False},
    {"id": "l4_2", "home": "Norja", "away": "Tanska", "aika": "To 24.9. 21:45", "start": datetime(2026, 9, 24, 21, 45), "double": False},
    {"id": "l4_3", "home": "Portugali", "away": "Wales", "aika": "To 24.9. 21:45", "start": datetime(2026, 9, 24, 21, 45), "double": False},
    {"id": "l4_4", "home": "Italia", "away": "Belgia", "aika": "Pe 25.9. 21:45", "start": datetime(2026, 9, 25, 21, 45), "double": False},
    {"id": "l4_5", "home": "Turkki", "away": "Ranska", "aika": "Pe 25.9. 21:45", "start": datetime(2026, 9, 25, 21, 45), "double": False},
    {"id": "l4_6", "home": "San Marino", "away": "Suomi", "aika": "La 26.9. 19:00", "start": datetime(2026, 9, 26, 19, 0), "double": True},
    {"id": "l4_7", "home": "Englanti", "away": "Espanja", "aika": "La 26.9. 21:45", "start": datetime(2026, 9, 26, 21, 45), "double": False},
    {"id": "l4_8", "home": "Norja", "away": "Portugali", "aika": "Su 27.9. 21:45", "start": datetime(2026, 9, 27, 21, 45), "double": False},
    {"id": "l4_9", "home": "Saksa", "away": "Kreikka", "aika": "Su 27.9. 21:45", "start": datetime(2026, 9, 27, 21, 45), "double": False},
    {"id": "l4_10", "home": "Belgia", "away": "Ranska", "aika": "Ma 28.9. 21:45", "start": datetime(2026, 9, 28, 21, 45), "double": False},
]

NHL_MATCHES = [
    {"id": "l5_1", "home": "Florida", "away": "Carolina", "aika": "Ti 29.9. 00:00", "start": datetime(2026, 9, 29, 0, 0), "double": True},
    {"id": "l5_2", "home": "Toronto", "away": "Montreal", "aika": "Ti 29.9. 02:00", "start": datetime(2026, 9, 29, 2, 0), "double": False},
    {"id": "l5_3", "home": "Boston", "away": "NY Rangers", "aika": "Ti 29.9. 03:00", "start": datetime(2026, 9, 29, 3, 0), "double": False},
    {"id": "l5_4", "home": "Edmonton", "away": "Vancouver", "aika": "Ti 29.9. 05:00", "start": datetime(2026, 9, 29, 5, 0), "double": False},
    {"id": "l5_5", "home": "Vegas", "away": "Chicago", "aika": "Ti 29.9. 05:30", "start": datetime(2026, 9, 29, 5, 30), "double": False},
    {"id": "l5_6", "home": "Philadelphia", "away": "Pittsburgh", "aika": "Ke 30.9. 02:30", "start": datetime(2026, 9, 30, 2, 30), "double": False},
    {"id": "l5_7", "home": "Toronto", "away": "NY Islanders", "aika": "Ke 30.9. 02:30", "start": datetime(2026, 9, 30, 2, 30), "double": False},
    {"id": "l5_8", "home": "Colorado", "away": "LA Kings", "aika": "Ke 30.9. 05:00", "start": datetime(2026, 9, 30, 5, 0), "double": False},
    {"id": "l5_9", "home": "New Jersey", "away": "Philadelphia", "aika": "To 1.10. 02:00", "start": datetime(2026, 10, 1, 2, 0), "double": False},
    {"id": "l5_10", "home": "NY Rangers", "away": "Tampa Bay", "aika": "To 1.10. 02:00", "start": datetime(2026, 10, 1, 2, 0), "double": False},
    {"id": "l5_11", "home": "Columbus", "away": "Buffalo", "aika": "To 1.10. 02:00", "start": datetime(2026, 10, 1, 2, 0), "double": False},
    {"id": "l5_12", "home": "Nashville", "away": "Minnesota", "aika": "To 1.10. 03:00", "start": datetime(2026, 10, 1, 3, 0), "double": False},
]

def calculate_match_points_only(username):
    total = 0
    for matches in [LIIGA_MATCHES, VALIOLIIGA_MATCHES, EURO_MATCHES, NATIONS_MATCHES, NHL_MATCHES]:
        for m in matches:
            pred = load_prediction(username, m["id"])
            real = load_real_result("match", m["id"])
            total += calculate_match_points(pred, real, double=m["double"])
    return total

def calculate_user_points(username):
    total = calculate_match_points_only(username)
    total += get_adjustment_total(username)
    return total

def get_user_rank(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [row["username"] for row in c.fetchall()]
    conn.close()

    if not users:
        return 1, 1

    standings = []
    for u in users:
        standings.append((u, calculate_user_points(u)))

    standings.sort(key=lambda x: (-x[1], x[0].lower()))

    total = len(standings)
    for i, (u, _) in enumerate(standings, start=1):
        if u == username:
            return i, total
    return total, total

# ====================== SIVUPALKKI ======================
if "site_access" not in st.session_state:
    st.session_state.site_access = False

if "page" not in st.session_state:
    st.session_state.page = "Etusivu"

if not st.session_state.get("logged_in_user"):
    st.sidebar.markdown("<div style='height: 75px;'></div>", unsafe_allow_html=True)

    with st.sidebar.expander("KIRJAUDU SISÄÄN", expanded=False):
        username = st.text_input("Käyttäjänimi", key="login_user")
        password = st.text_input("Salasana", type="password", key="login_pass")

        if st.button("Kirjaudu sisään", type="primary", use_container_width=True):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            conn.close()

            if row and check_password(password, row["password_hash"]):
                # Migroi vanha SHA-256-hash bcryptiin automaattisesti
                if not row["password_hash"].startswith("$2"):
                    conn2 = get_db_connection()
                    c2 = conn2.cursor()
                    c2.execute(
                        "UPDATE users SET password_hash = ? WHERE username = ?",
                        (hash_password(password), username)
                    )
                    conn2.commit()
                    conn2.close()

                st.session_state.logged_in_user = username
                st.session_state.site_access = False
                st.rerun()
            else:
                st.error("Väärä käyttäjänimi tai salasana")

    with st.sidebar.expander("VAIHDA SALASANA", expanded=False):
        pw_user = st.text_input("Käyttäjänimi", key="pwchange_user")
        pw_current = st.text_input("Nykyinen salasana", type="password", key="pwchange_current")
        pw_new = st.text_input("Uusi salasana", type="password", key="pwchange_new")
        pw_new2 = st.text_input("Toista uusi salasana", type="password", key="pwchange_new2")

        if st.button("Tallenna uusi salasana", type="primary", use_container_width=True, key="pwchange_save"):
            if not pw_user or not pw_current or not pw_new:
                st.error("Täytä kaikki kentät")
            elif pw_new != pw_new2:
                st.error("Uudet salasanat eivät täsmää")
            elif len(pw_new) < 6:
                st.error("Uuden salasanan tulee olla vähintään 6 merkkiä")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT password_hash FROM users WHERE username = ?", (pw_user,))
                row = c.fetchone()

                if row and check_password(pw_current, row["password_hash"]):
                    c.execute(
                        "UPDATE users SET password_hash = ? WHERE username = ?",
                        (hash_password(pw_new), pw_user)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Salasana vaihdettu onnistuneesti!")
                else:
                    conn.close()
                    st.error("Väärä käyttäjänimi tai nykyinen salasana")

    with st.sidebar.expander("LUO UUSI TILI", expanded=False):
        new_user = st.text_input("Käyttäjänimi", key="reg_user")
        new_pass = st.text_input("Salasana", type="password", key="reg_pass")
        new_pass2 = st.text_input("Toista salasana", type="password", key="reg_pass2")

        if st.button("Rekisteröidy", type="primary", use_container_width=True):
            if not new_user or not new_pass:
                st.error("Käyttäjänimi ja salasana pakollisia")
            elif new_pass != new_pass2:
                st.error("Salasanat eivät täsmää")
            elif len(new_pass) < 6:
                st.error("Salasanan tulee olla vähintään 6 merkkiä")
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT username FROM users WHERE username = ?", (new_user,))
                if c.fetchone():
                    st.error("Käyttäjänimi on jo käytössä")
                else:
                    c.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (new_user, hash_password(new_pass))
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Tili luotu onnistuneesti!")
                    st.info("Voit nyt kirjautua sisään.")

    page = "Etusivu"

else:
    st.sidebar.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    if not st.session_state.get("site_access"):
        st.sidebar.markdown("###")
        st.sidebar.caption("  Veikkauskisan salasanalla sisään...!  ")
        site_pw = st.sidebar.text_input("", type="password", key="site_pw")

        if st.sidebar.button("Avaa veikkauskisa", type="primary", use_container_width=True):
            if site_pw == SITE_PASSWORD:
                st.session_state.site_access = True
                st.success("Sivusto avattu!")
                st.rerun()
            else:
                st.sidebar.error("Väärä kutsusalasana")

        page = "Etusivu"

    else:
        menu_options = ["Etusivu", "Kisainfo", "VEIKKAUSKISA", "Veikkaustilanne", "Omat veikkaukset", "Kaikkien veikkaukset", "Hall Of Fame"]

        if st.session_state.page == "Admin":
            page = "Admin"
            st.sidebar.info("Olet Admin-paneelissa")
            if st.sidebar.button("← Palaa valikkoon", use_container_width=True):
                st.session_state.page = "Etusivu"
                st.rerun()
        else:
            if st.session_state.page not in menu_options:
                st.session_state.page = "Etusivu"

            selected = st.sidebar.radio(
                "",
                menu_options,
                index=menu_options.index(st.session_state.page),
                key="menu_radio"
            )

            if selected != st.session_state.page:
                st.session_state.page = selected
                st.rerun()

            page = selected

        rank, total = get_user_rank(st.session_state.logged_in_user)
        uname = st.session_state.logged_in_user

        st.sidebar.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: rgba(13, 19, 33, 0.85);
            border: 1px solid #ffffff;
            border-radius: 18px;
            padding: 10px 14px;
            margin-bottom: 6px;
            gap: 10px;
        ">
            <span style="
                color: #ffffff;
                font-weight: 600;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                min-width: 0;
            ">👤 {uname}</span>
            <span style="
                color: #00ff9d;
                font-weight: 700;
                flex-shrink: 0;
                white-space: nowrap;
            ">{rank}/{total}</span>
        </div>
        """, unsafe_allow_html=True)

        pad_l, pad_mid, pad_r = st.sidebar.columns([0.9, 9, 0.9])
        with pad_mid:
            if st.button("Kirjaudu ulos", use_container_width=True, key="logout_btn"):
                st.session_state.logged_in_user = None
                st.session_state.site_access = False
                st.session_state.is_admin = False
                st.session_state.page = "Etusivu"
                st.rerun()
        
        with st.sidebar.expander("Admin"):
            if not st.session_state.get("is_admin", False):
                pw = st.text_input("Admin-salasana", type="password", key="admin_pw_sidebar")
                if st.button("Kirjaudu adminiksi", use_container_width=True):
                    if pw == ADMIN_PASSWORD:
                        st.session_state.is_admin = True
                        st.success("Admin-oikeudet myönnetty")
                        st.rerun()
                    else:
                        st.error("Väärä salasana")
            else:
                st.success("Olet admin-tilassa")
                if st.button("Siirry Admin-paneeliin", type="primary", use_container_width=True):
                    st.session_state.page = "Admin"
                    st.rerun()

# ====================== ETUSIVU ======================
if page == "Etusivu":
    st.markdown("""
    <div style="
        height: 20vh;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: center;
        text-align: center;
        padding-bottom: 0;
    ">
        <h1 style="
            font-family: 'Cinzel', serif;
            font-size: 3.2rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 3px;
            text-shadow: 
                0 0 10px rgba(255,255,255,0.8),
                0 0 20px rgba(255,255,255,0.5),
                0 0 40px rgba(0,255,200,0.4),
                0 0 80px rgba(0,200,255,0.2);
            margin: 0;
            white-space: nowrap;
        ">
            Haamuhanskan veikkauskisoja
        </h1>
    </div>

    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# ====================== HALL OF FAME ======================
if page == "Hall Of Fame":
    st.title("Hall of Fame")
    st.caption("Haamuhanskan veikkauskisojen kärkikolmikot ")
    

    # ----- Menneet kisat -----
    PAST_CONTESTS = [
        {
            "name": "MM26 -testikisa",
            "date": "Kesä 2026",
            "participants": 18,
            "standings": [
                {"nimi": "Markus", "pisteet": 386},
                {"nimi": "Tommi", "pisteet": 354},
                {"nimi": "Tekoäly", "pisteet": 346},
            ]
        },
        # Lisää uusia menneitä kisoja tähän
    ]

    # Tabit: ensin nykyinen kisa, sitten menneet
    tab_names = ["Syyskuun palloilupaketti"] + [c["name"] for c in PAST_CONTESTS]
    tabs = st.tabs(tab_names)

    # ---------- 1. TAB: KÄYNNISSÄ OLEVA KISA ----------
    with tabs[0]:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username FROM users")
        users = [row["username"] for row in c.fetchall()]
        conn.close()

        if not users:
            st.info("Ei vielä pelaajia.")
        else:
            standings = []
            for u in users:
                standings.append({
                    "nimi": u,
                    "pisteet": calculate_user_points(u)
                })
            standings.sort(key=lambda x: x["pisteet"], reverse=True)
            top3 = standings[:3]

            medals = ["🥇", "🥈", "🥉"]
            colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
            bg_colors = ["rgba(255, 215, 0, 0.12)", "rgba(192, 192, 192, 0.10)", "rgba(205, 127, 50, 0.10)"]

            for i, entry in enumerate(top3):
                st.markdown(f"""
                <div style="
                    background: {bg_colors[i]};
                    border: 1px solid {colors[i]};
                    border-radius: 14px;
                    padding: 16px 20px;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    max-width: 480px;
                ">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <span style="font-size: 1.8rem;">{medals[i]}</span>
                        <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">
                            {entry['nimi']}
                        </div>
                    </div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #00ff9d;">
                        {entry['pisteet']} p
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ---------- MENNEET KISAT (sama tyylittely) ----------
    for idx, contest in enumerate(PAST_CONTESTS):
        with tabs[idx + 1]:
            medals = ["🥇", "🥈", "🥉"]
            colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
            bg_colors = ["rgba(255, 215, 0, 0.12)", "rgba(192, 192, 192, 0.10)", "rgba(205, 127, 50, 0.10)"]

            for i, entry in enumerate(contest["standings"]):
                st.markdown(f"""
                <div style="
                    background: {bg_colors[i]};
                    border: 1px solid {colors[i]};
                    border-radius: 14px;
                    padding: 16px 20px;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    max-width: 480px;
                ">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <span style="font-size: 1.8rem;">{medals[i]}</span>
                        <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">
                            {entry['nimi']}
                        </div>
                    </div>
                    <div style="font-size: 1.4rem; font-weight: 700; color: #00ff9d;">
                        {entry['pisteet']} p
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ====================== VEIKKAUSKISA ======================
if page == "VEIKKAUSKISA":
    st.title("Veikkauskisa - Syyskuun palloilupaketti")
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_match_list(matches, prefix):
        now = datetime.now()
        for m in matches:
            if now >= m["start"]:
                continue

            time_left = m["start"] - now
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            countdown = f"{days} pv {hours:02d}:{minutes:02d}" if days > 0 else f"{hours:02d}:{minutes:02d}"

            saved = load_prediction(st.session_state.logged_in_user, m["id"])

            double_txt = " 🔥 TUPLAPISTEET" if m["double"] else ""
            st.markdown(f"### {m['home']} – {m['away']}{double_txt}")
            st.markdown(
                f"<p style='font-size:1.05rem; color:#aaaaaa; margin-top:-8px;'>"
                f"{m['aika']} &nbsp;|&nbsp; Aikaa jäljellä: <b style='color:#00ff9d;'>{countdown}</b></p>",
                unsafe_allow_html=True
            )

            col1, col2, col3, col4 = st.columns([0.5, 0.5, 1, 3])
            with col1:
                default_h = saved["home_goals"] if saved and "home_goals" in saved else 0
                home_g = st.selectbox(f"{m['home']}", list(range(0, 13)), index=default_h, key=f"{prefix}_{m['id']}_h")
            with col2:
                default_a = saved["away_goals"] if saved and "away_goals" in saved else 0
                away_g = st.selectbox(f"{m['away']}", list(range(0, 13)), index=default_a, key=f"{prefix}_{m['id']}_a")
            with col3:
                if saved and "home_goals" in saved:
                    st.markdown(f"""
                    <div style="background-color:#1e2a44; padding:12px 16px; border-radius:8px; 
                                border:1px solid #00ff9d; font-size:1.40rem; min-height:90px; 
                                display:flex; align-items:center;">
                        <b>Tallennettu:</b>&nbsp; {saved['home_goals']}–{saved['away_goals']}
                    </div>
                    """, unsafe_allow_html=True)

            btn_label = "Päivitä veikkaus" if saved and "home_goals" in saved else "Tallenna veikkaus"
            if st.button(btn_label, type="primary" if not (saved and "home_goals" in saved) else "secondary", key=f"{prefix}_save_{m['id']}"):
                pred = {"home_goals": home_g, "away_goals": away_g}
                save_prediction(st.session_state.logged_in_user, m["id"], pred)
                st.success("Veikkaus tallennettu!")
                st.rerun()

            st.divider()

    def render_nhl_list(matches):
        now = datetime.now()
        for m in matches:
            if now >= m["start"]:
                continue

            time_left = m["start"] - now
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            countdown = f"{days} pv {hours:02d}:{minutes:02d}" if days > 0 else f"{hours:02d}:{minutes:02d}"

            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has_saved = saved and "mark" in saved

            double_txt = " 🔥 TUPLAPISTEET" if m["double"] else ""
            st.markdown(f"### {m['home']} – {m['away']}{double_txt}")
            st.markdown(
                f"<p style='font-size:1.05rem; color:#aaaaaa; margin-top:-8px;'>"
                f"{m['aika']} &nbsp;|&nbsp; Aikaa jäljellä: <b style='color:#00ff9d;'>{countdown}</b></p>",
                unsafe_allow_html=True
            )

            # ========== 1X2 ==========
            default_mark = saved.get("mark", "X") if saved else "X"
            mark = st.radio(
                "Merkki",
                ["1", "X", "2"],
                index=["1", "X", "2"].index(default_mark) if default_mark in ["1", "X", "2"] else 1,
                horizontal=True,
                key=f"nhl_mark_{m['id']}",
                label_visibility="collapsed"
            )

            btn_label_1x2 = "Päivitä veikkaus" if has_saved else "Tallenna veikkaus"
            if st.button(btn_label_1x2, type="primary" if not has_saved else "secondary", key=f"nhl_save_mark_{m['id']}"):
                pred = {
                    "mark": mark,
                    "split": saved.get("split", "2-2") if saved else "2-2",
                    "home_opts": saved.get("home_opts", []) if saved else [],
                    "away_opts": saved.get("away_opts", []) if saved else []
                }
                save_prediction(st.session_state.logged_in_user, m["id"], pred)
                st.success("1X2 tallennettu!")
                st.rerun()

            # Pieni väli
            st.markdown("")
            st.markdown("")

            # ========== MONIVETO ==========
            st.markdown("**MONIVETO** – Päätä ensin haluatko asettaa toiselle joukkueelle kolme maalia vai molemmille kaksi")

            default_split = saved.get("split", "2-2") if saved else "2-2"
            split = st.radio(
                "Jakotapa",
                ["3-1", "2-2", "1-3"],
                index=["3-1", "2-2", "1-3"].index(default_split) if default_split in ["3-1", "2-2", "1-3"] else 1,
                horizontal=True,
                key=f"nhl_split_{m['id']}",
                label_visibility="collapsed"
            )

            home_count = int(split.split("-")[0])
            away_count = int(split.split("-")[1])

            # Valikot allekkain + kavennettu leveys
            col_h, col_a = st.columns(2)

            with col_h:
                st.markdown(f"**{m['home']}**")
                home_opts = []
                default_home = saved.get("home_opts", [0] * home_count) if saved else [0] * home_count
                for i in range(home_count):
                    c1, _ = st.columns([1, 3])
                    with c1:
                        val = st.selectbox(
                            f"Vaihtoehto {i+1}",
                            list(range(0, 13)),
                            index=default_home[i] if i < len(default_home) else 0,
                            key=f"nhl_h_{m['id']}_{i}"
                        )
                    home_opts.append(val)

            with col_a:
                st.markdown(f"**{m['away']}**")
                away_opts = []
                default_away = saved.get("away_opts", [0] * away_count) if saved else [0] * away_count
                for i in range(away_count):
                    c1, _ = st.columns([1, 3])
                    with c1:
                        val = st.selectbox(
                            f"Vaihtoehto {i+1}",
                            list(range(0, 13)),
                            index=default_away[i] if i < len(default_away) else 0,
                            key=f"nhl_a_{m['id']}_{i}"
                        )
                    away_opts.append(val)

            btn_label_multi = "Päivitä veikkaus" if has_saved else "Tallenna veikkaus"
            if st.button(btn_label_multi, type="primary" if not has_saved else "secondary", key=f"nhl_save_multi_{m['id']}"):
                home_opts_clean = sorted(list(set(home_opts)))
                away_opts_clean = sorted(list(set(away_opts)))

                if len(home_opts_clean) != home_count or len(away_opts_clean) != away_count:
                    st.error("Valitse eri maalimäärät (ei samoja numeroita)")
                else:
                    pred = {
                        "mark": mark,
                        "split": split,
                        "home_opts": home_opts_clean,
                        "away_opts": away_opts_clean
                    }
                    save_prediction(st.session_state.logged_in_user, m["id"], pred)
                    st.success("Moniveto tallennettu!")
                    st.rerun()

            # Tallennettu-laatikko
            if has_saved:
                saved_combos = [f"{h}–{a}" for h in saved.get("home_opts", []) for a in saved.get("away_opts", [])]
                st.markdown(f"""
                <div style="background-color:#1e2a44; padding:12px 16px; border-radius:8px; 
                            border:1px solid #00ff9d; font-size:1.1rem; margin-top:12px; max-width: 420px;">
                    <b>Tallennettu:</b><br>
                    1X2: <b>{saved.get('mark')}</b><br>
                    Moniveto ({saved.get('split')}): {', '.join(saved_combos) if saved_combos else '–'}
                </div>
                """, unsafe_allow_html=True)

            st.divider()

    with tab1:
        render_match_list(LIIGA_MATCHES, "l1")
    with tab2:
        render_match_list(VALIOLIIGA_MATCHES, "l2")
    with tab3:
        render_match_list(EURO_MATCHES, "l3")
    with tab4:
        render_match_list(NATIONS_MATCHES, "l4")
    with tab5:
        render_nhl_list(NHL_MATCHES)

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.title("Syyskuun palloilupaketti")
    st.divider()

    col_rank, col_chat = st.columns([1, 1.4], gap="large")

    with col_rank:
        st.subheader("🏆 Veikkaustilanne")
        st.divider()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username FROM users ORDER BY username")
        users = [row["username"] for row in c.fetchall()]
        conn.close()

        if not users:
            st.info("Ei vielä yhtään rekisteröitynyttä pelaajaa.")
        else:
            standings = []
            for username in users:
                points = calculate_user_points(username)
                standings.append({
                    "nimi": username,
                    "pisteet": points
                })

            standings.sort(key=lambda x: x["pisteet"], reverse=True)

            for i, entry in enumerate(standings, start=1):
                is_me = entry["nimi"] == st.session_state.logged_in_user
                name = f"<b>{entry['nimi']}</b>" if is_me else entry["nimi"]

                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; 
                                max-width:100%; margin:2px 0; font-size:1.1rem;
                                background-color: rgba(30, 42, 68, 0.6);
                                padding: 6px 12px; border-radius: 8px;">
                        <span>{i}. {name}</span>
                        <span style="font-weight:600; color:#00ff9d;">{entry['pisteet']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with col_chat:
        st.subheader("📣 Sana on vapaa...!")
        st.divider()

        COMMENTS_FILE = "comments.json"
        comments = load_json(COMMENTS_FILE, default=[])

        # Kirjoituslaatikko ylhäällä
        if st.session_state.get("logged_in_user"):
            with st.form("comment_form", clear_on_submit=True):
                new_comment = st.text_area(
                    "Kirjoita kommentti...",
                    height=100,
                    placeholder="Anna palaa.... 🔥",
                    max_chars=600,
                    label_visibility="collapsed"
                )
                submitted = st.form_submit_button("💥 Julkaise", use_container_width=True)
                if submitted and new_comment.strip():
                    comments.append({
                        "user": st.session_state.logged_in_user,
                        "text": new_comment.strip(),
                        "time": datetime.now().strftime("%d.%m. %H:%M")
                    })
                    save_json(COMMENTS_FILE, comments)
                    st.session_state.comment_page = 1
                    st.success("Kommentti julkaistu!")
                    st.rerun()
        else:
            st.warning("Kirjaudu sisään kirjoittaaksesi kommentteja.")

        st.markdown("")

        comments_per_page = 5
        total_pages = max(1, (len(comments) + comments_per_page - 1) // comments_per_page)

        if "comment_page" not in st.session_state:
            st.session_state.comment_page = 1

        if st.session_state.comment_page > total_pages:
            st.session_state.comment_page = total_pages
        if st.session_state.comment_page < 1:
            st.session_state.comment_page = 1

        current_page = st.session_state.comment_page
        start_idx = (current_page - 1) * comments_per_page
        end_idx = start_idx + comments_per_page
        displayed_comments = list(reversed(comments))[start_idx:end_idx]

        if displayed_comments:
            for i, c in enumerate(displayed_comments):
                global_idx = len(comments) - 1 - (start_idx + i)
                is_own = c["user"] == st.session_state.get("logged_in_user")

                st.markdown(f"""
                    <div style="background-color: #1e2a44; padding: 14px 16px; border-radius: 12px; 
                                margin-bottom: 12px; border-left: 5px solid #00ff9d;">
                        <strong>{c['user']}</strong> 
                        <span style="color:#888; font-size:0.85rem;">{c['time']}</span><br>
                        {c['text']}
                    </div>
                """, unsafe_allow_html=True)

                if is_own:
                    if st.button("✏️ Muokkaa", key=f"edit_{global_idx}"):
                        st.session_state.editing_comment = global_idx
                        st.rerun()
        else:
            st.info("Ei vielä kommentteja. Ole ensimmäinen!")

        if total_pages > 1:
            c1, c2, c3 = st.columns([1, 1.2, 1])
            with c1:
                if st.button("← Edellinen", disabled=(current_page <= 1), use_container_width=True):
                    st.session_state.comment_page = current_page - 1
                    st.rerun()
            with c2:
                st.markdown(
                    f"<div style='text-align:center; padding-top:8px; color:#aaaaaa;'>"
                    f"Sivu {current_page} / {total_pages}</div>",
                    unsafe_allow_html=True
                )
            with c3:
                if st.button("Seuraava →", disabled=(current_page >= total_pages), use_container_width=True):
                    st.session_state.comment_page = current_page + 1
                    st.rerun()

        if st.session_state.get("editing_comment") is not None:
            idx = st.session_state.editing_comment
            if 0 <= idx < len(comments):
                old = comments[idx]
                st.write("**Muokkaa kommenttiasi:**")
                new_text = st.text_area("Kommentti", value=old["text"], height=100, key="edit_text")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Tallenna", type="primary", key="save_edit"):
                        if new_text.strip():
                            comments[idx]["text"] = new_text.strip()
                            comments[idx]["edited"] = datetime.now().strftime("%d.%m. %H:%M")
                            save_json(COMMENTS_FILE, comments)
                            st.success("Kommentti päivitetty!")
                            st.session_state.editing_comment = None
                            st.rerun()
                with c2:
                    if st.button("Peruuta", key="cancel_edit"):
                        st.session_state.editing_comment = None
                        st.rerun()

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    st.title("Omat veikkaukset")
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_own_list(matches, list_name):
        found_any = False
        total_points = 0

        for m in matches:
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            if not saved:
                continue

            found_any = True
            real = load_real_result("match", m["id"])
            points = calculate_match_points(saved, real, double=m["double"])
            total_points += points

            double_txt = " 🔥 TUPLAPISTEET" if m["double"] else ""

            if real:
                real_score = f"{real['home_goals']}–{real['away_goals']}"
                real_line = f"<b>Oikea tulos:</b> {real_score}<br>"
            else:
                real_line = "<b>Oikea tulos:</b> <span style='color:#888;'>ei vielä syötetty</span><br>"

            # NHL-muoto
            if "mark" in saved:
                combos = [f"{h}–{a}" for h in saved.get("home_opts", []) for a in saved.get("away_opts", [])]
                veikkaus_txt = f"1X2: <b>{saved.get('mark')}</b><br>Moniveto: {', '.join(combos)}"
            else:
                veikkaus_txt = f"<b>Veikkaus:</b> {saved.get('home_goals')}–{saved.get('away_goals')}"

            st.markdown(f"""
            <div style="background-color:#1e2a44; padding:14px 18px; border-radius:8px; 
                        border:1px solid #aaaaaa; margin-bottom:18px; max-width: 420px;">
                <b>{m['home']} – {m['away']}{double_txt}</b><br>
                <span style="color:#aaaaaa; font-size:0.9rem;">{m['aika']}</span><br><br>
                {veikkaus_txt}<br>
                {real_line}
                <b style="color:#00ff9d;">Pisteet: {points}</b>
            </div>
            """, unsafe_allow_html=True)

        if not found_any:
            st.info("Et ole vielä tallentanut yhtään veikkausta tälle listalle.")
        else:
            st.markdown(f"""
            <div style="background-color:#0d1321; padding:16px 20px; border-radius:10px; 
                        border:2px solid #00ff9d; max-width: 520px; margin-top: 10px;">
                <b style="font-size:1.2rem; color:#00ff9d;">Yhteensä {list_name}: {total_points} pistettä</b>
            </div>
            """, unsafe_allow_html=True)

    with tab1:
        render_own_list(LIIGA_MATCHES, "Lista 1")
    with tab2:
        render_own_list(VALIOLIIGA_MATCHES, "Lista 2")
    with tab3:
        render_own_list(EURO_MATCHES, "Lista 3")
    with tab4:
        render_own_list(NATIONS_MATCHES, "Lista 4")
    with tab5:
        render_own_list(NHL_MATCHES, "Lista 5")


# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.title("Kaikkien veikkaukset")
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Lista 1 - SM-liigan arkipelit",
        "Lista 2 - Valioliigakierros",
        "Lista 3 - Europelien helmiä",
        "Lista 4 - Kansojen liigan pelejä",
        "Lista 5 - NHL-Tusina"
    ])

    def render_all_predictions(matches, list_name):
        now = datetime.now()
        shown_any = False
        me = st.session_state.logged_in_user

        for m in matches:
            real = load_real_result("match", m["id"])
            is_closed = now >= m["start"] or real is not None

            if not is_closed:
                continue

            shown_any = True
            all_preds = load_all_predictions_for_match(m["id"])
            double_txt = " 🔥 TUPLAPISTEET" if m["double"] else ""

            if real:
                real_score = f"{real['home_goals']}–{real['away_goals']}"
                real_html = f"<b style='color:#00ff9d;'>Oikea tulos: {real_score}</b>"
            else:
                real_html = "<span style='color:#888;'>Tulos ei vielä syötetty</span>"

            st.markdown(f"""
            <div style="background-color:#1e2a44; padding:16px 18px; border-radius:10px;
                        border:1px solid #aaaaaa; margin-bottom:8px; max-width:420px;">
                <b style="font-size:1.15rem;">{m['home']} – {m['away']}{double_txt}</b><br>
                <span style="color:#aaaaaa; font-size:0.9rem;">{m['aika']}</span><br>
                {real_html}
            </div>
            """, unsafe_allow_html=True)

            if not all_preds:
                st.info("Ei vielä yhtään veikkausta tälle ottelulle.")
                st.markdown("<br>", unsafe_allow_html=True)
                continue

            rows = []
            for username, pred in all_preds.items():
                if "mark" in pred:  # NHL
                    combos = [f"{h}–{a}" for h in pred.get("home_opts", []) for a in pred.get("away_opts", [])]
                    score_str = f"1X2:{pred.get('mark')} | {', '.join(combos)}"
                else:
                    score_str = f"{pred.get('home_goals')}–{pred.get('away_goals')}"

                pts = calculate_match_points(pred, real, double=m["double"]) if real else None
                rows.append({
                    "username": username,
                    "score": score_str,
                    "points": pts if pts is not None else -1
                })

            if real:
                rows.sort(key=lambda x: (-x["points"], x["username"].lower()))
            else:
                rows.sort(key=lambda x: x["username"].lower())

            with st.expander(f"Veikkaukset ja pisteet ({len(rows)})", expanded=False):
                for i, row in enumerate(rows, start=1):
                    is_me = row["username"] == me
                    name = f"<b style='color:#00ff9d;'>{row['username']}</b>" if is_me else row["username"]

                    if real:
                        pts_html = f"<b style='color:#00ff9d;'>{row['points']} p</b>"
                    else:
                        pts_html = "<span style='color:#888;'>—</span>"

                    place = f"{i}." if real else ""

                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                                background-color:#0d1321; padding:8px 14px; border-radius:8px;
                                margin-bottom:6px; max-width:420px; border:1px solid #2a3548;">
                        <span style="color:#cccccc;">
                            <span style="color:#888; min-width:1.8rem; display:inline-block;">{place}</span>
                            {name}
                            <span style="color:#888;"> · </span>
                            {row['score']}
                        </span>
                        <span>{pts_html}</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

        if not shown_any:
            st.info(f"Ei vielä yhtään suljettua ottelua listalla {list_name}.")

    with tab1:
        render_all_predictions(LIIGA_MATCHES, "Lista 1")
    with tab2:
        render_all_predictions(VALIOLIIGA_MATCHES, "Lista 2")
    with tab3:
        render_all_predictions(EURO_MATCHES, "Lista 3")
    with tab4:
        render_all_predictions(NATIONS_MATCHES, "Lista 4")
    with tab5:
        render_all_predictions(NHL_MATCHES, "Lista 5")


# ====================== KISAINFON ======================
if page == "Kisainfo":
    st.title("Tervetuloa veikkaamaan!")
    st.info("Tähän tulee kisojen säännöt ja pistelaskujärjestelmä.")

# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")

    if not st.session_state.get("is_admin", False):
        pw = st.text_input("Syötä admin-salasana", type="password", key="admin_pw")
        if st.button("Kirjaudu adminiksi"):
            if pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("✅ Admin-oikeudet myönnetty")
                st.rerun()
            else:
                st.error("Väärä salasana")
        st.stop()

    st.success("✅ Olet admin-tilassa")

    admin_tab = st.radio(
        "Valitse toiminto",
        ["Käyttäjien hallinta", "Tulosten syöttö", "Pistekorjaukset",
         "Varmuuskopiointi & palautus", "Tulevan kisan asetukset"],
        horizontal=True
    )

    ALL_MATCH_LISTS = [
        ("Lista 1 – SM-Liiga", LIIGA_MATCHES),
        ("Lista 2 – Valioliiga", VALIOLIIGA_MATCHES),
        ("Lista 3 – Europelien helmiä", EURO_MATCHES),
        ("Lista 4 – Kansojen liiga", NATIONS_MATCHES),
        ("Lista 5 – NHL-Tusina", NHL_MATCHES),
    ]

    if admin_tab == "Käyttäjien hallinta":
        st.write("### 👥 Käyttäjien hallinta")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username, created_at FROM users ORDER BY username")
        all_users = c.fetchall()
        conn.close()

        if not all_users:
            st.info("Ei käyttäjiä.")
        else:
            for user in all_users:
                username = user["username"]
                created = user["created_at"][:10] if user["created_at"] else "-"
                match_pts = calculate_match_points_only(username)
                bonus = get_adjustment_total(username)
                total_pts = match_pts + bonus

                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    st.write(f"**{username}**")
                    st.caption(f"Luotu: {created} · Ottelupisteet: {match_pts} · Korjaukset: {bonus:+d} · Yhteensä: {total_pts}")

                with col2:
                    with st.popover("Nollaa salasana"):
                        new_pw = st.text_input("Uusi salasana", type="password", key=f"new_pw_{username}")
                        new_pw2 = st.text_input("Toista uusi salasana", type="password", key=f"new_pw2_{username}")
                        if st.button("Tallenna uusi salasana", key=f"save_pw_{username}"):
                            if not new_pw:
                                st.error("Salasana ei voi olla tyhjä")
                            elif new_pw != new_pw2:
                                st.error("Salasanat eivät täsmää")
                            elif len(new_pw) < 6:
                                st.error("Salasanan tulee olla vähintään 6 merkkiä")
                            else:
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute(
                                    "UPDATE users SET password_hash = ? WHERE username = ?",
                                    (hash_password(new_pw), username)
                                )
                                conn.commit()
                                conn.close()
                                st.success(f"Salasana päivitetty käyttäjälle **{username}**")
                                st.rerun()

                with col3:
                    confirm_key = f"confirm_del_user_{username}"
                    if not st.session_state.get(confirm_key, False):
                        if st.button("Poista", key=f"del_{username}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning(f"Poistetaanko **{username}** pysyvästi?")
                        c_yes, c_no = st.columns(2)
                        with c_yes:
                            if st.button("Kyllä, poista", key=f"del_yes_{username}", type="primary"):
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("DELETE FROM users WHERE username = ?", (username,))
                                c.execute("DELETE FROM predictions WHERE username = ?", (username,))
                                c.execute("DELETE FROM point_adjustments WHERE username = ?", (username,))
                                conn.commit()
                                conn.close()
                                st.session_state[confirm_key] = False
                                st.success(f"{username} poistettu")
                                st.rerun()
                        with c_no:
                            if st.button("Peruuta", key=f"del_no_{username}"):
                                st.session_state[confirm_key] = False
                                st.rerun()

                st.divider()

    elif admin_tab == "Tulosten syöttö":
        st.write("### 📊 Tulosten syöttö")

        now = datetime.now()

        total_matches = 0
        missing = 0
        started_missing = 0
        for _, matches in ALL_MATCH_LISTS:
            for m in matches:
                total_matches += 1
                real = load_real_result("match", m["id"])
                if real is None:
                    missing += 1
                    if now >= m["start"]:
                        started_missing += 1

        st.info(
            f"**Otteluita yhteensä:** {total_matches} · "
            f"**Syöttämättä:** {missing} · "
            f"**Alkaneet ilman tulosta:** {started_missing}"
        )

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filter = st.radio(
                "Näytä",
                ["Vain puuttuvat", "Kaikki", "Vain syötetyt"],
                horizontal=True,
                key="result_status_filter"
            )
        with col_f2:
            list_names = ["Kaikki listat"] + [name for name, _ in ALL_MATCH_LISTS]
            list_filter = st.selectbox("Lista", list_names, key="result_list_filter")
        with col_f3:
            search = st.text_input("Haku (joukkue)", placeholder="esim. KalPa", key="result_search")

        st.divider()

        def parse_score(text):
            if not text:
                return None
            text = text.strip().replace("–", "-").replace(":", "-").replace(" ", "-")
            parts = text.split("-")
            if len(parts) != 2:
                return None
            try:
                h, a = int(parts[0].strip()), int(parts[1].strip())
                if h < 0 or a < 0:
                    return None
                return h, a
            except ValueError:
                return None

        shown_any = False

        for list_name, matches in ALL_MATCH_LISTS:
            if list_filter != "Kaikki listat" and list_filter != list_name:
                continue

            list_matches_to_show = []
            for m in matches:
                real = load_real_result("match", m["id"])
                has_result = real is not None

                if status_filter == "Vain puuttuvat" and has_result:
                    continue
                if status_filter == "Vain syötetyt" and not has_result:
                    continue

                if search:
                    q = search.lower()
                    if q not in m["home"].lower() and q not in m["away"].lower():
                        continue

                list_matches_to_show.append((m, real, has_result))

            if not list_matches_to_show:
                continue

            shown_any = True
            with st.expander(f"**{list_name}** ({len(list_matches_to_show)} ottelua)", expanded=(status_filter == "Vain puuttuvat")):
                for m, real, has_result in list_matches_to_show:
                    pred_count = count_predictions_for_match(m["id"])
                    is_started = now >= m["start"]
                    double_txt = " 🔥 TUPLAPISTEET" if m["double"] else ""

                    if has_result:
                        status_color = "#00ff9d"
                        status_txt = f"Tallennettu: {real['home_goals']}–{real['away_goals']}"
                    elif is_started:
                        status_color = "#ff6b6b"
                        status_txt = "Peli alkanut – tulos puuttuu!"
                    else:
                        status_color = "#888888"
                        status_txt = "Ei vielä tulosta (peli ei alkanut)"

                    st.markdown(
                        f"**{m['home']} – {m['away']}{double_txt}**  \n"
                        f"<span style='color:#aaaaaa; font-size:0.9rem;'>{m['aika']}</span> · "
                        f"Veikkauksia: **{pred_count}** · "
                        f"<span style='color:{status_color};'>{status_txt}</span>",
                        unsafe_allow_html=True
                    )

                    default_score = ""
                    if has_result:
                        default_score = f"{real['home_goals']}-{real['away_goals']}"

                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        score_input = st.text_input(
                            "Tulos (esim. 2-1)",
                            value=default_score,
                            key=f"score_in_{m['id']}",
                            label_visibility="collapsed",
                            placeholder="esim. 2-1"
                        )
                    with c2:
                        save_clicked = st.button("Tallenna", key=f"save_res_{m['id']}", use_container_width=True)
                    with c3:
                        if has_result:
                            del_confirm_key = f"confirm_del_res_{m['id']}"
                            if not st.session_state.get(del_confirm_key, False):
                                if st.button("Poista tulos", key=f"del_res_{m['id']}", use_container_width=True):
                                    st.session_state[del_confirm_key] = True
                                    st.rerun()
                            else:
                                if st.button("Vahvista poisto", key=f"del_res_yes_{m['id']}", type="primary", use_container_width=True):
                                    delete_real_result("match", m["id"])
                                    st.session_state[del_confirm_key] = False
                                    st.success("Tulos poistettu")
                                    st.rerun()

                    if save_clicked:
                        parsed = parse_score(score_input)
                        if parsed is None:
                            st.error("Virheellinen muoto. Käytä esim. 2-1")
                        else:
                            home_g, away_g = parsed
                            overwrite_key = f"confirm_overwrite_{m['id']}"

                            if has_result and (
                                real["home_goals"] != home_g or real["away_goals"] != away_g
                            ):
                                if not st.session_state.get(overwrite_key, False):
                                    st.session_state[overwrite_key] = True
                                    st.warning(
                                        f"Tulos on jo {real['home_goals']}–{real['away_goals']}. "
                                        f"Haluatko korvata tuloksella {home_g}–{away_g}?"
                                    )
                                    ow1, ow2 = st.columns(2)
                                    with ow1:
                                        if st.button("Kyllä, korvaa", key=f"ow_yes_{m['id']}", type="primary"):
                                            result = {
                                                "home_goals": home_g,
                                                "away_goals": away_g,
                                                "score": f"{home_g}-{away_g}"
                                            }
                                            save_real_result("match", m["id"], result)
                                            st.session_state[overwrite_key] = False
                                            st.success(f"Tulos päivitetty: {m['home']} {home_g}–{away_g} {m['away']}")
                                            st.rerun()
                                    with ow2:
                                        if st.button("Peruuta", key=f"ow_no_{m['id']}"):
                                            st.session_state[overwrite_key] = False
                                            st.rerun()
                            else:
                                result = {
                                    "home_goals": home_g,
                                    "away_goals": away_g,
                                    "score": f"{home_g}-{away_g}"
                                }
                                save_real_result("match", m["id"], result)
                                st.success(f"Tulos tallennettu: {m['home']} {home_g}–{away_g} {m['away']}")
                                st.rerun()

                    st.markdown("---")

        if not shown_any:
            st.info("Ei otteluita valituilla suodattimilla.")

    elif admin_tab == "Pistekorjaukset":
        st.write("### ✏️ Manuaaliset pistekorjaukset")
        st.caption("Käytä virheiden korjaamiseen tai ylimääräisten pisteiden antamiseen. Korjaukset lisätään ottelupisteisiin.")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username FROM users ORDER BY username")
        usernames = [row["username"] for row in c.fetchall()]
        conn.close()

        if not usernames:
            st.info("Ei käyttäjiä.")
        else:
            selected_user = st.selectbox("Valitse pelaaja", usernames, key="adj_user")

            match_pts = calculate_match_points_only(selected_user)
            bonus = get_adjustment_total(selected_user)
            st.markdown(
                f"**Ottelupisteet:** {match_pts} · "
                f"**Korjaukset:** {bonus:+d} · "
                f"**Yhteensä:** **{match_pts + bonus}**"
            )

            st.write("#### Lisää korjaus")
            ac1, ac2 = st.columns([1, 3])
            with ac1:
                adj_points = st.number_input("Pisteet (+/-)", value=0, step=1, key="adj_pts")
            with ac2:
                adj_reason = st.text_input("Syy (valinnainen)", placeholder="esim. hyvitys virheestä / bonus", key="adj_reason")

            if st.button("Tallenna korjaus", type="primary"):
                if adj_points == 0:
                    st.error("Pisteiden määrä ei voi olla 0")
                else:
                    add_point_adjustment(
                        selected_user,
                        adj_points,
                        adj_reason,
                        st.session_state.logged_in_user or "admin"
                    )
                    st.success(f"Korjaus tallennettu: {adj_points:+d} p pelaajalle {selected_user}")
                    st.rerun()

            st.divider()
            st.write("#### Korjaushistoria")
            adjustments = get_user_adjustments(selected_user)
            if not adjustments:
                st.info("Ei korjauksia tälle pelaajalle.")
            else:
                for adj in adjustments:
                    created = adj["created_at"][:16].replace("T", " ") if adj["created_at"] else "-"
                    reason = adj["reason"] or "—"
                    dc1, dc2 = st.columns([5, 1])
                    with dc1:
                        st.markdown(
                            f"**{adj['points']:+d} p** · {reason}  \n"
                            f"<span style='color:#888; font-size:0.85rem;'>{created} · {adj['created_by'] or 'admin'}</span>",
                            unsafe_allow_html=True
                        )
                    with dc2:
                        del_adj_key = f"confirm_del_adj_{adj['id']}"
                        if not st.session_state.get(del_adj_key, False):
                            if st.button("Poista", key=f"del_adj_{adj['id']}"):
                                st.session_state[del_adj_key] = True
                                st.rerun()
                        else:
                            if st.button("Vahvista", key=f"del_adj_yes_{adj['id']}", type="primary"):
                                delete_point_adjustment(adj["id"])
                                st.session_state[del_adj_key] = False
                                st.success("Korjaus poistettu")
                                st.rerun()
                    st.markdown("---")

    elif admin_tab == "Varmuuskopiointi & palautus":
        st.subheader("💾 Varmuuskopiointi ja palautus")
        st.caption("Varmuuskopio sisältää tietokannan (käyttäjät + veikkaukset + tulokset + pistekorjaukset) sekä keskustelun (comments.json).")

        import zipfile
        import io

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM predictions")
        pred_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM real_results")
        result_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM point_adjustments")
        adj_count = c.fetchone()[0]
        conn.close()

        comments = load_json("comments.json", default=[])
        comment_count = len(comments)

        st.info(f"""
        **Nykyinen tila:**  
        • Käyttäjiä: **{user_count}**  
        • Veikkauksia: **{pred_count}**  
        • Syötettyjä tuloksia: **{result_count}**  
        • Pistekorjauksia: **{adj_count}**  
        • Kommentteja: **{comment_count}**
        """)

        st.write("#### Lataa varmuuskopio")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            if os.path.exists(DB_FILE):
                zip_file.write(DB_FILE, arcname="veikkaus.db")
            if os.path.exists("comments.json"):
                zip_file.write("comments.json", arcname="comments.json")
            else:
                zip_file.writestr("comments.json", "[]")

        zip_buffer.seek(0)

        st.download_button(
            label="⬇️ Lataa varmuuskopio (.zip)",
            data=zip_buffer,
            file_name=f"haamuhanska_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )

        st.divider()

        st.write("#### Palauta varmuuskopio")
        st.warning("Palautus korvaa nykyiset käyttäjät, veikkaukset, tulokset, pistekorjaukset **ja koko keskustelun**.")

        uploaded_zip = st.file_uploader("Valitse aiemmin ladattu .zip-tiedosto", type=["zip"])

        if uploaded_zip is not None:
            restore_key = "confirm_restore_backup"
            if not st.session_state.get(restore_key, False):
                if st.button("🔄 Palauta varmuuskopio", type="primary", use_container_width=True):
                    st.session_state[restore_key] = True
                    st.rerun()
            else:
                st.error("Haluatko varmasti palauttaa varmuuskopion? Nykyinen data ylikirjoitetaan.")
                r1, r2 = st.columns(2)
                with r1:
                    if st.button("Kyllä, palauta", type="primary", use_container_width=True):
                        try:
                            with zipfile.ZipFile(uploaded_zip, "r") as zip_ref:
                                if "veikkaus.db" in zip_ref.namelist():
                                    with open(DB_FILE, "wb") as f:
                                        f.write(zip_ref.read("veikkaus.db"))
                                if "comments.json" in zip_ref.namelist():
                                    with open("comments.json", "wb") as f:
                                        f.write(zip_ref.read("comments.json"))
                                else:
                                    save_json("comments.json", [])
                            st.session_state[restore_key] = False
                            st.success("✅ Varmuuskopio palautettu onnistuneesti!")
                            st.rerun()
                        except Exception as e:
                            st.session_state[restore_key] = False
                            st.error(f"Virhe palautuksessa: {e}")
                with r2:
                    if st.button("Peruuta", use_container_width=True):
                        st.session_state[restore_key] = False
                        st.rerun()

    elif admin_tab == "Tulevan kisan asetukset":
        st.info("Tänne lisätään seuraavan kisan asetukset myöhemmin.")

        st.markdown("---")
        st.subheader("💬 Keskustelun tyhjennys")
        st.warning("Tämä poistaa **kaikki** kommentit pysyvästi. Toimintoa ei voi perua.")

        clear_key = "confirm_clear_comments"
        if not st.session_state.get(clear_key, False):
            if st.button("Tyhjennä koko keskustelu", type="primary"):
                st.session_state[clear_key] = True
                st.rerun()
        else:
            st.error("Haluatko varmasti tyhjentää koko keskustelun?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Kyllä, tyhjennä", type="primary"):
                    save_json("comments.json", [])
                    st.session_state[clear_key] = False
                    st.success("✅ Keskustelu tyhjennetty!")
                    st.rerun()
            with cc2:
                if st.button("Peruuta"):
                    st.session_state[clear_key] = False
                    st.rerun()