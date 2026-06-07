import streamlit as st
import pandas as pd
import json
import hashlib
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="HAAMUHANSKA",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Vihreät napit kaikille sivuille */
    .stButton button {
        background-color: #00ff9d !important;
        color: #0a0f1c !important;
        font-weight: 700;
        border: none;
    }
    .stButton button:hover {
        background-color: #00cc7a !important;
    }
    
    /* Erityisesti "Kirjaudu ulos" ja "Päivitä veikkaus" */
    button[kind="secondary"] {
        background-color: #00ff9d !important;
        color: #0a0f1c !important;
    }
</style>
""", unsafe_allow_html=True)

# ====================== GLOBAALI TYYLITTELY ======================
st.markdown("""
<style>
    .stApp {
        background-image: url("https://i.imgur.com/r4bYzli.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(rgba(10,15,28,0.75), rgba(10,15,28,0.88));
        z-index: 0;
    }
    
    /* Pakotetaan valkoinen raja sivupalkkiin */
    section[data-testid="stSidebar"] {
        background-color: #05080f !important;
        border-right: 2px solid #e0e0e0 !important;
        box-shadow: 3px 0 15px rgba(224, 224, 224, 0.1) !important;
    }
    
    .block-container {
        position: relative;
        z-index: 1;
    }
</style>
""", unsafe_allow_html=True)


# ====================== TYYLITTELY ======================
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://i.imgur.com/r4bYzli.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(rgba(10,15,28,0.85), rgba(10,15,28,0.92));
        z-index: 0;
    }

    /* === SIVUPALKKI + RAJA === */
    section[data-testid="stSidebar"] {
        background-color: #05080f !important;
        border-right: 3px solid rgba(0, 255, 157, 0.4);   /* Vihreä raja */
        box-shadow: 4px 0 15px rgba(0, 255, 157, 0.15);
    }
    /* ======================== */

    /* Muut tyylit (lomake jne.) */
    .stTabs [data-testid="stTabPanel"] {
        background-color: #05080f !important;
        border-radius: 16px;
        padding: 40px 35px;
        max-width: 420px !important;
        margin: 40px auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== TIEDOSTOT ======================
USERS_FILE = "users.json"
PREDICTIONS_FILE = "predictions.json"
RESULTS_FILE = "real_results.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(file_path, default=None):
    if default is None:
        default = {}
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
        return True
    except Exception as e:
        st.error(f"Tallennus epäonnistui: {e}")
        return False

# Lataa tiedot
users = load_json(USERS_FILE)
predictions = load_json(PREDICTIONS_FILE)
real_results = load_json(RESULTS_FILE)

# Session state
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

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
    {"id":31,"date":"2026-06-20", "time":"03:30", "home":"Brasilia", "away":"Haiti", "group":"C", "double_points": False},
    {"id":32,"date":"2026-06-20", "time":"06:00", "home":"Turkki", "away":"Paraguay", "group":"D", "double_points": False},
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
    {"id":72,"date":"2026-06-28", "time":"05:00", "home":"Jordania", "away":"Argentiina", "group":"J", "double_points": True},
    {"id":73, "date":"2026-06-28", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":74, "date":"2026-06-29", "time":"20:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":75, "date":"2026-06-29", "time":"23:30", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":76, "date":"2026-06-30", "time":"04:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":77, "date":"2026-06-30", "time":"20:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":78, "date":"2026-07-1", "time":"00:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":79, "date":"2026-07-1", "time":"04:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":80, "date":"2026-07-1", "time":"19:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":81, "date":"2026-07-1", "time":"23:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":82, "date":"2026-07-2", "time":"03:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":83, "date":"2026-07-2", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":84, "date":"2026-07-3", "time":"02:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":85, "date":"2026-07-3", "time":"06:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":86, "date":"2026-07-3", "time":"21:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":87, "date":"2026-07-4", "time":"01:00", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":88, "date":"2026-07-4", "time":"04:30", "home":"TBA", "away":"TBA", "round":"Round of 32", "double_points": False},
    {"id":89, "date":"2026-07-4", "time":"20:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":90, "date":"2026-07-5", "time":"00:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":91, "date":"2026-07-5", "time":"23:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":92, "date":"2026-07-6", "time":"03:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":93, "date":"2026-07-6", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":94, "date":"2026-07-7", "time":"03:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":95, "date":"2026-07-7", "time":"19:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":96, "date":"2026-07-7", "time":"23:00", "home":"TBA", "away":"TBA", "round":"Round of 16", "double_points": False},
    {"id":97, "date":"2026-07-9", "time":"23:00", "home":"TBA", "away":"TBA", "round":"Puolivälierä", "double_points": False},
    {"id":98, "date":"2026-07-10", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Puolivälierä", "double_points": False},
    {"id":99, "date":"2026-07-12", "time":"00:00", "home":"TBA", "away":"TBA", "round":"Puolivälierä", "double_points": False},
    {"id":100, "date":"2026-07-12", "time":"04:00", "home":"TBA", "away":"TBA", "round":"Puolivälierä", "double_points": False},
    {"id":101, "date":"2026-07-14", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Välierä", "double_points": False},
    {"id":102, "date":"2026-07-15", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Välierä", "double_points": False},
    {"id":103, "date":"2026-07-18", "time":"00:00", "home":"TBA", "away":"TBA", "round":"Pronssiottelu", "double_points": True},
    {"id":104, "date":"2026-07-19", "time":"22:00", "home":"TBA", "away":"TBA", "round":"Finaali", "double_points": True},
]


# ====================== ERIKOISKOHTEET ======================
special_bets = [
    {"id": "zero_zero_over", "name": "Alkulohkovaiheessa pelattujen maalittomien tasapelien (0–0) kokonaismäärä", "points": 4, "type": "over_under", "options": ["Yli 5,5", "Alle 5,5"]},
    {"id": "penalties_over", "name": "Alkulohkovaiheessa tuomittujen rangaistuspotkujen kokonaismäärä", "points": 4, "type": "over_under", "options": ["Yli 23,5", "Alle 23,5"]},
    {"id": "own_goals_over", "name": "Alkulohkovaiheessa tehtyjen omien maalien kokonaismäärä", "points": 4, "type": "over_under", "options": ["Yli 5,5", "Alle 5,5"]},
    {"id": "free_kick_goals_over", "name": "Alkulohkovaiheessa tehtyjen suorien vapaapotkumaalien kokonaismäärä", "points": 4, "type": "over_under", "options": ["Yli 2,5", "Alle 2,5"]},
    {"id": "red_cards_over", "name": "Suorien punaisten korttien kokonaismäärä alkulohkovaiheessa", "points": 4, "type": "over_under", "options": ["Yli 5,5", "Alle 5,5"]},
    {"id": "total_goals_over", "name": "Kokonaismaalimäärä kaikissa alkulohko-otteluissa (72 ottelua)", "points": 4, "type": "over_under", "options": ["Yli 199,5", "Alle 199,5"]},

    {"id": "most_goals_group", "name": "Alkulohkojen maalirikkain lohko", "points": 6, "type": "group_select"},
    {"id": "least_goals_group", "name": "Alkulohkojen vähämaalisin lohko", "points": 6, "type": "group_select"},

    {"id": "highest_single_team_goals", "name": "Mikä on alkulohkovaiheen suurin yksittäinen maalimäärä, jonka YKSI joukkue tekee yhdessä ottelussa?", "points": 5, "type": "number"},
    {"id": "teams_with_9_points", "name": "Kuinka moni maa saa alkulohkojen peleissä täydet 9 pistettä?", "points": 5, "type": "number"},

    {"id": "every_team_scores", "name": "Tekeekö jokainen joukkue kisoissa vähintään yhden maalin?", "points": 3, "type": "yesno"},
    {"id": "hat_trick", "name": "Nähdäänkö alkulohkoissa hattutemppu?", "points": 3, "type": "yesno"},

    # Monivalintakohteet (kaksi maata)
    {"id": "most_goals", "name": "Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 6, "type": "select", "multi": True},
    {"id": "most_cards", "name": "Mikä maa saa alkulohkoissa eniten keltaisia kortteja?", "points": 6, "type": "select", "multi": True},
    {"id": "lowest_xg", "name": "Mikä maa luo kaikkein vähiten maaliodottamaa (xG) alkulohkojen peleissä?", "points": 6, "type": "select", "multi": True},

    {"id": "fastest_goal", "name": "Missä ajassa tehdään alkulohkopelien nopein avausmaali?", "points": 4, "type": "select", "options": ["Alle 1 min", "1–3 min", "Yli 3 min"]},
    {"id": "messi_vs_ronaldo", "name": "Kumpi tekee enemmän maaleja alkulohkojen peleissä, Messi vai Ronaldo?", "points": 4, "type": "select", "options": ["Messi", "Yhtä monta", "Ronaldo"]},

    {"id": "top_scorer", "name": "Kuka on kisojen maalikuningas (sukunimi)?", "points": 10, "type": "text"},
    {"id": "top_scorer_goals", "name": "Millä maalimäärällä maalikuninkuus voitetaan?", "points": 6, "type": "number"},
    {"id": "champion", "name": "Mikä maa voittaa mestaruuden?", "points": 10, "type": "select"},
]

# ====================== APUFUNKTIOT ======================
def get_countdown(match):
    try:
        match_time = datetime.strptime(f"{match['date']} {match['time']}", "%Y-%m-%d %H:%M")
        lock_time = match_time - timedelta(minutes=15)
        time_left = lock_time - datetime.now()
        if time_left.total_seconds() <= 0:
            return "🔴 Lukittu", False
        hours, rem = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)
        return f"⏱️ {hours}t {minutes:02d}min jäljellä", True
    except:
        return "🔴 Virhe aikataulussa", False

def calculate_match_points(pred, real, is_double=False):
    if not pred or not real:
        return 0
    p_home, p_away = pred
    r_home, r_away = real

    if p_home == r_home and p_away == r_away:
        points = 8
    elif (p_home > p_away and r_home > r_away) or (p_home < p_away and r_home < r_away) or (p_home == p_away and r_home == r_away):
        if p_home == p_away:
            points = 4
        elif abs(p_home - r_home) + abs(p_away - r_away) == 1:
            points = 6
        elif abs(p_home - r_home) == 0 or abs(p_away - r_away) == 0:
            points = 5
        else:
            points = 3
    else:
        points = 0

    return points * 2 if is_double else points

# ====================== SIVUPALKKI ======================
st.sidebar.title("🏆 MM26 - Veikkauskisa")

if st.session_state.logged_in_user:
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
    st.sidebar.success(f"**{st.session_state.logged_in_user}**")
    
    if st.sidebar.button("Kirjaudu ulos", key="logout_btn"):
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()
else:
    page = "Kirjaudu / Rekisteröidy"


if page == "Etusivu":
    st.markdown("""
    <style>
    .etusivu_text {
        text-align: center; 
        font-size: 7rem; 
        font-weight: 900;
        background: linear-gradient(90deg, #00ff9d, #4d9fff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 80px rgba(0, 255, 157, 0.6);
        margin: 50px 0 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="etusivu_text">MM26</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <p style="text-align: center; font-size: 2.6rem; font-weight: 700; 
                   color: #e0e0e0; margin-bottom: 40px; text-shadow: 0 4px 25px rgba(0,0,0,0.8);">
            Tervetuloa veikkaamaan!<br>
            
        </p>
    """, unsafe_allow_html=True)



    # ====================== KIRJAUTUMINEN / REKISTERÖITYMINEN ======================
users = load_json(USERS_FILE)

if not st.session_state.get("logged_in_user"):
    
    st.markdown("""
    <style>
    .stApp {
        background-image: url("https://i.imgur.com/r4bYzli.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(rgba(10,15,28,0.78), rgba(10,15,28,0.92));
        z-index: 0;
    }
    section[data-testid="stSidebar"] {
        background-color: #05080f !important;
        border-right: 3px solid #e0e0e0;
    }
    .stTabs [data-testid="stTabPanel"] {
        background-color: #05080f !important;
        border-radius: 16px;
        padding: 40px 35px;
        max-width: 420px !important;
        margin: 40px auto !important;
    }
    .stTextInput input {
        background-color: #0a0f1c !important;
    }
    .stButton button {
        background-color: #00ff9d !important;
        color: #0a0f1c !important;
        font-weight: 700;
        height: 52px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <h1 style="text-align: center; color: #00ff9d; margin: -20px 0 -20px 0; 
               font-size: 2.9rem; text-shadow: 0 0 60px rgba(0,255,157,0.7);">
        
    </h1>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1, 1])

    with col:
        tab1, tab2 = st.tabs(["Kirjaudu sisään", "Luo uusi tili"])

        with tab1:
            st.subheader("")
            username = st.text_input("Käyttäjänimi", key="login_user").strip()
            password = st.text_input("Salasana", type="password", key="login_pass")
            
            if st.button("Kirjaudu sisään", type="primary", use_container_width=True):
                if username in users and users[username] == hash_password(password):
                    st.session_state.logged_in_user = username
                    st.session_state.is_admin = (username.lower() == "admin")
                    st.success(f"Tervetuloa takaisin, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Väärä käyttäjänimi tai salasana")

        with tab2:
            st.subheader("")
            new_user = st.text_input("Käyttäjänimi", key="reg_user").strip()
            new_pass = st.text_input("Salasana", type="password", key="reg_pass")
            new_pass2 = st.text_input("Toista salasana", type="password", key="reg_pass2")
            
            if st.button("Rekisteröidy", type="primary", use_container_width=True):
                if not new_user or not new_pass:
                    st.error("Käyttäjänimi ja salasana ovat pakollisia")
                elif new_pass != new_pass2:
                    st.error("Salasanat eivät täsmää")
                elif new_user in users:
                    st.error(f"❌ Käyttäjänimi '{new_user}' on jo käytössä")
                else:
                    users[new_user] = hash_password(new_pass)
                    save_json(USERS_FILE, users)
                    st.success(f"Tili '{new_user}' luotu onnistuneesti, voit kirjautua sisään!")
                    
                    
                    # EI st.rerun() täällä




# ====================== SÄÄNNÖT ======================
if page == "Säännöt":
    st.title("Säännöt ja pisteytysjärjestelmä")
    st.markdown("---")
    
    st.subheader("Otteluveikkaukset")
    st.markdown("""
    Veikkauskohteista saa pisteitä vain, jos veikattu tulos (1X2) on oikein. Lopullinen pistemäärä määrittyy sen mukaisesti, kuinka lähelle oikeaa tulosta olet veikannut. 
Jokaisessa lohkossa on yksi tuplapisteet antava ottelu (yhteensä siis 12 kpl), joka on kaikille veikkaajille sama. Veikkauskohde sulkeutuu aina 15 minuuttia ennen ottelun alkua, siihen asti veikkausta voi käydä vaihtamassa vapaasti. Tuorein veikkaus näkyy veikkauskohteen kohdalla ja päivittyy aina Omat veikkaukset- valikkoon. Pisteet veikkauksista tulevat alla olevan taulukon mukaisesti. 
    """)
    
    # Tyylikäs pistetaulukko
    data = {
        "Veikkauksesi": [
            "Täysin oikein",
            "Oikea voittaja + yhden joukkueen maalit oikein ja toisen vain yhdellä pielessä",
            "Oikea voittaja + yhden joukkueen maalit oikein ja toisen yli yhdellä pielessä",
            "Tasapeli oikein, mutta maalit väärin",
            "Vain oikea voittaja, molempien joukkueiden maalit väärin",
            "Väärä 1X2"
        ],
        "Pisteet": ["**8**", "**6**", "**5**", "**4**", "**3**", "**0**"]
    }
    
    df = pd.DataFrame(data)
    st.table(df.style.set_properties(**{
        'text-align': 'left',
        'font-size': '1.05rem',
        'padding': '14px 20px'
    }).set_table_styles([
        {'selector': 'thead th', 'props': [('background-color', '#1e2a44'), ('color', '#00ff9d'), ('font-size', '1.5rem')]}
    ]))
    
    st.markdown("---")
    
    st.subheader("Erikoiskohteet")
    st.markdown("""
    Erikoiskohteilla on omat kiinteät pistemääränsä, jotka näkyvät veikkausta tehtäessä. Erikoiskohteissa on kolme kohdetta, joihin voit valita kaksi veikkausta ja joista kumpi tahansa veikkaus osuessaan antaa kohteesta pisteet. Erikoiskohteet sulkeutuvat kaikki samanaikaisesti 15 minuuttia ennen ensimmäisen ottelun alkua, jonka jälkeen veikkaaminen ei ole enää mahdollista. Jos veikkauskohteessa on lopulta useampi eri vaihtoehto oikein, kaikista saa luonnollisesti pisteet samanarvoisesti. 
    
    """)
    
    st.info("MUISTA VEIKATA KAIKKI ERIKOISKOHTEET ENNEN AVAUSPELIN ALKAMISTA!")
    
    st.markdown("---")
    st.caption("Pisteet päivittyvät automaattisesti tulosten kirjaamisen jälkeen.")


# ====================== VEIKKAA ERIKOISKOHTEITA ======================
if page == "Veikkaa erikoiskohteita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        real_special = real_results.get("special", {})
        
        # Tarkistetaan sulkeutuminen
        if matches:
            _, special_open = get_countdown(matches[0])
        else:
            special_open = True
        
        if real_special or not special_open:
            st.success("✅ Erikoiskohteet ovat lukittu.")
            st.info("Erikoiskohteiden veikkaus sulkeutui 15 minuuttia ennen turnauksen avausottelua.")
        else:

            

            user_special = predictions.get(user, {}).get("special", {})
            
            for bet in special_bets:
                bet_id = bet["id"]
                current_pred = user_special.get(bet_id)
                
                st.markdown(f"**{bet['name']}**")
                st.markdown(f"<span style='color:#00ff9d;'>**({bet.get('points', 5)} pistettä)**</span>", unsafe_allow_html=True)

                # Statuslaatikko (vihreä kun veikattu)
                status_cols = st.columns([4.2, 1.1])
                with status_cols[1]:
                    if current_pred:
                        st.markdown(f"""
                            <div style="background-color: #00cc7a; color: #0a0f1c; 
                                        padding: 8px 14px; border-radius: 6px; 
                                        font-weight: 700; font-size: 1.25rem; 
                                        text-align: center;">
                                {current_pred}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div style="background-color: #334466; color: #aaaaaa; 
                                        padding: 8px 14px; border-radius: 6px; 
                                        font-weight: 500; text-align: center;">
                                —
                            </div>
                        """, unsafe_allow_html=True)

                # Syöttökenttä
                input_cols = st.columns([0.1, 0.8, 2.3])
                with input_cols[1]:
                    if bet.get("multi") is True:
                        selected = st.multiselect("Valitse kaksi maata", 
                                                countries, 
                                                default=[x.strip() for x in str(current_pred).split(",")] if current_pred else [],
                                                key=f"spec_{bet_id}",
                                                max_selections=2)
                        value = ", ".join(selected)
                    elif bet.get("options"):
                        value = st.radio("", bet["options"], horizontal=True, key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet.get("type") == "yesno":
                        value = st.radio("", ["Kyllä", "Ei"], horizontal=True, key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet.get("type") == "group_select":
                        value = st.selectbox("", ["A","B","C","D","E","F","G","H","I","J","K","L"], key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet.get("type") == "number":
                        default = int(current_pred) if current_pred and str(current_pred).isdigit() else 0
                        value = st.number_input("", min_value=0, max_value=50, value=default, key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet.get("type") == "text":
                        value = st.text_input("", value=current_pred or "", key=f"spec_{bet_id}", label_visibility="collapsed")
                    else:
                        value = st.selectbox("", countries, key=f"spec_{bet_id}", label_visibility="collapsed")
                
                # Tallennusnappi
                btn_cols = st.columns([0.2, 1.8, 5.05])
                with btn_cols[1]:
                    btn_text = "Päivitä veikkaus" if current_pred else "Tallenna"
                    if st.button(btn_text, key=f"save_spec_{bet_id}", use_container_width=True):
                        if user not in predictions:
                            predictions[user] = {}
                        if "special" not in predictions[user]:
                            predictions[user]["special"] = {}
                        predictions[user]["special"][bet_id] = str(value).strip()
                        save_json(PREDICTIONS_FILE, predictions)
                        st.success("✅ Veikkaus tallennettu!")
                        st.rerun()
                
                st.divider()   # Selkeä erotinviiva kohteiden väliin

# ====================== VEIKKAA OTTELUITA ======================
if page == "Veikkaa otteluita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        user_preds = predictions.get(user, {})
        
        open_matches = []
        for m in matches:
            match_id = str(m['id'])
            if match_id in real_results.get("matches", {}):
                continue
            _, is_open = get_countdown(m)
            if is_open:
                open_matches.append(m)
        
        if not open_matches:
            st.success("✅ Tällä hetkellä ei ole avoimia veikkauskohteita.")
        else:
            st.caption(f"Avoimia otteluita: {len(open_matches)}")
            
            for m in open_matches:
                match_id = str(m['id'])
                is_double = m.get("double_points", False)
                current_pred = user_preds.get(match_id)  # [home, away] tai None
                
                countdown_str, is_open = get_countdown(m)
                match_date = datetime.strptime(m['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
                
                if is_double:
                    st.markdown("""
                        <div style="background: linear-gradient(90deg, #2a1f0f, #3a2a10); 
                                    border: 2px solid #ffcc00; border-radius: 8px; 
                                    padding: 2px 10px; margin: 16px 0px; display: inline-block;">
                            <span style="color:#ffcc00; font-weight:600;"> Veikkauskohteesta tuplapisteet </span>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"**{m['home']} — {m['away']}**  ({m.get('group', '')})")
                
                # Aikarivi
                st.markdown(f"""
                    <div style="background-color: #1e2a44; padding: 10px 15px; border-radius: 10px; 
                                border-left: 4px solid #00ff9d; margin: 8px 0;">
                        <span style="color: #00ff9d; font-weight: 600;">
                             {match_date} klo {m['time']}
                        </span>
                        <span style="margin-left: 50px; color: #ffd700; font-weight: 500;">
                            {countdown_str}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                # ✅ PIENI VIHREÄ LAATIKKO - vain tulos
                col_status = st.columns([4.5, 0.8])
                with col_status[1]:
                    if current_pred:
                        st.markdown(f"""
                            <div style="background-color: #00cc7a; color: #0a0f1c; 
                                        padding: 8px 14px; border-radius: 12px; 
                                        font-weight: 700; font-size: 1.35rem; 
                                        text-align: center;">
                                {current_pred[0]}–{current_pred[1]}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div style="background-color: #334466; color: #aaaaaa; 
                                        padding: 8px 14px; border-radius: 6px; 
                                        font-weight: 500; text-align: center;">
                                —
                            </div>
                        """, unsafe_allow_html=True)

                # Maal syötteet
                score_cols = st.columns([2.2, 1.1, 1.1, 2.2])
                with score_cols[0]:
                    st.markdown("")
                with score_cols[1]:
                    home_score = st.number_input(
                        "", 
                        min_value=0, 
                        max_value=15, 
                        value=current_pred[0] if current_pred else 0,
                        key=f"h_{match_id}", 
                        label_visibility="collapsed"
                    )
                with score_cols[2]:
                    away_score = st.number_input(
                        "", 
                        min_value=0, 
                        max_value=15, 
                        value=current_pred[1] if current_pred else 0,
                        key=f"a_{match_id}", 
                        label_visibility="collapsed"
                    )
                with score_cols[3]:
                    st.markdown("")

                # Tallennusnappi
                btn_cols = st.columns([3.3, 2.4, 3.3])
                with btn_cols[1]:
                    btn_text = "Päivitä veikkaus" if current_pred else "Tallenna"
                    if st.button(btn_text, key=f"save_match_{match_id}", use_container_width=True):
                        if user not in predictions:
                            predictions[user] = {}
                        predictions[user][match_id] = [home_score, away_score]
                        save_json(PREDICTIONS_FILE, predictions)
                        st.success(f"✅ Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                        st.rerun()
                
                st.divider()

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"Omat veikkaukset")
        
        tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
        
        # ====================== OTTELUVEIKKAUKSET ======================
        with tab1:
            st.caption("")
            for m in matches:
                match_id = str(m['id'])
                pred = predictions.get(user, {}).get(match_id)
                real = real_results.get("matches", {}).get(match_id)
                is_double = m.get("double_points", False)
                
                st.markdown(f"**{m['home']} — {m['away']}**  ({m.get('group', '')})")
                
                
                
                cols = st.columns([0.4, 0.2, 0.2, 1.0])
                with cols[0]:
                    if pred:
                        st.write(f"Oma veikkaus: **{pred[0]}–{pred[1]}**")
                    else:
                        st.write("Ei veikkausta")
                
                with cols[1]:
                    if real:
                        st.success(f"Tulos: **{real[0]}–{real[1]}**")
                
                with cols[2]:
                    if real and pred:
                        pts = calculate_match_points(pred, real, is_double)
                        st.markdown(f"""
                            <div style="background-color: #00cc7a; color: #0a0f1c; 
                                        padding: 15px 12px; border-radius: 6px; 
                                        font-weight: 700; text-align: center;">
                                +{pts}
                            </div>
                        """, unsafe_allow_html=True)
                    elif real:
                        st.markdown(f"""
                            <div style="background-color: #334466; color: #aaaaaa; 
                                        padding: 8px 12px; border-radius: 6px; 
                                        text-align: center;">
                                +0
                            </div>
                        """, unsafe_allow_html=True)
                
                if is_double:
                    st.caption("★ Tuplapisteet")
                
                st.divider()

        # ====================== ERIKOISKOHTEET ======================
        with tab2:
            st.caption("")
            user_special = predictions.get(user, {}).get("special", {})
            real_special = real_results.get("special", {})
            
            for bet in special_bets:
                pred_value = user_special.get(bet["id"])
                real_value = real_special.get(bet["id"])
                
                st.markdown(f"**{bet['name']}**")
                
                
                cols = st.columns([0.6, 0.6, 0.3, 1.2])
                with cols[0]:
                    if pred_value:
                        st.write(f"Oma veikkaus: **{pred_value}**")
                    else:
                        st.write("Ei veikkausta")
                
                with cols[1]:
                    if real_value:
                        st.success(f"Toteutunut: **{real_value}**")
                
                with cols[2]:
                    if real_value and pred_value:
                        points = 0
                        pred_str = str(pred_value).strip().lower()
                        real_str = str(real_value).strip().lower()
                        
                        if bet.get("multi") is True:
                            pred_list = [x.strip().lower() for x in pred_str.split(",")]
                            real_list = [x.strip().lower() for x in real_str.split(",")]
                            if any(p in real_list for p in pred_list):
                                points = bet.get("points", 0)
                        else:
                            if pred_str == real_str or pred_str in real_str or real_str in pred_str:
                                points = bet.get("points", 0)
                        
                        if points > 0:
                            st.markdown(f"""
                                <div style="background-color: #00cc7a; color: #0a0f1c; 
                                            padding: 15px 16px; border-radius: 8px; 
                                            font-weight: 700; text-align: center;">
                                    +{points}
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div style="background-color: #00cc7a; color: #0a0f1c; 
                                            padding: 15px 16px; border-radius: 8px; 
                                            font-weight: 700; text-align: center;">
                                    +0
                                </div>
                            """, unsafe_allow_html=True)
                
                st.divider()

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.subheader("VEIKKAUSTILANNE")
    
    leaderboard = []
    for username in users.keys():
        user_pred = predictions.get(username, {})
        total = 0
        for m in matches:
            pred = user_pred.get(str(m['id']))
            real = real_results.get("matches", {}).get(str(m['id']))
            if pred and real:
                total += calculate_match_points(pred, real, m.get("double_points", False))
        
        user_special = user_pred.get("special", {})
        real_special = real_results.get("special", {})
        for bet in special_bets:
            pred_val = user_special.get(bet["id"])
            real_val = real_special.get(bet["id"])
            if pred_val and real_val:
                pred_str = str(pred_val).strip().lower()
                real_str = str(real_val).strip().lower()
                if bet.get("multi") is True:
                    pred_list = [x.strip().lower() for x in pred_str.split(",")]
                    real_list = [x.strip().lower() for x in real_str.split(",")]
                    if any(p in real_list for p in pred_list):
                        total += bet.get("points", 0)
                elif pred_str == real_str or pred_str in real_str or real_str in pred_str:
                    total += bet.get("points", 0)
        
        manual_points = sum(c["points"] for c in real_results.get("manual_corrections", {}).get(username, []))
        total += manual_points
        leaderboard.append({"Nimi": username, "Pisteet": total, "Manuaaliset": manual_points})
    
    leaderboard.sort(key=lambda x: x["Pisteet"], reverse=True)

    st.caption(f"Otteluveikkaukset: {len(real_results.get('matches', {}))}/{len(matches)}  |  "
               f"Erikoiskohteet: {len(real_results.get('special', {}))}/{len(special_bets)}")
    st.subheader("")
    for i, entry in enumerate(leaderboard, 1):
        cols = st.columns([0.3, 0.8, 3.4])
        with cols[0]:
            st.markdown(f"<h3 style='margin:8px 0 0 0;'>{i}.</h3>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"<h3 style='margin:8px 0 0 0;'>{entry['Nimi']}</h3>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<div style='text-align:left; font-size:2.6rem; font-weight:700; color:#00ff9d;'>{entry['Pisteet']}</div>", unsafe_allow_html=True)
        if entry.get('Manuaaliset', 0) != 0:
            sign = "+" if entry['Manuaaliset'] > 0 else ""
            st.caption(f"Manuaalikorjaus: {sign}{entry['Manuaaliset']} pistettä")
        st.divider()

# ====================== KOMMENTTIKENTTÄ ======================
    st.subheader("")
    st.subheader("📣 Ajatuksia? Sana on vapaa!")
    st.subheader("")

    COMMENTS_FILE = "comments.json"
    comments = load_json(COMMENTS_FILE, default=[])

    comments_per_page = 6
    total_pages = (len(comments) + comments_per_page - 1) // comments_per_page

    # Tuoreimmat kommentit ensin
    if total_pages > 0:
        current_page = st.session_state.get("comment_page", 1)
    else:
        current_page = 1

    # Kommentit ensin (näytetään ennen sivunvaihtoa)
    start_idx = (current_page - 1) * comments_per_page
    end_idx = start_idx + comments_per_page
    displayed_comments = list(reversed(comments))[start_idx:end_idx]

    if displayed_comments:
        for i, c in enumerate(displayed_comments):
            global_idx = len(comments) - 1 - (start_idx + i)
            is_own = c['user'] == st.session_state.logged_in_user
            with st.container():
                col1, col2 = st.columns([3, 3])
                with col1:
                    st.markdown(f"""
                        <div style="background-color: #1e2a44; padding: 24px 24px; border-radius: 24px; 
                                    margin-bottom: 22px; border-left: 14px solid #00ff9d;">
                            <strong>{c['user']}</strong> 
                            <span style="color:#888; font-size:0.9rem;">{c['time']}</span><br>
                            {c['text']}
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if is_own and st.button("✏️", key=f"edit_{global_idx}"):
                        st.session_state.editing_comment = global_idx
                        st.rerun()
    else:
        st.info("Ei vielä kommentteja. Ole ensimmäinen!")

    # Sivunvaihtolaatikko KOMMENTTIEN ALLE
    if total_pages > 1:
        st.markdown("<div style='text-align: center; margin: 20px 0 10px 0;'>", unsafe_allow_html=True)
        current_page = st.number_input("Sivu", min_value=1, max_value=total_pages, 
                                     value=current_page, step=1, key="comment_page", 
                                     label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption(f"**Sivu {current_page} / {total_pages}**")

    # Muokkaus + uusi kommentti
    if st.session_state.get("editing_comment") is not None:
        idx = st.session_state.editing_comment
        old = comments[idx]
        st.write("**Muokkaa kommenttiasi:**")
        new_text = st.text_area("Kommentti", value=old['text'], height=120, key="edit_text")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Tallenna muutokset", type="primary"):
                if new_text.strip():
                    comments[idx]['text'] = new_text.strip()
                    comments[idx]['edited'] = datetime.now().strftime("%d.%m. %H:%M")
                    save_json(COMMENTS_FILE, comments)
                    st.success("✅ Kommentti päivitetty!")
                    st.session_state.editing_comment = None
                    st.rerun()
        with c2:
            if st.button("Peruuta", type="secondary"):
                st.session_state.editing_comment = None
                st.rerun()

    st.divider()
    if st.session_state.logged_in_user:
        with st.form("comment_form", clear_on_submit=True):
            new_comment = st.text_area("Kommenttisi...", height=140, placeholder="Anna palaa.... 🔥", max_chars=600)
            if st.form_submit_button(" 💥 Julkaise kommenttisi 💥", use_container_width=True) and new_comment.strip():
                comments.append({
                    "user": st.session_state.logged_in_user,
                    "text": new_comment.strip(),
                    "time": datetime.now().strftime("%d.%m. %H:%M")
                })
                save_json(COMMENTS_FILE, comments)
                st.success("✅ Kommentti julkaistu!")
                st.rerun()
    else:
        st.warning("Kirjaudu sisään kirjoittaaksesi kommentteja.")    

# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("Kaikkien veikkaukset")
    st.caption("Täällä näet muiden pelaajien veikkaukset heti kun kohde on sulkeutunut.")
    
    tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
    
    # ====================== OTTELUT ======================
    with tab1:
        for m in matches:
            match_id = str(m['id'])
            real = real_results.get("matches", {}).get(match_id)
            is_double = m.get("double_points", False)
            
            # Näytetään jos ottelu on sulkeutunut (tai tulos on jo)
            _, is_open = get_countdown(m)
            if is_open and not real:
                continue  # Ei vielä sulkeutunut → ei näytetä
                
            st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')})")
            
            if real:
                st.success(f"Tulos: **{real[0]}–{real[1]}**")
            else:
                st.info("Ottelu on sulkeutunut – tulos odottaa")
            
            for u in sorted(users.keys()):
                pred = predictions.get(u, {}).get(match_id)
                if pred:
                    if real:
                        pts = calculate_match_points(pred, real, is_double)
                        st.write(f"**{u}**: {pred[0]}–{pred[1]}")
                    else:
                        st.write(f"**{u}**: {pred[0]}–{pred[1]}")
            
            st.divider()

    # ====================== ERIKOISKOHTEET ======================
    with tab2:
        for bet in special_bets:
            bet_id = bet["id"]
            real_val = real_results.get("special", {}).get(bet_id)
            
            # Näytetään jos erikoiskohde on sulkeutunut
            _, special_open = get_countdown(matches[0]) if matches else (None, False)
            
            if special_open and not real_val:
                continue  # Ei vielä sulkeutunut
            
            st.markdown(f"**{bet['name']}**")
            
            if real_val:
                st.success(f"Toteutunut: **{real_val}**")
            else:
                st.info("Kohde on sulkeutunut – tulos odottaa")
            
            for u in sorted(users.keys()):
                user_pred = predictions.get(u, {}).get("special", {}).get(bet_id)
                if user_pred:
                    if real_val:
                        # Pisteytys
                        if bet.get("multi") is True:
                            pred_list = [x.strip().lower() for x in str(user_pred).split(",")]
                            real_list = [x.strip().lower() for x in str(real_val).split(",")]
                            pts = bet.get("points", 0) if any(p in real_list for p in pred_list) else 0
                        else:
                            pts = bet.get("points", 0) if str(user_pred).strip().lower() == str(real_val).strip().lower() else 0
                        
                        st.write(f"**{u}**: {user_pred} {'→ **+' + str(pts) + 'p**' if pts > 0 else ''}")
                    else:
                        st.write(f"**{u}**: {user_pred}")
            
            st.divider()
   
# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("")
    
    ADMIN_PASSWORD = "haamuhanska2026"  # ← VAIHDA TÄHÄN TURVALLISEEN SALASANAAN!
    
    if not st.session_state.get("is_admin", False):
        pw = st.text_input("Syötä admin-salasana", type="password", key="admin_login")
        if st.button("Kirjaudu adminiksi"):
            if pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("✅ Admin-oikeudet myönnetty")
                st.rerun()
            else:
                st.error("❌ Väärä salasana")
        st.stop()
    
    st.success("✅ Olet admin-tilassa")
    
    admin_tab = st.radio("", 
                        ["Ottelujen tulokset", 
                         "Erikoiskohteiden tulokset", 
                         "Manuaalinen pistekorjaus",
                         "Pelaajien hallinta",
                         "Varmuuskopiointi"], 
                        horizontal=True)

    # ====================== OTTELUJEN TULOKSET ======================
    if admin_tab == "Ottelujen tulokset":
        st.write("###")
        for m in matches:
            match_id = str(m['id'])
            current_real = real_results.get("matches", {}).get(match_id)
            
            col1, col2, col3, col4 = st.columns([1, 0.4, 0.4, 1.2])
            with col1:
                st.write(f"**{m['home']} — {m['away']}**")
            with col2:
                h = st.number_input("", 0, 20, value=current_real[0] if current_real else 0, 
                                  key=f"ah_{match_id}")
            with col3:
                a = st.number_input("", 0, 20, value=current_real[1] if current_real else 0, 
                                  key=f"aa_{match_id}")
            with col4:
                if st.button("Tallenna", key=f"save_{match_id}"):
                    if "matches" not in real_results:
                        real_results["matches"] = {}
                    real_results["matches"][match_id] = [h, a]
                    save_json(RESULTS_FILE, real_results)
                    st.success(f"Tallennettu: {m['home']} {h}–{a} {m['away']}")
                    st.rerun()
                
                if current_real and st.button("Poista", key=f"del_{match_id}"):
                    real_results["matches"].pop(match_id, None)
                    save_json(RESULTS_FILE, real_results)
                    st.success("Tulos poistettu")
                    st.rerun()
            st.divider()

    # ====================== ERIKOISKOHTEIDEN TULOKSET ======================
    elif admin_tab == "Erikoiskohteiden tulokset":
        st.write("###  ")
        for bet in special_bets:
            bet_id = bet["id"]
            current = real_results.get("special", {}).get(bet_id)
            
            st.write(f"**{bet['name']}**")
            new_val = st.text_input("Oikea tulos", value=current or "", key=f"e_{bet_id}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Tallenna", key=f"esave_{bet_id}"):
                    if "special" not in real_results:
                        real_results["special"] = {}
                    real_results["special"][bet_id] = new_val.strip()
                    save_json(RESULTS_FILE, real_results)
                    st.success("Tallennettu!")
                    st.rerun()
            with col2:
                if current and st.button("Poista", key=f"edel_{bet_id}"):
                    real_results.get("special", {}).pop(bet_id, None)
                    save_json(RESULTS_FILE, real_results)
                    st.success("Poistettu")
                    st.rerun()
            st.divider()

    # ====================== MANUAALINEN PISTEKORJAUS (PÄIVITETTY) ======================
    elif admin_tab == "Manuaalinen pistekorjaus":
        st.write("###")
        st.caption("Korjaa pelaajan pistemäärä")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_user = st.selectbox("", options=list(users.keys()), key="manual_user")
        with col2:
            points = st.number_input("", value=0, step=1, key="manual_points")
        
        reason = st.text_area("(Syy korjaukselle)", 
                            placeholder="esim. Bugi tai tekninen virhe", 
                            key="manual_reason", height=80)
        
        if st.button("Tallenna", type="primary", use_container_width=True):
            if not reason or reason.strip() == "":
                st.error("Anna syy pistekorjaukselle!")
            else:
                if "manual_corrections" not in real_results:
                    real_results["manual_corrections"] = {}
                if selected_user not in real_results["manual_corrections"]:
                    real_results["manual_corrections"][selected_user] = []
                
                correction = {
                    "points": int(points),
                    "reason": reason.strip(),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                real_results["manual_corrections"][selected_user].append(correction)
                save_json(RESULTS_FILE, real_results)
                
                sign = "+" if points >= 0 else ""
                st.success(f"✅ {sign}{points} pistettä lisätty pelaajalle **{selected_user}**")
                st.rerun()

        # ====================== LOKIKIRJA ======================
        st.divider()
        st.write("### Tehdyt pistekorjaukset")
        
        corrections = real_results.get("manual_corrections", {})
        if corrections:
            for user in sorted(corrections.keys()):
                user_corrections = corrections[user]
                if user_corrections:
                    with st.expander(f"**{user}** — {len(user_corrections)} korjausta", expanded=True):
                        for c in reversed(user_corrections):   # uusimmat ensin
                            sign = "+" if c["points"] >= 0 else ""
                            st.write(f"**{sign}{c['points']} p** | {c['timestamp']} | {c['reason']}")
        else:
            st.info("Ei vielä yhtään pistekorjausta.")

       # ====================== PELAAJIEN HALLINTA ======================
    elif admin_tab == "Pelaajien hallinta":
        st.write("")
        st.caption("Poista pelaaja veikkauskisasta")
        
        selected_user = st.selectbox("", 
                                   options=list(users.keys()), 
                                   key="delete_user_select")
        
        # Vahvistus checkbox aina näkyvissä
        confirm = st.checkbox(f"Olen varma, että haluan poistaa pelaajan **{selected_user}** ", 
                             key="confirm_delete")
        
        if st.button("Poista pelaaja", type="primary", use_container_width=True):
            if confirm:
                # Poistetaan pelaaja
                if selected_user in users:
                    del users[selected_user]
                if selected_user in predictions:
                    del predictions[selected_user]
                if real_results.get("manual_corrections") and selected_user in real_results["manual_corrections"]:
                    del real_results["manual_corrections"][selected_user]
                
                save_json(USERS_FILE, users)
                save_json(PREDICTIONS_FILE, predictions)
                save_json(RESULTS_FILE, real_results)
                
                st.success(f"✅ Pelaaja **{selected_user}** on poistettu kokonaan!")
                st.rerun()
            else:
                st.error("Et rastittanut vahvistusruutua. Poistoa ei suoritettu.")
        
        st.divider()
        st.write("#### Nykyiset pelaajat")
        for user in sorted(users.keys()):
            st.write(f"• **{user}**")

    # ====================== VARMUUSKOPIOINTI ======================
    else:
        st.write("### ")
        st.info("Varmuuskopio tallentuu **sinun omalle koneellesi**. Tarvittaessa käyttäkää kopiota pisteiden lisäämiseen manuaalisesti.")
        
        st.write("")
        if st.button("Lataa kopio kaikkien veikkauksista", type="primary", use_container_width=True):
            backup = {
                "users": users,
                "predictions": predictions,
                "real_results": real_results,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.download_button(
                label="📥 Lataa backup.json",
                data=json.dumps(backup, ensure_ascii=False, indent=2),
                file_name=f"mm26_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.divider()
        st.write("#### Palauta varmuuskopio")
        uploaded = st.file_uploader("", type="json")
        if uploaded is not None:
            if st.button("⚠️ Korvaa kaikki tiedostot tällä varmuuskopiolla", type="primary", use_container_width=True):
                try:
                    backup_data = json.load(uploaded)
                    users.clear()
                    users.update(backup_data.get("users", {}))
                    predictions.clear()
                    predictions.update(backup_data.get("predictions", {}))
                    real_results.clear()
                    real_results.update(backup_data.get("real_results", {}))
                    
                    save_json(USERS_FILE, users)
                    save_json(PREDICTIONS_FILE, predictions)
                    save_json(RESULTS_FILE, real_results)
                    st.success("✅ Varmuuskopio palautettu onnistuneesti!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Virhe palautuksessa: {e}")