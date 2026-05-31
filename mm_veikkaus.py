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

# ====================== TYYLITTELY ======================
st.markdown("""
<style>
    .stApp { background-color: #0a0f1c; color: #e0e0e0; }
    h1 { color: #00ff9d; font-weight: 700; letter-spacing: -0.02em; }
    h2, h3 { color: #ffffff; font-weight: 600; }
    section[data-testid="stSidebar"] { background-color: #0f1629; border-right: 1px solid #1e2a44; }
    .stButton button { 
        background-color: #00ff9d; color: #0a0f1c; font-weight: 700; 
        border-radius: 8px; height: 48px; transition: all 0.3s;
    }
    .stButton button:hover { background-color: #00cc7a; transform: translateY(-2px); }
    .etusivu_text {
        text-align: center; font-size: 6.5rem; font-weight: 900;
        background: linear-gradient(90deg, #00ff9d, #4d9fff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 60px 0 20px 0; text-shadow: 0 0 60px rgba(0, 255, 157, 0.5);
    }
    @media (max-width: 768px) {
        .etusivu_text { font-size: 3.8rem; margin: 40px 0 15px 0; }
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
    *[{"id": f"group_{letter.lower()}", "name": f"Lohko {letter} voittaja", "points": 3, "type": "select"} for letter in "ABCDEFGHIJKL"],
    {"id": "most_goals_group", "name": "Missä lohkossa tehdään yhteensä eniten maaleja?", "points": 5, "type": "group_select"},
    {"id": "total_penalties", "name": "Kuinka monta rangaistuspotkua alkulohkoissa tuomitaan yhteensä?", "points": 3, "type": "penalty_range"},
    {"id": "lowest_xg", "name": "Mikä maa luo vähiten maaliodottamaa (xG) alkulohkojen peleissä?", "points": 5, "type": "select"},
    {"id": "ronaldo_goals", "name": "Monta maalia Cristiano Ronaldo tekee alkulohkojen peleissä?", "points": 3, "type": "number"},
    {"id": "goal_first_minute", "name": "Tehdäänkö alkulohkojen yhdessäkään ottelussa maalia ensimmäisen peliminuutin aikana?", "points": 3, "type": "yesno"},
    {"id": "own_goals_5plus", "name": "Tehdäänkö alkulohkojen peleissä vähintään kuusi omaa maalia?", "points": 3, "type": "yesno"},
    {"id": "zero_zero_5plus", "name": "Päättyykö alkulohkojen peleistä vähintään kuusi ottelua 0-0?", "points": 3, "type": "yesno"},
    {"id": "red_cards_5plus", "name": "Kirjataanko alkulohkojen peleissä vähintään kuusi suoraa punaista korttia?", "points": 3, "type": "yesno"},
    {"id": "free_kick_goal", "name": "Tehdäänkö alkulohkojen otteluissa vähintään kolme maalia suoraan vapaapotkusta?", "points": 3, "type": "yesno"},
    {"id": "hat_trick", "name": "Nähdäänkö alkulohkojen peleissä hattutemppu?", "points": 3, "type": "yesno"},
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
        return f"⏳ {hours}t {minutes:02d}min jäljellä", True
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
st.sidebar.title("⚽ MM26 - Veikkauskisa")

if st.session_state.logged_in_user:
    page = st.sidebar.selectbox(
        "Valikko",
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
    st.sidebar.success(f"Käyttäjä: **{st.session_state.logged_in_user}**")
    
    if st.sidebar.button("Kirjaudu ulos", key="logout_btn"):
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()
else:
    page = "Kirjaudu / Rekisteröidy"

# ====================== ETUSIVU ======================
if page == "Etusivu":
    st.markdown('<div class="etusivu_text">MM26</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 2.8rem; font-weight: 700; color: #e0e0e0; margin-bottom: 60px;">Tervetuloa veikkaamaan ja onnea matkaan!</p>', unsafe_allow_html=True)

# ====================== KIRJAUDU / REKISTERÖIDY ======================
if page == "Kirjaudu / Rekisteröidy":
    if st.session_state.logged_in_user:
        st.success(f"Olet kirjautuneena nimellä: **{st.session_state.logged_in_user}**")
        if st.button("Kirjaudu ulos"):
            st.session_state.logged_in_user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Kirjaudu sisään", "Luo uusi tunnus"])
        
        with tab1:
            st.subheader("Kirjaudu sisään")
            col = st.columns([1, 2, 1])[1]
            with col:
                username = st.text_input("Käyttäjänimi", key="login_user")
                password = st.text_input("Salasana", type="password", key="login_pass")
                
                if st.button("Kirjaudu sisään", type="primary", use_container_width=True):
                    if username in users and users[username] == hash_password(password):
                        st.session_state.logged_in_user = username
                        st.success("✅ Kirjautuminen onnistui!")
                        st.rerun()
                    else:
                        st.error("❌ Väärä käyttäjänimi tai salasana")
        
        with tab2:
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
                        st.success("✅ Tunnus luotu! Voit nyt kirjautua sisään.")

# ====================== SÄÄNNÖT ======================
if page == "Säännöt":
    st.title("Säännöt ja pisteytysjärjestelmä")
    st.markdown("---")
    
    st.subheader("Otteluveikkaukset")
    st.markdown("""
    **Pisteet ottelusta:**
    - Täysin oikea tulos → **8 pistettä**
    - Oikea voittaja + yksi maali oikein → **6 pistettä**
    - Oikea voittaja + molemmat maalit oikein (mutta ero >1) → **5 pistettä**
    - Oikea tasapeli (maalit väärin) → **4 pistettä**
    - Vain oikea voittaja → **3 pistettä**
    - Väärä 1X2 → **0 pistettä**
    
    Lohkoissa on merkitty tuplapiste-otteluita (×2).
    """)
    
    st.markdown("---")
    st.subheader("Erikoiskohteet")
    st.write("Erikoiskohteilla on omat pistemääränsä (3–10 pistettä). Pisteet tulevat näkyviin kun tulos on syötetty admin-paneelissa.")
    
    st.caption("Erikoiskohteet sulkeutuvat 15 minuuttia ennen ensimmäistä ottelua.")


# ====================== VEIKKAA OTTELUITA ======================
if page == "Veikkaa otteluita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader("⚽ Veikkaa otteluita")
        
        # Avoimet ottelut (ei vielä tulosta)
        open_matches = [m for m in matches if str(m['id']) not in real_results.get("matches", {})]
        
        if not open_matches:
            st.success("✅ Kaikki ottelut ovat jo lukittu tai pelattu.")
        else:
            for m in open_matches:
                match_id = str(m['id'])
                is_double = m.get("double_points", False)
                countdown_str, is_open = get_countdown(m)
                
                # Tuplapiste korostus
                if is_double:
                    st.markdown("""
                        <div style="background: linear-gradient(90deg, #2a1f0f, #3a2a10); border: 2px solid #ffcc00; 
                        border-radius: 12px; padding: 12px 15px; margin: 12px 0;">
                        <span style="color:#ffcc00; font-weight:700;">🔥 TUPLAPISTEET ×2</span>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"**{m['home']} — {m['away']}**  ({m.get('group', '')})")
                st.markdown(countdown_str)
                
                col1, col2 = st.columns(2)
                with col1:
                    home_score = st.number_input("Kotimaalit", min_value=0, max_value=15, value=0, 
                                               key=f"h_{match_id}")
                with col2:
                    away_score = st.number_input("Vierasmaalit", min_value=0, max_value=15, value=0, 
                                               key=f"a_{match_id}")
                
                if st.button("Tallenna veikkaus", key=f"save_match_{match_id}", use_container_width=True):
                    if user not in predictions:
                        predictions[user] = {}
                    predictions[user][match_id] = [home_score, away_score]
                    save_json(PREDICTIONS_FILE, predictions)
                    st.success(f"✅ Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                
                if is_double:
                    st.markdown("</div>", unsafe_allow_html=True)
                st.divider()


# ====================== VEIKKAA ERIKOISKOHTEITA ======================
if page == "Veikkaa erikoiskohteita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        real_special = real_results.get("special", {})
        
        if real_special:
            st.success("✅ Erikoiskohteet on lukittu.")
            st.info("Voit tarkastella veikkauksiasi Omat veikkaukset -sivulta.")
        else:
            st.subheader("🏆 Erikoiskohteet")
            st.caption("Erikoiskohteet sulkeutuvat 15 minuuttia ennen ensimmäistä ottelua.")
            
            user_special = predictions.get(user, {}).get("special", {})
            
            for bet in special_bets:
                bet_id = bet["id"]
                current_pred = user_special.get(bet_id)
                
                st.markdown(f"**{bet['name']}** ({bet['points']} pistettä)")
                
                if bet["type"] == "yesno":
                    value = st.radio("Valinta:", ["Kyllä", "Ei"], horizontal=True, 
                                   key=f"spec_{bet_id}", index=0 if current_pred == "Kyllä" else 1)
                elif bet["type"] == "group_select":
                    value = st.selectbox("Valitse lohko", ["A","B","C","D","E","F","G","H","I","J","K","L"], 
                                       key=f"spec_{bet_id}")
                elif bet["type"] == "penalty_range":
                    value = st.selectbox("Valitse vaihtoehto", ["0-10", "11-15", "16-20", "21+"], 
                                       key=f"spec_{bet_id}")
                elif bet["type"] == "number" or bet["id"] == "ronaldo_goals":
                    value = st.number_input("Anna numero", min_value=0, max_value=30, value=int(current_pred) if current_pred and current_pred.isdigit() else 0, 
                                          key=f"spec_{bet_id}")
                elif bet["id"] == "top_scorer":
                    value = st.text_input("Pelaajan nimi", value=current_pred or "", key=f"spec_{bet_id}")
                else:
                    value = st.selectbox("Valitse maa", countries, key=f"spec_{bet_id}")
                
                if st.button("Tallenna veikkaus", key=f"save_spec_{bet_id}", use_container_width=True):
                    if user not in predictions:
                        predictions[user] = {}
                    if "special" not in predictions[user]:
                        predictions[user]["special"] = {}
                    predictions[user]["special"][bet_id] = str(value).strip()
                    save_json(PREDICTIONS_FILE, predictions)
                    st.success("✅ Erikoiskohde tallennettu!")
                
                st.divider()


# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"📋 {user} - Omat veikkaukset")
        
        tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
        
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
                        st.write(f"Tulos: **{real[0]}–{real[1]}**")
                    else:
                        st.write("Tulos ei vielä saatavilla")
                    if pred:
                        st.write(f"Oma veikkaus: **{pred[0]}–{pred[1]}**")
                    else:
                        st.write("Ei veikkausta")
                
                with col2:
                    if real and pred:
                        pts = calculate_match_points(pred, real, is_double)
                        double_note = " ×2" if is_double else ""
                        st.success(f"**+{pts} pistettä**{double_note}")
                    elif real:
                        st.info("0 pistettä")
                
                st.divider()
        
        with tab2:
            user_special = predictions.get(user, {}).get("special", {})
            real_special = real_results.get("special", {})
            
            for bet in special_bets:
                pred_value = user_special.get(bet["id"])
                real_value = real_special.get(bet["id"])
                
                st.markdown(f"**{bet['name']}**")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if pred_value:
                        st.write(f"Oma veikkaus: **{pred_value}**")
                    else:
                        st.write("Ei veikkausta")
                    if real_value:
                        st.success(f"Toteutunut tulos: **{real_value}**")
                
                with col2:
                    if real_value and pred_value:
                        if str(pred_value).lower().strip() in str(real_value).lower().strip():
                            st.success(f"+{bet.get('points', 0)}p")
                
                st.divider()


# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.subheader("🏆 Veikkaustilanne")
    
    leaderboard = []
    for username in users.keys():
        user_pred = predictions.get(username, {})
        total = 0
        
        # Ottelupisteet
        for m in matches:
            pred = user_pred.get(str(m['id']))
            real = real_results.get("matches", {}).get(str(m['id']))
            if pred and real:
                total += calculate_match_points(pred, real, m.get("double_points", False))
        
        # Erikoiskohteet
        user_special = user_pred.get("special", {})
        real_special = real_results.get("special", {})
        for bet in special_bets:
            if user_special.get(bet["id"]) and real_special.get(bet["id"]):
                if str(user_special[bet["id"]]).lower().strip() in str(real_special[bet["id"]]).lower().strip():
                    total += bet.get("points", 0)
        
        leaderboard.append({"Nimi": username, "Pisteet": total})
    
    leaderboard.sort(key=lambda x: x["Pisteet"], reverse=True)
    
    for i, entry in enumerate(leaderboard, 1):
        c1, c2, c3 = st.columns([0.8, 2, 1])
        with c1:
            st.markdown(f"**#{i}**")
        with c2:
            st.markdown(f"**{entry['Nimi']}**")
        with c3:
            st.markdown(f"<div style='text-align:center; font-size:1.4rem; font-weight:700; color:#00ff9d;'>{entry['Pisteet']}p</div>", unsafe_allow_html=True)
        st.divider()


# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("👥 Kaikkien veikkaukset")
    st.caption("Täällä näet kaikkien pelaajien veikkaukset kun ottelut tai erikoiskohteet on ratkenneet.")
    
    tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
    
    with tab1:
        locked_matches = real_results.get("matches", {})
        if not locked_matches:
            st.info("Yhtään ottelua ei ole vielä ratkennut.")
        else:
            for m in matches:
                match_id = str(m['id'])
                real = locked_matches.get(match_id)
                if real:
                    is_double = m.get("double_points", False)
                    st.markdown(f"**{m['home']} — {m['away']}** { '(×2)' if is_double else ''}")
                    st.success(f"Tulos: **{real[0]}–{real[1]}**")
                    
                    for u in sorted(users.keys()):
                        pred = predictions.get(u, {}).get(match_id)
                        if pred:
                            pts = calculate_match_points(pred, real, is_double)
                            st.write(f"{u}: {pred[0]}–{pred[1]} → **+{pts}p**")
                    st.divider()
    
    with tab2:
        locked_special = real_results.get("special", {})
        if not locked_special:
            st.info("Erikoiskohteita ei ole vielä ratkennut.")
        else:
            for bet in special_bets:
                real_val = locked_special.get(bet["id"])
                if real_val:
                    st.markdown(f"**{bet['name']}**")
                    st.success(f"Oikea vastaus: **{real_val}**")
                    
                    for u in sorted(users.keys()):
                        user_pred = predictions.get(u, {}).get("special", {}).get(bet["id"])
                        if user_pred:
                            pts = bet.get("points", 0) if str(user_pred).lower().strip() in str(real_val).lower().strip() else 0
                            st.write(f"{u}: {user_pred} {'→ **+' + str(pts) + 'p**' if pts > 0 else ''}")
                    st.divider()
    
   
# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")
    
    ADMIN_PASSWORD = "admin123"  # ← VAIHDA TÄHÄN TURVALLINEN SALASANA!
    
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
    
    admin_tab = st.radio("Valitse toiminto", ["Ottelujen tulokset", "Erikoiskohteiden tulokset"], horizontal=True)
    
    if admin_tab == "Ottelujen tulokset":
        st.write("### Ottelujen tulosten syöttö")
        for m in matches:
            match_id = str(m['id'])
            current_real = real_results.get("matches", {}).get(match_id)
            
            col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
            with col1:
                st.write(f"**{m['home']} — {m['away']}**")
            with col2:
                h = st.number_input("Koti", 0, 20, value=current_real[0] if current_real else 0, 
                                  key=f"ah_{match_id}")
            with col3:
                a = st.number_input("Vieras", 0, 20, value=current_real[1] if current_real else 0, 
                                  key=f"aa_{match_id}")
            with col4:
                if st.button("Tallenna", key=f"save_{match_id}"):
                    if "matches" not in real_results:
                        real_results["matches"] = {}
                    real_results["matches"][match_id] = [h, a]
                    save_json(RESULTS_FILE, real_results)
                    st.success(f"Tallennettu: {m['home']} {h}–{a} {m['away']}")
                    st.rerun()
                
                if current_real and st.button("🗑️ Poista", key=f"del_{match_id}"):
                    real_results["matches"].pop(match_id, None)
                    save_json(RESULTS_FILE, real_results)
                    st.success("Tulos poistettu")
                    st.rerun()
            st.divider()
    
    else:  # Erikoiskohteiden tulokset
        st.write("### Erikoiskohteiden tulosten syöttö")
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
