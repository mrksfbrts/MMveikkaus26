import streamlit as st
import pandas as pd
import json
import hashlib
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="MM26 Veikkaus",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Yleinen tumma moderni teema */
    .stApp {
        background-color: #0a0f1c;
        color: #e0e0e0;
    }
    
    /* Otsikot */
    h1 {
        color: #00ff9d;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        color: #ffffff;
        font-weight: 600;
    }
    
    /* Sivupalkki */
    section[data-testid="stSidebar"] {
        background-color: #0f1629;
        border-right: 1px solid #1e2a44;
    }
    
    /* Korttimainen ulkoasu */
    .stContainer, div[data-testid="stExpander"] {
        background-color: #121a2e;
        border-radius: 12px;
        border: 1px solid #1e2a44;
    }
    
    /* Napit */
    .stButton button {
        background-color: #00ff9d;
        color: #0a0f1c;
        font-weight: 700;
        border-radius: 8px;
        height: 48px;
        transition: all 0.3s;
    }
    .stButton button:hover {
        background-color: #00cc7a;
        transform: translateY(-2px);
    }
    
    /* Taulukot */
    .stTable, .stDataFrame {
        border-radius: 0px;
        overflow: hidden;
    }
    
    /* Etusivun iso otsikko */
    .etusivu_text {
        text-align: center;
        font-size: 6.5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #00ff9d, #4d9fff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 60px 0 20px 0;
        text-shadow: 0 0 60px rgba(0, 255, 157, 0.5);
    }
    
    /* Viimeistely */
    .stMarkdown, .stText {
        line-height: 1.7;
    }
    
    /* Mobiili-parannus */
    @media (max-width: 768px) {
        .etusivu_text { font-size: 3.8rem; margin: 40px 0 15px 0; }
        h1 { font-size: 2rem !important; }
        .stButton button { height: 52px; font-size: 1.1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ====================== TIETOKANTA (SQLite) ======================
import sqlite3

DB_FILE = "veikkaus.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users-taulu
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                 )''')
    
    # Predictions-taulu
    c.execute('''CREATE TABLE IF NOT EXISTS predictions (
                    username TEXT,
                    match_id TEXT,
                    prediction TEXT,
                    is_special INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (username, match_id, is_special)
                 )''')
    
    # Real results -taulu
    c.execute('''CREATE TABLE IF NOT EXISTS real_results (
                    result_type TEXT,   -- "match" tai "special"
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


# Alusta tietokanta
init_db()

# ====================== VANHAN DATAN MIGRAATIO ======================
def migrate_from_json():
    """Siirtää vanhat JSON-tiedostot SQLiteen (suoritetaan kerran)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Migroi users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users_data = json.load(f)
            for username, pw_hash in users_data.items():
                c.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?, ?)", 
                         (username, pw_hash))
        except:
            pass
    
    # Migroi predictions
    if os.path.exists(PREDICTIONS_FILE):
        try:
            with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
                preds = json.load(f)
            for username, user_preds in preds.items():
                # Otteluvedot
                for match_id, pred in user_preds.items():
                    if match_id != "special":
                        c.execute("INSERT OR REPLACE INTO predictions (username, match_id, prediction, is_special) VALUES (?, ?, ?, 0)",
                                 (username, match_id, json.dumps(pred)))
                # Erikoiskohteet
                if "special" in user_preds:
                    for bet_id, value in user_preds["special"].items():
                        c.execute("INSERT OR REPLACE INTO predictions (username, match_id, prediction, is_special) VALUES (?, ?, ?, 1)",
                                 (username, bet_id, value))
        except:
            pass
    
    # Migroi real_results
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
            # Ottelut
            for mid, res in results.get("matches", {}).items():
                c.execute("INSERT OR REPLACE INTO real_results (result_type, id, result) VALUES ('match', ?, ?)",
                         (mid, json.dumps(res)))
            # Erikoiskohteet
            for bid, res in results.get("special", {}).items():
                c.execute("INSERT OR REPLACE INTO real_results (result_type, id, result) VALUES ('special', ?, ?)",
                         (bid, res))
        except:
            pass
    
    conn.commit()
    conn.close()
    st.toast("✅ Vanha data siirretty SQLiteen", icon="📦")


# Suorita migraatio ensimmäisellä käynnistyksellä
if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) < 1000:
    migrate_from_json()

# ====================== MUUTTUJIEN ALUSTUS ======================
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# Ladataan käyttäjät tietokannasta
users = get_all_users()

# ====================== MAAT ======================
countries = sorted([
    "Algeria", "Argentiina", "Australia", "Belgia", "Bosnia ja Hertsegovina", 
    "Brasilia", "Curaçao", "Ecuador", "Egypti", "Englanti", "Espanja", 
    "Etelä-Afrikka", "Etelä-Korea", "Ghana", "Haiti", "Hollanti", "Irak", 
    "Iran", "Itävalta", "Japani", "Jordania", "Kanada", "Kap Verde", 
    "Kolumbia", "Kongon demokraattinen tasavalta", "Kroatia", "Marokko", 
    "Meksiko", "Norja", "Norsunluurannikko", "Panama", "Paraguay", 
    "Portugali", "Qatar", "Ranska", "Ruotsi", "Saksa", "Saudi-Arabia", 
    "Senegal", "Skotlanti", "Sveitsi", "Tunisia", "Turkki", "Tšekki", 
    "USA", "Uruguay", "Uusi-Seelanti", "Uzbekistan"

])

# ====================== 72 OTTELUA - YLEN MUKAAN ======================
matches = [
    {"id":1, "date":"2026-06-11", "time":"22:00", "home":"Meksiko", "away":"Etelä-Afrikka", "group":"A", "double_points": False},
    {"id":2, "date":"2026-06-12", "time":"05:00", "home":"Etelä-Korea", "away":"Tšekki", "group":"A", "double_points": False},
    {"id":3, "date":"2026-06-12", "time":"22:00", "home":"Kanada", "away":"Bosnia ja Hertsegovina", "group":"B", "double_points": False},
    {"id":4, "date":"2026-06-13", "time":"04:00", "home":"USA", "away":"Paraguay", "group":"D", "double_points": True},   # Lohko D
    {"id":5, "date":"2026-06-13", "time":"22:00", "home":"Qatar", "away":"Sveitsi", "group":"B", "double_points": False},
    {"id":6, "date":"2026-06-14", "time":"01:00", "home":"Brasilia", "away":"Marokko", "group":"C", "double_points": False},
    {"id":7, "date":"2026-06-14", "time":"04:00", "home":"Haiti", "away":"Skotlanti", "group":"C", "double_points": False},
    {"id":8, "date":"2026-06-14", "time":"07:00", "home":"Australia", "away":"Turkki", "group":"D", "double_points": False},
    {"id":9, "date":"2026-06-14", "time":"20:00", "home":"Saksa", "away":"Curaçao", "group":"E", "double_points": False},
    {"id":10,"date":"2026-06-14", "time":"23:00", "home":"Hollanti", "away":"Japani", "group":"F", "double_points": False},
    {"id":11,"date":"2026-06-15", "time":"02:00", "home":"Norsunluurannikko", "away":"Ecuador", "group":"E", "double_points": False},
    {"id":12,"date":"2026-06-15", "time":"05:00", "home":"Ruotsi", "away":"Tunisia", "group":"F", "double_points": False},
    {"id":13,"date":"2026-06-15", "time":"19:00", "home":"Espanja", "away":"Kap Verde", "group":"H", "double_points": False},
    {"id":14,"date":"2026-06-15", "time":"22:00", "home":"Belgia", "away":"Egypti", "group":"G", "double_points": False},
    {"id":15,"date":"2026-06-16", "time":"01:00", "home":"Saudi-Arabia", "away":"Uruguay", "group":"H", "double_points": False},
    {"id":16,"date":"2026-06-16", "time":"04:00", "home":"Iran", "away":"Uusi-Seelanti", "group":"G", "double_points": True},   # Lohko G
    {"id":17,"date":"2026-06-16", "time":"22:00", "home":"Ranska", "away":"Senegal", "group":"I", "double_points": False},
    {"id":18,"date":"2026-06-17", "time":"01:00", "home":"Irak", "away":"Norja", "group":"I", "double_points": False},
    {"id":19,"date":"2026-06-17", "time":"04:00", "home":"Argentiina", "away":"Algeria", "group":"J", "double_points": False},
    {"id":20,"date":"2026-06-17", "time":"07:00", "home":"Itävalta", "away":"Jordania", "group":"J", "double_points": False},
    {"id":21,"date":"2026-06-17", "time":"20:00", "home":"Portugali", "away":"Kongon demokraattinen tasavalta", "group":"K", "double_points": False},
    {"id":22,"date":"2026-06-17", "time":"23:00", "home":"Englanti", "away":"Kroatia", "group":"L", "double_points": True},    # Lohko L
    {"id":23,"date":"2026-06-18", "time":"02:00", "home":"Ghana", "away":"Panama", "group":"L", "double_points": False},
    {"id":24,"date":"2026-06-18", "time":"05:00", "home":"Uzbekistan", "away":"Kolumbia", "group":"K", "double_points": False},
    {"id":25,"date":"2026-06-18", "time":"19:00", "home":"Tšekki", "away":"Etelä-Afrikka", "group":"A", "double_points": False},
    {"id":26,"date":"2026-06-18", "time":"22:00", "home":"Sveitsi", "away":"Bosnia ja Hertsegovina", "group":"B", "double_points": False},
    {"id":27,"date":"2026-06-19", "time":"01:00", "home":"Kanada", "away":"Qatar", "group":"B", "double_points": True},      # Lohko B
    {"id":28,"date":"2026-06-19", "time":"04:00", "home":"Meksiko", "away":"Etelä-Korea", "group":"A", "double_points": True}, # Lohko A
    {"id":29,"date":"2026-06-19", "time":"22:00", "home":"USA", "away":"Australia", "group":"D", "double_points": False},
    {"id":30,"date":"2026-06-20", "time":"01:00", "home":"Skotlanti", "away":"Marokko", "group":"C", "double_points": False},
    {"id":31,"date":"2026-06-20", "time":"04:00", "home":"Brasilia", "away":"Haiti", "group":"C", "double_points": False},
    {"id":32,"date":"2026-06-20", "time":"07:00", "home":"Turkki", "away":"Paraguay", "group":"D", "double_points": False},
    {"id":33,"date":"2026-06-20", "time":"20:00", "home":"Hollanti", "away":"Ruotsi", "group":"F", "double_points": False},
    {"id":34,"date":"2026-06-20", "time":"23:00", "home":"Saksa", "away":"Norsunluurannikko", "group":"E", "double_points": False},
    {"id":35,"date":"2026-06-21", "time":"03:00", "home":"Ecuador", "away":"Curaçao", "group":"E", "double_points": True},    # Lohko E
    {"id":36,"date":"2026-06-21", "time":"07:00", "home":"Tunisia", "away":"Japani", "group":"F", "double_points": True},     # Lohko F
    {"id":37,"date":"2026-06-21", "time":"19:00", "home":"Espanja", "away":"Saudi-Arabia", "group":"H", "double_points": False},
    {"id":38,"date":"2026-06-21", "time":"22:00", "home":"Belgia", "away":"Iran", "group":"G", "double_points": False},
    {"id":39,"date":"2026-06-22", "time":"01:00", "home":"Uruguay", "away":"Kap Verde", "group":"H", "double_points": False},
    {"id":40,"date":"2026-06-22", "time":"04:00", "home":"Uusi-Seelanti", "away":"Egypti", "group":"G", "double_points": False},
    {"id":41,"date":"2026-06-22", "time":"20:00", "home":"Argentiina", "away":"Itävalta", "group":"J", "double_points": False},
    {"id":42,"date":"2026-06-23", "time":"00:00", "home":"Ranska", "away":"Irak", "group":"I", "double_points": False},
    {"id":43,"date":"2026-06-23", "time":"03:00", "home":"Norja", "away":"Senegal", "group":"I", "double_points": True},      # Lohko I
    {"id":44,"date":"2026-06-23", "time":"06:00", "home":"Jordania", "away":"Algeria", "group":"J", "double_points": False},
    {"id":45,"date":"2026-06-23", "time":"20:00", "home":"Portugali", "away":"Uzbekistan", "group":"K", "double_points": False},
    {"id":46,"date":"2026-06-23", "time":"23:00", "home":"Englanti", "away":"Ghana", "group":"L", "double_points": False},
    {"id":47,"date":"2026-06-24", "time":"02:00", "home":"Panama", "away":"Kroatia", "group":"L", "double_points": False},
    {"id":48,"date":"2026-06-24", "time":"05:00", "home":"Kolumbia", "away":"Kongon demokraattinen tasavalta", "group":"K", "double_points": False},
    {"id":49,"date":"2026-06-24", "time":"22:00", "home":"Sveitsi", "away":"Kanada", "group":"B", "double_points": False},
    {"id":50,"date":"2026-06-24", "time":"22:00", "home":"Bosnia ja Hertsegovina", "away":"Qatar", "group":"B", "double_points": False},
    {"id":51,"date":"2026-06-25", "time":"01:00", "home":"Skotlanti", "away":"Brasilia", "group":"C", "double_points": True},   # Lohko C
    {"id":52,"date":"2026-06-25", "time":"01:00", "home":"Marokko", "away":"Haiti", "group":"C", "double_points": False},
    {"id":53,"date":"2026-06-25", "time":"04:00", "home":"Tšekki", "away":"Meksiko", "group":"A", "double_points": False},
    {"id":54,"date":"2026-06-25", "time":"04:00", "home":"Etelä-Afrikka", "away":"Etelä-Korea", "group":"A", "double_points": False},
    {"id":55,"date":"2026-06-25", "time":"23:00", "home":"Curaçao", "away":"Norsunluurannikko", "group":"E", "double_points": False},
    {"id":56,"date":"2026-06-25", "time":"23:00", "home":"Ecuador", "away":"Saksa", "group":"E", "double_points": False},
    {"id":57,"date":"2026-06-26", "time":"02:00", "home":"Japani", "away":"Ruotsi", "group":"F", "double_points": False},
    {"id":58,"date":"2026-06-26", "time":"02:00", "home":"Tunisia", "away":"Hollanti", "group":"F", "double_points": False},
    {"id":59,"date":"2026-06-26", "time":"05:00", "home":"Turkki", "away":"USA", "group":"D", "double_points": False},
    {"id":60,"date":"2026-06-26", "time":"05:00", "home":"Paraguay", "away":"Australia", "group":"D", "double_points": False},
    {"id":61,"date":"2026-06-26", "time":"22:00", "home":"Norja", "away":"Ranska", "group":"I", "double_points": False},
    {"id":62,"date":"2026-06-26", "time":"22:00", "home":"Senegal", "away":"Irak", "group":"I", "double_points": False},
    {"id":63,"date":"2026-06-27", "time":"03:00", "home":"Kap Verde", "away":"Saudi-Arabia", "group":"H", "double_points": False},
    {"id":64,"date":"2026-06-27", "time":"03:00", "home":"Uruguay", "away":"Espanja", "group":"H", "double_points": True},     # Lohko H
    {"id":65,"date":"2026-06-27", "time":"06:00", "home":"Egypti", "away":"Iran", "group":"G", "double_points": False},
    {"id":66,"date":"2026-06-27", "time":"06:00", "home":"Uusi-Seelanti", "away":"Belgia", "group":"G", "double_points": False},
    {"id":67,"date":"2026-06-28", "time":"00:00", "home":"Panama", "away":"Englanti", "group":"L", "double_points": False},
    {"id":68,"date":"2026-06-28", "time":"00:00", "home":"Kroatia", "away":"Ghana", "group":"L", "double_points": False},
    {"id":69,"date":"2026-06-28", "time":"02:30", "home":"Kolumbia", "away":"Portugali", "group":"K", "double_points": True},  # Lohko K
    {"id":70,"date":"2026-06-28", "time":"02:30", "home":"Kongon demokraattinen tasavalta", "away":"Uzbekistan", "group":"K", "double_points": False},
    {"id":71,"date":"2026-06-28", "time":"05:00", "home":"Algeria", "away":"Itävalta", "group":"J", "double_points": False},
    {"id":72,"date":"2026-06-28", "time":"05:00", "home":"Jordania", "away":"Argentiina", "group":"J", "double_points": True}   # Lohko J
]

# ====================== ERIKOISKOHTEET ======================
special_bets = [
    {"id": "most_goals", "name": "Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 5, "type": "select"},
    {"id": "most_cards", "name": "Mikä maa saa alkulohkoissa eniten varoituksia?", "points": 5, "type": "select"},
    {"id": "top_scorer", "name": "Paras maalintekijä", "points": 10, "type": "text"},
    {"id": "top_scorer_goals", "name": "Millä maalimäärällä voitetaan maalintekijäkuninkuus?", "points": 5, "type": "number"},
    {"id": "champion", "name": "Maailmanmestari?", "points": 10, "type": "select"},

    # Lohkovoittajat
    *[{"id": f"group_{letter.lower()}", "name": f"Lohko {letter} voittaja", "points": 3, "type": "select"} for letter in "ABCDEFGHIJKL"],

    # Uudet kohteet toiveidesi mukaan
    {"id": "most_goals_group", "name": "Missä lohkossa tehdään yhteensä eniten maaleja?", "points": 5, "type": "group_select"},
    {"id": "total_penalties", "name": "Kuinka monta rangaistuspotkua alkulohkoissa tuomitaan yhteensä?", "points": 3, "type": "penalty_range"},
    {"id": "lowest_xg", "name": "Mikä maa luo vähiten maaliodottamaa (xG) alkulohkojen peleissä?", "points": 5, "type": "select"},
    {"id": "ronaldo_goals", "name": "Monta maalia Cristiano Ronaldo tekee alkulohkojen peleissä?", "points": 3, "type": "number"},

    # Kyllä/Ei -kohteet
    {"id": "goal_first_minute", "name": "Tehdäänkö alkulohkojen yhdessäkään ottelussa maalia ensimmäisen peliminuutin aikana?", "points": 3, "type": "yesno"},
    {"id": "own_goals_5plus", "name": "Tehdäänkö alkulohkojen peleissä vähintään kuusi omaa maalia?", "points": 3, "type": "yesno"},
    {"id": "zero_zero_5plus", "name": "Päättyykö alkulohkojen peleistä vähintään kuusi ottelua maalittomaan tasapeliin?", "points": 3, "type": "yesno"},
    {"id": "red_cards_5plus", "name": "Kirjataanko alkulohkojen peleissä vähintään kuusi suoraa punaista korttia?", "points": 3, "type": "yesno"},
    {"id": "free_kick_goal", "name": "Tehdäänkö alkulohkoissa maalia suoraan vapaapotkusta?", "points": 3, "type": "yesno"},
    {"id": "hat_trick", "name": "Nähdäänkö alkulohkojen peleissä hattutemppu?", "points": 3, "type": "yesno"},
]


# ====================== FUNKTIOT ======================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default


def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.toast("💾 Tallennettu", icon="✅")
    except:
        st.error("Tallennus epäonnistui")


def get_countdown(match):
    try:
        match_time = datetime.strptime(f"{match['date']} {match['time']}", "%Y-%m-%d %H:%M")
        lock_time = match_time - timedelta(minutes=15)
        time_left = lock_time - datetime.now()
        if time_left.total_seconds() <= 0:
            return "🔴 Lukittu", False
        hours, rem = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)
        return f"⏳ {hours}t {minutes:02d}min jäljellä", True
    except:
        return "Virhe", False


def get_special_bets_countdown():
    return get_countdown(matches[0]) if matches else ("", False)


def calculate_match_points(pred, real, is_double=False):
    """
    pred ja real ovat listoja: [kotimaali, vierasmaali]
    is_double = True → pisteet tuplataan
    """
    if not pred or not real:
        return 0
    
    p_home, p_away = pred
    r_home, r_away = real
    
    # 1. Täysin oikein
    if p_home == r_home and p_away == r_away:
        points = 8
    
    # Oikea voittaja tai tasapeli?
    elif (p_home > p_away and r_home > r_away) or \
         (p_home < p_away and r_home < r_away) or \
         (p_home == p_away and r_home == r_away):
        
        # Tasapeli
        if p_home == p_away:
            points = 4
        # 6 pistettä: toisen joukkueen maalit oikein, toisen yhdellä väärin
        elif (abs(p_home - r_home) == 0 and abs(p_away - r_away) == 1) or \
             (abs(p_home - r_home) == 1 and abs(p_away - r_away) == 0):
            points = 6
        # 5 pistettä: toisen joukkueen maalit täysin oikein
        elif abs(p_home - r_home) == 0 or abs(p_away - r_away) == 0:
            points = 5
        # 3 pistettä: vain oikea voittaja
        else:
            points = 3
    else:
        points = 0  # Väärä 1X2
    
    # Tuplapisteet jos ottelu on merkitty sellaiseksi
    if is_double:
        points *= 2
        
    return points

# ====================== SIVUPALKKI ======================
st.sidebar.title("⚽ MM26 - Veikkauskisa")

if not st.session_state.get("logged_in_user"):
    page = "Kirjaudu / Rekisteröidy"
else:
    page = st.sidebar.selectbox(
        "",
        [
            "Etusivu",
            "Veikkaa otteluita",
            "Veikkaa erikoiskohteita",
            "Omat veikkaukset",
            "Veikkaustilanne",
            "Kaikkien veikkaukset",
            "Säännöt",
            "Admin"
        ]
    )
    
    st.sidebar.success(f"{st.session_state.logged_in_user}")
    
    if st.sidebar.button("Kirjaudu ulos", key="logout_btn"):
        st.session_state.logged_in_user = None
        st.rerun()

# ====================== ETUSIVU ======================
if page == "Etusivu":
    # Taustatyylit
    st.markdown("""
        <style>
            .etusivu_text { 
                text-align: center; 
                font-size: 9.2rem; 
                font-weight: 1000; 
                color: #00ff9d; 
                text-shadow: 0 0px rgba(0, 255, 157, 0.8);
                margin: 40px 0 30px 0;
                position: relative;
                z-index: 2;
            }
            .welcome_text { 
                text-align: center; 
                font-size: 5.7rem; 
                font-weight: 1000; 
                color: #e0e0e0; 
                margin-bottom: 80px;
                position: relative;
                z-index: 2;
            }
            .background-countries {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                z-index: 0;
                opacity: 0.08;
                color: #ffffff;
                font-size: 1.15rem;
                line-height: 1.8;
                pointer-events: none;
                user-select: none;
            }
        </style>
    """, unsafe_allow_html=True)

   

    # Varsinainen sisältö
    st.markdown('<div class="etusivu_text">MM26</div>', unsafe_allow_html=True)
    st.markdown('<p class="welcome_text">Tervetuloa veikkaamaan ja onnea matkaan!</p>', unsafe_allow_html=True)

# ====================== KIRJAUDU / REKISTERÖIDY ======================
if page == "Kirjaudu / Rekisteröidy":
    if st.session_state.logged_in_user:
        st.success(f"Olet kirjautuneena nimellä: **{st.session_state.logged_in_user}**")
        if st.button("Kirjaudu ulos"):
            st.session_state.logged_in_user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Kirjaudu sisään", "Luo uusi tunnus"])
        
               with tab1:  # Kirjautuminen
            st.subheader("Kirjaudu sisään")
            col = st.columns([1, 2, 1])[1]
            with col:
                username = st.text_input("Käyttäjänimi", key="login_user")
                password = st.text_input("Salasana", type="password", key="login_pass")
                
                if st.button("Kirjaudu sisään", type="primary", use_container_width=True):
                    if username in users and users[username] == hash_password(password):
                        st.session_state.logged_in_user = username
                        st.success("Kirjautuminen onnistui!")
                        st.rerun()
                    else:
                        st.error("Väärä käyttäjänimi tai salasana")
        
        with tab2:  # Rekisteröityminen
            st.subheader("Luo uusi tunnus")
            col = st.columns([1, 2, 1])[1]
            with col:
                new_user = st.text_input("Käyttäjänimi", key="reg_user")
                new_pass = st.text_input("Salasana", type="password", key="reg_pass")
                new_pass2 = st.text_input("Toista salasana", type="password", key="reg_pass2")
                
                if st.button("Rekisteröidy", type="primary", use_container_width=True):
                    if not new_user or not new_pass:
                        st.error("Käyttäjänimi ja salasana ovat pakollisia")
                    elif new_pass != new_pass2:
                        st.error("Salasanat eivät täsmää")
                    elif new_user in users:
                        st.error("Käyttäjänimi on jo käytössä")
                    else:
                        users[new_user] = hash_password(new_pass)
                        save_json(USERS_FILE, users)
                        st.success("Tunnus luotu onnistuneesti! Voit nyt kirjautua sisään.")

# ====================== SÄÄNNÖT ======================
if page == "Säännöt":
    st.title("Säännöt ja pisteytysjärjestelmä")
    st.markdown("---")
    
    st.subheader("Otteluveikkaukset")
    
    st.markdown("""
    Pisteitä saa ainoastaan, kun on veikannut oikeaa tulosta (1X2). Lopullisen veikkauskohteen pistemäärän määrittelee se, kuinka lähelle oikeaa tulosta veikkasit. Jokaisessa lohkossa on yksi ennalta määritelty peli, josta on tarjolla tuplapisteet.  
    """)
    
    # Pistetaulukko
    data = {
        "Veikkauksesi": [
            "Täysin oikea tulos",
            "Oikea voittaja + toisen joukkueen maalimäärä oikein ja toisen vain **yhdellä** maalilla väärin",
            "Oikea voittaja + toisen joukkueen maalimäärä oikein ja toisen **yli yhdellä** maalilla väärin",
            "Oikein veikattu tasapeli, mutta maalimäärät väärin",
            "Oikea voittaja, mutta molempien joukkueiden maalit väärin",
            "Väärä 1X2"
        ],
        "Pisteet": ["**8**", "**6**", "**5**", "**4**", "**3**", "**0**"]
    }
    
    import pandas as pd
    df = pd.DataFrame(data)
    st.table(df.style.set_properties(**{'text-align': 'left'}))
    
    st.markdown("---")
    
    st.subheader("Erikoiskohteet")
    st.write("**Jokaiselle erikoiskohteelle on määritelty omat pistemääränsä oikein veikatessa (3-10). Ne näkyvät veikkausta tehtäessä. Erikoiskohteista saatavat pisteet rekisteröityvät veikkaustilanteeseen heti kun kohde on ratkennut. Muutamassa erikoiskohteessa voidaan päätyä tilanteeseen, jossa useampi eri veikkaus on oikein. Tällöin tietenkin pisteet tulevat kaikista näistä veikkauksista samanarvoisesti.**")
    
    st.markdown("---")
    st.caption("""
    Yksittäinen veikkauskohde/ottelu sulkeutuu aina 15 minuuttia ennen pelin alkamista. Voit muokata omaa veikkaustasi siihen asti aivan vapaasti. Kun kohde sulkeutuu se poistuu veikattavien kohteiden listalta ja ylimpänä näkyy aina seuraavaksi sulkeutuva kohde. Erikoiskohteet sulkeutuvat kaikki samanaikaisesti 15 minuuttia ennen kisojen ensimmäisen pelin alkua. Pisteet päivittyvät automaattisesti. Näet omat veikkauksesi heti valikon kohdasta "Omat veikkaukset" kun olet ne veikannut, kaikkien muiden veikkaukset tulevat vertailtavaksi näkyviin vasta kun pelikohde on mennyt kiinni ja tulos kirjattu sivulle.""")


# ====================== VEIKKAA OTTELUITA ======================
if page == "Veikkaa otteluita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader("Veikkaa otteluita")
        
        open_matches = [m for m in matches if real_results.get("matches", {}).get(str(m['id'])) is None]
        
        if not open_matches:
            st.success("✅ Kaikki ottelut on jo veikkailtu tai lukittu!")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["Lista 1", "Lista 2", "Lista 3", "Lista 4"])
            tabs_list = [tab1, tab2, tab3, tab4]
            
            for tab_idx, tab in enumerate(tabs_list):
                with tab:
                    start = tab_idx * 18
                    end = min(start + 18, len(open_matches))
                    current_tab_matches = open_matches[start:end]
                    
                    for m in current_tab_matches:
                        match_id = str(m['id'])
                        is_double = m.get("double_points", False)
                        
                        countdown_info = get_countdown(m)
                        if isinstance(countdown_info, tuple):
                            countdown_str, is_open = countdown_info
                        else:
                            countdown_str, is_open = str(countdown_info), False
                        
                        # Tuplapiste-ottelun korostus
                        if is_double:
                            st.markdown(f"""
                                <div style="background: linear-gradient(90deg, #2a1f0f, #3a2a10); 
                                            border: 2px solid #ffcc00; border-radius: 12px; 
                                            padding: 12px 15px; margin: 8px 0;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span style="font-size: 1.4rem;">🔥</span>
                                        <span style="color: #ffcc00; font-weight: 700; font-size: 1.1rem;">
                                            TUPLAPISTEET ×2
                                        </span>
                                    </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')})")
                        
                        if not is_open:
                            st.markdown("🔴 **Kohde on suljettu**")
                        else:
                            st.markdown(f"🟢 **{countdown_str}**")
                        
                        col_home, col_away = st.columns(2)
                        with col_home:
                            home_score = st.number_input("", 0, 10, 0, key=f"h_{match_id}")
                        with col_away:
                            away_score = st.number_input("", 0, 10, 0, key=f"a_{match_id}")
                        
                        if st.button("Tallenna veikkaus", key=f"save_{match_id}", use_container_width=True):
                            if user not in predictions:
                                predictions[user] = {}
                            predictions[user][match_id] = [home_score, away_score]
                            save_json(PREDICTIONS_FILE, predictions)
                            st.success(f"Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                        
                        if is_double:
                            st.markdown("</div>", unsafe_allow_html=True)  # Suljetaan tupladivi
                        
                        st.divider()
                        
# ====================== VEIKKAA ERIKOISKOHTEITA ======================
if page == "Veikkaa erikoiskohteita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        real_special = real_results.get("special", {})
        
        if real_special and len(real_special) > 0:
            st.success("✅ Erikoiskohteet ovat lukittu.")
            st.info("Voit tarkastella veikkauksiasi 'Omat veikkaukset' -sivulta.")
        else:
            st.subheader("🏆 Veikkaa erikoiskohteita")
            st.caption("Erikoiskohteet ovat avoinna")
            
            user_special = predictions.get(user, {}).get("special", {})
            
            for bet in special_bets:
                bet_id = bet["id"]
                pred_value = user_special.get(bet_id)
                real_value = real_special.get(bet_id)
                
                question = bet.get('name') or bet.get('question') or bet.get('text', bet_id)
                st.markdown(f"**{question}** ({bet.get('points', 6)} pistettä)")
                
                if real_value:
                    st.success(f"Toteutunut vastaus: **{real_value}**")
                else:
                    # Eri tyyppien käsittely
                    if bet["type"] == "yesno":
                        value = st.radio("Valitse:", ["Kyllä", "Ei"], horizontal=True, 
                                       key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["type"] == "group_select":
                        groups = ["A","B","C","D","E","F","G","H","I","J","K","L"]
                        value = st.selectbox("Valitse lohko", options=groups, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["type"] == "penalty_range":
                        options = ["0-10", "11-20", "21-30", "31+"]
                        value = st.selectbox("Valitse vaihtoehto", options=options, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["id"] in ["most_goals", "most_cards", "champion", "lowest_xg", 
                                     "most_penalties_scored", "most_sub_goals", "most_corners", 
                                     "most_first_half_goals"]:
                        value = st.selectbox("Valitse maa", options=countries, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["id"].startswith("group_"):
                        group_letter = bet["id"].split("_")[1].upper()
                        group_matches = [m for m in matches if m.get("group") == group_letter]
                        group_teams = sorted(set([m["home"] for m in group_matches] + [m["away"] for m in group_matches]))
                        value = st.selectbox("Lohkovoittaja", options=group_teams, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["type"] == "number" or bet["id"] in ["ronaldo_goals"]:
                        value = st.number_input("Anna numero", min_value=0, max_value=20, value=0, 
                                              key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    elif bet["id"] == "top_scorer":
                        value = st.text_input("Pelaajan nimi", key=f"spec_{bet_id}", label_visibility="collapsed")
                    else:
                        value = st.text_input("Vastaus", key=f"spec_{bet_id}", label_visibility="collapsed")
                    
                    if st.button("Tallenna veikkaus", key=f"save_spec_{bet_id}", use_container_width=True):
                        if user not in predictions:
                            predictions[user] = {"special": {}}
                        if "special" not in predictions[user]:
                            predictions[user]["special"] = {}
                        predictions[user]["special"][bet_id] = str(value).strip()
                        save_json(PREDICTIONS_FILE, predictions)
                        st.success("✅ Veikkaus tallennettu!")
                
                st.divider()

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.subheader("VEIKKAUSTILANNE")
    
    # Lasketaan pisteet
    leaderboard = []
    for user in users.keys():
        user_pred = predictions.get(user, {})
        total_points = 0
        
        for m in matches:
            pred = user_pred.get(str(m['id']))
            real = real_results.get("matches", {}).get(str(m['id']))
            if pred and real:
                is_double = m.get("double_points", False)
                total_points += calculate_match_points(pred, real, is_double)
        
        user_special = user_pred.get("special", {})
        real_special = real_results.get("special", {})
        for bet in special_bets:
            pred_val = user_special.get(bet["id"])
            real_val = real_special.get(bet["id"])
            if pred_val and real_val:
                user_str = str(pred_val).lower().strip()
                real_list = [x.strip().lower() for x in str(real_val).split(",")]
                if user_str in real_list:
                    total_points += bet.get("points", 6)
        
        leaderboard.append({"Nimi": user, "Pisteet": total_points})
    
    leaderboard.sort(key=lambda x: x["Pisteet"], reverse=True)
    
    for i, entry in enumerate(leaderboard):
        entry["Sija"] = i + 1
    
    # Tyylikäs versio ohuilla viivoilla
    for entry in leaderboard:
        c1, c2, c3 = st.columns([0.5, 0.3, 1.4])
        
        with c1:
            st.markdown(f"""
                <div style="text-align: right; font-size: 1.8rem; font-weight: 700; color: #00ff9d; padding-right: 12px;">
                    {entry["Sija"]}
                </div>
            """, unsafe_allow_html=True)
        
        with c2:
            st.markdown(f"""
                <div style="font-size: 1.8rem; font-weight: 700; color: #e0e0e0;">
                    {entry["Nimi"]}
                </div>
            """, unsafe_allow_html=True)
        
        with c3:
            st.markdown(f"""
                <div style="text-align: center; background: #2a2a4a; color: #ffff88; 
                font-weight: 700; font-size: 1.2rem; width: 54px; height: 54px; 
                border-radius: 50%; display: flex; align-items: center; 
                justify-content: center; margin: 0 auto; box-shadow: 0 0 12px rgba(255,255,136,0.3);">
                    {entry["Pisteet"]}
                </div>
            """, unsafe_allow_html=True)
        
        # Hieno ohut viiva
        st.markdown("""
            <div style="height: 1px; background: linear-gradient(to right, transparent, #334466, transparent); 
            margin: 8px 40px;"></div>
        """, unsafe_allow_html=True)

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"OMAT VEIKKAUKSET")
        
        tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
        
        # ====================== TAB 1: OTTELUVEIKKAUKSET ======================
        with tab1:
            for m in matches:
                match_id = str(m['id'])
                pred = predictions.get(user, {}).get(match_id)
                real = real_results.get("matches", {}).get(match_id)
                is_double = m.get("double_points", False)
                
                st.markdown(f"**{m['home']} — {m['away']}**")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if real:
                        st.markdown(f"**Tulos:** {real[0]}–{real[1]}")
                    else:
                        st.write("Tulos ei vielä saatavilla")
                    
                    if pred:
                        st.write(f"Oma veikkaus: **{pred[0]}–{pred[1]}**")
                    else:
                        st.write("Ei veikkausta")
                
                with col2:
                    if real and pred:
                        pts = calculate_match_points(pred, real, is_double)
                        double_note = " (×2)" if is_double else ""
                        st.success(f"**+{pts} pistettä**{double_note}")
                    elif real:
                        st.info("0 pistettä")
                
                st.divider()

        # ====================== TAB 2: ERIKOISKOHTEET ======================
        with tab2:
            user_special = predictions.get(user, {}).get("special", {})
            real_special = real_results.get("special", {})
            
            for bet in special_bets:
                pred_value = user_special.get(bet["id"])
                real_value = real_special.get(bet["id"])
                
                question = bet.get('name', bet["id"])
                st.markdown(f"**{question}**")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if real_value:
                        st.success(f"Toteutunut: **{real_value}**")
                    if pred_value:
                        st.write(f"Oma veikkaus: {pred_value}")
                    else:
                        st.write("Ei veikkausta")
                
                with col2:
                    if real_value and pred_value:
                        user_str = str(pred_value).lower().strip()
                        real_list = [x.strip().lower() for x in str(real_value).split(",")]
                        pts = bet.get("points", 6) if user_str in real_list else 0
                        if pts > 0:
                            st.success(f"+{pts}p")
                
                st.divider()
           
# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("KAIKKIEN VEIKKAUKSET")
    st.caption("Tälle sivulle päivittyvät kaikkien veikkaajien tekemät veikkaukset vertailtavaksi ottelujen päätyttyä")
    
    tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
    
    locked_matches = real_results.get("matches", {})
    locked_special = real_results.get("special", {})
    
    # ====================== TAB 1: OTTELUT ======================
    with tab1:
        if not locked_matches:
            st.info("Yksikään veikkauskohde ei ole vielä ratkennut")
        else:
            for m in matches:
                match_id = str(m['id'])
                real = locked_matches.get(match_id)
                if real:
                    is_double = m.get("double_points", False)
                    double_text = " **(×2)**" if is_double else ""
                    
                    st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')}){double_text}")
                    st.success(f"Tulos: **{real[0]}–{real[1]}**")
                    
                    for u in sorted(users.keys()):
                        pred = predictions.get(u, {}).get(match_id)
                        if pred:
                            pts = calculate_match_points(pred, real, is_double)
                            st.markdown(f"**{u}**: {pred[0]}–{pred[1]} (+{pts}p)")
                    st.divider()

    # ====================== TAB 2: ERIKOISKOHTEET ======================
    with tab2:
        if not locked_special:
            st.info("Erikoiskohteiden veikkaus päättyy 15 minuuttia ennen ensimmäisen pelin alkua")
        else:
            for bet in special_bets:
                bet_id = bet["id"]
                real_val = locked_special.get(bet_id)
                
                if real_val:
                    if bet_id == "most_goals":
                        question = "Mikä maa tekee alkulohkojen peleissä eniten maaleja?"
                    elif bet_id == "most_cards":
                        question = "Mikä maa saa alkulohkojen peleissä eniten varoituksia?"
                    elif bet_id == "top_scorer":
                        question = "Paras maalintekijä koko turnauksessa?"
                    elif bet_id == "top_scorer_goals":
                        question = "Millä maalimäärällä voitetaan maalintekijäkuninkuus?"
                    elif bet_id == "champion":
                        question = "Maailmanmestarimaa?"
                    elif "group_" in bet_id:
                        group_letter = bet_id.split("_")[-1].upper()
                        question = f"Lohkon {group_letter} voittaja?"
                    else:
                        question = bet.get('name', bet_id.replace("_", " ").title())
                    
                    st.markdown(f"**{question}**")
                    st.success(f"**Oikea vastaus:** {real_val}")
                    
                    for u in sorted(users.keys()):
                        user_special = predictions.get(u, {}).get("special", {})
                        user_pred = user_special.get(bet_id)
                        if user_pred:
                            user_str = str(user_pred).lower().strip()
                            real_list = [x.strip().lower() for x in str(real_val).split(",")]
                            pts = bet.get("points", 6) if user_str in real_list else 0
                            if pts > 0:
                                st.markdown(f"**{u}**: {user_pred} (+{pts}p)")
                            else:
                                st.markdown(f"**{u}**: {user_pred}")
                    
                    st.divider()
    
    # ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")
    
    ADMIN_PASSWORD = "admin123"   # <--- VAIHDA TÄHÄN OMA SALASANASI
    
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
    
    admin_choice = st.sidebar.selectbox(
        "Valitse toiminto",
        ["Lisää ottelun tulos", "Lisää erikoiskohteen tulos", "Hallinnoi käyttäjiä"]
    )
    
    if admin_choice == "Lisää ottelun tulos":
        st.write("### Ottelujen tulosten syöttö / muokkaus")
        
        for m in matches:
            match_id = str(m['id'])
            real = real_results.get("matches", {}).get(match_id)
            
            col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
            with col1:
                st.write(f"**{m['home']} — {m['away']}**")
            with col2:
                h = st.number_input("Koti", 0, 20, value=real[0] if real else 0, key=f"h{match_id}")
            with col3:
                a = st.number_input("Vieras", 0, 20, value=real[1] if real else 0, key=f"a{match_id}")
            with col4:
                if st.button("Tallenna", key=f"save{match_id}"):
                    if "matches" not in real_results:
                        real_results["matches"] = {}
                    real_results["matches"][match_id] = [h, a]
                    save_json("real_results.json", real_results)
                    st.success(f"✅ Tallennettu: {m['home']} {h}–{a} {m['away']}")
                    st.rerun()
                
                if real and st.button("🗑️ Poista tulos", key=f"del{match_id}"):
                    real_results["matches"].pop(match_id, None)
                    save_json("real_results.json", real_results)
                    st.success("Tulos poistettu – kohde avattu uudelleen")
                    st.rerun()
    
    elif admin_choice == "Lisää erikoiskohteen tulos":
        st.write("### Erikoiskohteiden tulosten syöttö")
        for bet in special_bets:
            bet_id = bet["id"]
            real_val = real_results.get("special", {}).get(bet_id)
            question = bet.get('question') or bet.get('text', bet_id)
            
            st.write(f"**{question}**")
            new_val = st.text_input("Oikea vastaus", value=real_val or "", key=f"e{bet_id}")
            
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("Tallenna", key=f"save{bet_id}"):
                    if "special" not in real_results:
                        real_results["special"] = {}
                    real_results["special"][bet_id] = new_val.strip()
                    save_json("real_results.json", real_results)
                    st.success("✅ Tallennus onnistui!")
                    st.rerun()
            with col2:
                if real_val and st.button("Poista tulos", key=f"del_spec{bet_id}"):
                    real_results["special"].pop(bet_id, None)
                    save_json("real_results.json", real_results)
                    st.success("Tulos poistettu")
                    st.rerun()
    
    elif admin_choice == "Hallinnoi käyttäjiä":
        # (sama kuin aiemmin)
        st.write("### 👥 Hallinnoi käyttäjiä")
        if not users:
            st.info("Ei käyttäjiä")
        else:
            for user in list(users.keys()):
                col1, col2 = st.columns([4,1])
                with col1:
                    st.write(f"**{user}**")
                with col2:
                    if st.button("Poista", key=f"del_user{user}"):
                        users.pop(user, None)
                        predictions.pop(user, None)
                        save_json("users.json", users)
                        save_json("predictions.json", predictions)
                        st.success(f"{user} poistettu")
                        st.rerun()
