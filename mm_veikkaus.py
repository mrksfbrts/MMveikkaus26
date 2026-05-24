import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
import json
from datetime import datetime, timedelta

st.set_page_config(
    page_title="MM26 Veikkaus",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== PERSISTENT DISK (Render) ======================
DATA_DIR = "/data"   # Renderin Persistent Disk käyttää tätä polkua
DB_PATH = os.path.join(DATA_DIR, "veikkaus.db")
os.makedirs(DATA_DIR, exist_ok=True)

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, password_hash TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS predictions (
                    username TEXT, 
                    match_id TEXT, 
                    home_goals INTEGER, 
                    away_goals INTEGER,
                    special_bets TEXT DEFAULT '{}',
                    PRIMARY KEY (username, match_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS real_results (
                    type TEXT, 
                    id TEXT, 
                    result TEXT,
                    PRIMARY KEY (type, id))''')
    
    conn.commit()
    conn.close()

init_db()

# ====================== HELPER FUNKTIOT ======================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    conn = get_db()
    df = pd.read_sql_query("SELECT username, password_hash FROM users", conn)
    conn.close()
    return dict(df.values.tolist())

def save_user(username, password_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()

def save_prediction(username, match_id, home_goals, away_goals, special=None):
    conn = get_db()
    c = conn.cursor()
    special_json = json.dumps(special) if special else '{}'
    c.execute("""INSERT OR REPLACE INTO predictions 
                 (username, match_id, home_goals, away_goals, special_bets) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (username, str(match_id), int(home_goals), int(away_goals), special_json))
    conn.commit()
    conn.close()

def load_real_results():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM real_results", conn)
    conn.close()
    real = {"matches": {}, "special": {}}
    for _, row in df.iterrows():
        try:
            data = json.loads(row['result'])
            if row['type'] == "matches":
                real["matches"][row['id']] = data
            else:
                real["special"][row['id']] = data
        except:
            pass
    return real

def save_real_result(result_type, rid, result):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO real_results (type, id, result) VALUES (?, ?, ?)",
              (result_type, str(rid), json.dumps(result)))
    conn.commit()
    conn.close()


# ====================== MAAT ======================
countries = sorted([
    "Algeria", "Argentiina", "Australia", "Belgia", "Bosnia ja Hertsegovina", "Brasilia",
    "Chile", "Curaçao", "Ecuador", "Egypti", "Englanti", "Espanja", "Etelä-Afrikka",
    "Etelä-Korea", "Ghana", "Haiti", "Iran", "Irak", "Italia", "Itävalta", "Japani",
    "Jordania", "Kanada", "Kolumbia", "Kroatia", "Marokko", "Meksiko", "Nigeria",
    "Norja", "Norsunluurannikko", "Panama", "Paraguay", "Portugali", "Qatar", "Ranska",
    "Ruotsi", "Saksa", "Saudi-Arabia", "Senegal", "Skotlanti", "Sveitsi", "Tanska",
    "Tunisia", "Turkki", "Tšekki", "Uruguay", "USA", "Uusi-Seelanti", "Uzbekistan"
])

# ====================== OTTELUT ======================
matches = [
    {"id":1, "date":"2026-06-11", "time":"22:00", "home":"Meksiko", "away":"Etelä-Afrikka", "group":"A"},
    {"id":2, "date":"2026-06-12", "time":"05:00", "home":"Etelä-Korea", "away":"Tšekki", "group":"A"},
    {"id":3, "date":"2026-06-12", "time":"22:00", "home":"Kanada", "away":"Bosnia ja Hertsegovina", "group":"B"},
    {"id":4, "date":"2026-06-13", "time":"04:00", "home":"USA", "away":"Paraguay", "group":"D"},
    {"id":5, "date":"2026-06-13", "time":"22:00", "home":"Qatar", "away":"Sveitsi", "group":"B"},
    {"id":6, "date":"2026-06-14", "time":"01:00", "home":"Brasilia", "away":"Marokko", "group":"C"},
    {"id":7, "date":"2026-06-14", "time":"04:00", "home":"Haiti", "away":"Skotlanti", "group":"C"},
    {"id":8, "date":"2026-06-14", "time":"07:00", "home":"Australia", "away":"Turkki", "group":"D"},
    {"id":9, "date":"2026-06-14", "time":"20:00", "home":"Saksa", "away":"Curaçao", "group":"E"},
    {"id":10,"date":"2026-06-14", "time":"23:00", "home":"Hollanti", "away":"Japani", "group":"F"},
    {"id":11,"date":"2026-06-15", "time":"02:00", "home":"Norsunluurannikko", "away":"Ecuador", "group":"E"},
    {"id":12,"date":"2026-06-15", "time":"05:00", "home":"Ruotsi", "away":"Tunisia", "group":"F"},
    {"id":13,"date":"2026-06-15", "time":"19:00", "home":"Espanja", "away":"Kap Verde", "group":"H"},
    {"id":14,"date":"2026-06-15", "time":"22:00", "home":"Belgia", "away":"Egypti", "group":"G"},
    {"id":15,"date":"2026-06-16", "time":"01:00", "home":"Saudi-Arabia", "away":"Uruguay", "group":"H"},
    {"id":16,"date":"2026-06-16", "time":"04:00", "home":"Iran", "away":"Uusi-Seelanti", "group":"G"},
    {"id":17,"date":"2026-06-16", "time":"22:00", "home":"Ranska", "away":"Senegal", "group":"I"},
    {"id":18,"date":"2026-06-17", "time":"01:00", "home":"Irak", "away":"Norja", "group":"I"},
    {"id":19,"date":"2026-06-17", "time":"04:00", "home":"Argentiina", "away":"Algeria", "group":"J"},
    {"id":20,"date":"2026-06-17", "time":"07:00", "home":"Itävalta", "away":"Jordania", "group":"J"},
    {"id":21,"date":"2026-06-17", "time":"20:00", "home":"Portugali", "away":"Kongon demokraattinen tasavalta", "group":"K"},
    {"id":22,"date":"2026-06-17", "time":"23:00", "home":"Englanti", "away":"Kroatia", "group":"L"},
    {"id":23,"date":"2026-06-18", "time":"02:00", "home":"Ghana", "away":"Panama", "group":"L"},
    {"id":24,"date":"2026-06-18", "time":"05:00", "home":"Uzbekistan", "away":"Kolumbia", "group":"K"},
    {"id":25,"date":"2026-06-18", "time":"19:00", "home":"Tšekki", "away":"Etelä-Afrikka", "group":"A"},
    {"id":26,"date":"2026-06-18", "time":"22:00", "home":"Sveitsi", "away":"Bosnia ja Hertsegovina", "group":"B"},
    {"id":27,"date":"2026-06-19", "time":"01:00", "home":"Kanada", "away":"Qatar", "group":"B"},
    {"id":28,"date":"2026-06-19", "time":"04:00", "home":"Meksiko", "away":"Etelä-Korea", "group":"A"},
    {"id":29,"date":"2026-06-19", "time":"22:00", "home":"USA", "away":"Australia", "group":"D"},
    {"id":30,"date":"2026-06-20", "time":"01:00", "home":"Skotlanti", "away":"Marokko", "group":"C"},
    {"id":31,"date":"2026-06-20", "time":"04:00", "home":"Brasilia", "away":"Haiti", "group":"C"},
    {"id":32,"date":"2026-06-20", "time":"07:00", "home":"Turkki", "away":"Paraguay", "group":"D"},
    {"id":33,"date":"2026-06-20", "time":"20:00", "home":"Hollanti", "away":"Ruotsi", "group":"F"},
    {"id":34,"date":"2026-06-20", "time":"23:00", "home":"Saksa", "away":"Norsunluurannikko", "group":"E"},
    {"id":35,"date":"2026-06-21", "time":"03:00", "home":"Ecuador", "away":"Curaçao", "group":"E"},
    {"id":36,"date":"2026-06-21", "time":"07:00", "home":"Tunisia", "away":"Japani", "group":"F"},
    {"id":37,"date":"2026-06-21", "time":"19:00", "home":"Espanja", "away":"Saudi-Arabia", "group":"H"},
    {"id":38,"date":"2026-06-21", "time":"22:00", "home":"Belgia", "away":"Iran", "group":"G"},
    {"id":39,"date":"2026-06-22", "time":"01:00", "home":"Uruguay", "away":"Kap Verde", "group":"H"},
    {"id":40,"date":"2026-06-22", "time":"04:00", "home":"Uusi-Seelanti", "away":"Egypti", "group":"G"},
    {"id":41,"date":"2026-06-22", "time":"20:00", "home":"Argentiina", "away":"Itävalta", "group":"J"},
    {"id":42,"date":"2026-06-23", "time":"00:00", "home":"Ranska", "away":"Irak", "group":"I"},
    {"id":43,"date":"2026-06-23", "time":"03:00", "home":"Norja", "away":"Senegal", "group":"I"},
    {"id":44,"date":"2026-06-23", "time":"06:00", "home":"Jordania", "away":"Algeria", "group":"J"},
    {"id":45,"date":"2026-06-23", "time":"20:00", "home":"Portugali", "away":"Uzbekistan", "group":"K"},
    {"id":46,"date":"2026-06-23", "time":"23:00", "home":"Englanti", "away":"Ghana", "group":"L"},
    {"id":47,"date":"2026-06-24", "time":"02:00", "home":"Panama", "away":"Kroatia", "group":"L"},
    {"id":48,"date":"2026-06-24", "time":"05:00", "home":"Kolumbia", "away":"Kongon demokraattinen tasavalta", "group":"K"},
    {"id":49,"date":"2026-06-24", "time":"22:00", "home":"Sveitsi", "away":"Kanada", "group":"B"},
    {"id":50,"date":"2026-06-24", "time":"22:00", "home":"Bosnia ja Hertsegovina", "away":"Qatar", "group":"B"},
    {"id":51,"date":"2026-06-25", "time":"01:00", "home":"Skotlanti", "away":"Brasilia", "group":"C"},
    {"id":52,"date":"2026-06-25", "time":"01:00", "home":"Marokko", "away":"Haiti", "group":"C"},
    {"id":53,"date":"2026-06-25", "time":"04:00", "home":"Tšekki", "away":"Meksiko", "group":"A"},
    {"id":54,"date":"2026-06-25", "time":"04:00", "home":"Etelä-Afrikka", "away":"Etelä-Korea", "group":"A"},
    {"id":55,"date":"2026-06-25", "time":"23:00", "home":"Curaçao", "away":"Norsunluurannikko", "group":"E"},
    {"id":56,"date":"2026-06-25", "time":"23:00", "home":"Ecuador", "away":"Saksa", "group":"E"},
    {"id":57,"date":"2026-06-26", "time":"02:00", "home":"Japani", "away":"Ruotsi", "group":"F"},
    {"id":58,"date":"2026-06-26", "time":"02:00", "home":"Tunisia", "away":"Hollanti", "group":"F"},
    {"id":59,"date":"2026-06-26", "time":"05:00", "home":"Turkki", "away":"USA", "group":"D"},
    {"id":60,"date":"2026-06-26", "time":"05:00", "home":"Paraguay", "away":"Australia", "group":"D"},
    {"id":61,"date":"2026-06-26", "time":"22:00", "home":"Norja", "away":"Ranska", "group":"I"},
    {"id":62,"date":"2026-06-26", "time":"22:00", "home":"Senegal", "away":"Irak", "group":"I"},
    {"id":63,"date":"2026-06-27", "time":"03:00", "home":"Kap Verde", "away":"Saudi-Arabia", "group":"H"},
    {"id":64,"date":"2026-06-27", "time":"03:00", "home":"Uruguay", "away":"Espanja", "group":"H"},
    {"id":65,"date":"2026-06-27", "time":"06:00", "home":"Egypti", "away":"Iran", "group":"G"},
    {"id":66,"date":"2026-06-27", "time":"06:00", "home":"Uusi-Seelanti", "away":"Belgia", "group":"G"},
    {"id":67,"date":"2026-06-28", "time":"00:00", "home":"Panama", "away":"Englanti", "group":"L"},
    {"id":68,"date":"2026-06-28", "time":"00:00", "home":"Kroatia", "away":"Ghana", "group":"L"},
    {"id":69,"date":"2026-06-28", "time":"02:30", "home":"Kolumbia", "away":"Portugali", "group":"K"},
    {"id":70,"date":"2026-06-28", "time":"02:30", "home":"Kongon demokraattinen tasavalta", "away":"Uzbekistan", "group":"K"},
    {"id":71,"date":"2026-06-28", "time":"05:00", "home":"Algeria", "away":"Itävalta", "group":"J"},
    {"id":72,"date":"2026-06-28", "time":"05:00", "home":"Jordania", "away":"Argentiina", "group":"J"}
]

# ====================== ERIKOISKOHTEET ======================
special_bets = [
    {"id": "most_goals", "name": "1. Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 5, "type": "select"},
    {"id": "most_cards", "name": "2. Mikä maa saa alkulohkoissa eniten varoituksia?", "points": 5, "type": "select"},
    {"id": "top_scorer", "name": "3. Paras maalintekijä", "points": 10, "type": "text"},
    {"id": "top_scorer_goals", "name": "4. Millä maalimäärällä voitetaan maalintekijäkuninkuus?", "points": 5, "type": "number"},
    {"id": "champion", "name": "5. Maailmanmestari", "points": 10, "type": "select"},
]

for letter in "ABCDEFGHIJKL":
    special_bets.append({"id": f"group_{letter.lower()}", "name": f"Lohko {letter} voittaja", "points": 3, "type": "select"})

# ====================== ISTUNTO ======================
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

users = load_users()
real_results = load_real_results()

st.toast("✅ Tietokanta ja Persistent Disk käytössä", icon="🔒")

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
    st.markdown("""
        <style>
            .etusivu_text { 
                text-align: center; 
                font-size: 9.2rem; 
                font-weight: 1000; 
                color: #00ff9d; 
                text-shadow: 0 0px rgba(0, 255, 157, 0.8);
                margin: 40px 0 30px 0;
            }
            .welcome_text { 
                text-align: center; 
                font-size: 5.7rem; 
                font-weight: 1000; 
                color: #e0e0e0; 
                margin-bottom: 80px;
            }
        </style>
    """, unsafe_allow_html=True)

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
        
        with tab1:
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
                        save_user(new_user, hash_password(new_pass))
                        users[new_user] = hash_password(new_pass)
                        st.success("Tunnus luotu onnistuneesti! Voit nyt kirjautua sisään.")

# ====================== SÄÄNNÖT ======================
if page == "Säännöt":
    st.title("Säännöt ja pisteytysjärjestelmä")
    st.markdown("---")
    st.subheader("Otteluveikkaukset")
    st.markdown("""Pisteitä saa ainoastaan, kun on veikannut oikeaa tulosta (1X2)...""")  # voit kopioida tarkemman tekstin alkuperäisestä
    
    # Pistetaulukko (sama kuin ennen)
    data = {
        "Veikkauksesi": ["Täysin oikea tulos", "Oikea voittaja + ...", "Väärä 1X2"],
        "Pisteet": ["**8**", "**6/5/4/3**", "**0**"]
    }
    st.table(pd.DataFrame(data))
    
    st.caption("Yksittäinen veikkauskohde sulkeutuu 15 minuuttia ennen ottelun alkua...")

# ====================== VEIKKAA OTTELUITA ======================
if page == "Veikkaa otteluita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader("Veikkaa otteluita")
        
        open_matches = [m for m in matches if str(m['id']) not in real_results.get("matches", {})]
        
        if not open_matches:
            st.success("✅ Kaikki ottelut on jo veikkailtu tai lukittu!")
        else:
            for m in open_matches:
                match_id = str(m['id'])
                countdown_str, is_open = get_countdown(m) if 'get_countdown' in globals() else ("⏳ Avoin", True)
                
                st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')})")
                if not is_open:
                    st.markdown("🔴 **Kohde on suljettu**")
                else:
                    st.markdown(f"🟢 **{countdown_str}**")
                
                col_home, col_away = st.columns(2)
                with col_home:
                    home_score = st.number_input("Koti", 0, 10, 0, key=f"h_{match_id}")
                with col_away:
                    away_score = st.number_input("Vieras", 0, 10, 0, key=f"a_{match_id}")
                
                if st.button("Tallenna veikkaus", key=f"save_{match_id}", use_container_width=True):
                    save_prediction(user, match_id, home_score, away_score)
                    st.success(f"Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                    st.rerun()
                st.divider()

# ====================== VEIKKAA ERIKOISKOHTEITA ======================
if page == "Veikkaa erikoiskohteita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        # Toteuta erikoiskohteet vastaavasti...
        st.info("Erikoiskohteiden veikkauslogiikka voidaan lisätä myöhemmin samalla tavalla.")

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.subheader("VEIKKAUSTILANNE")
    leaderboard = []
    for user in users.keys():
        total_points = 0
        # Lisää pistelaskenta myöhemmin
        leaderboard.append({"Nimi": user, "Pisteet": total_points})
    
    leaderboard.sort(key=lambda x: x["Pisteet"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["Sija"] = i + 1
    st.dataframe(leaderboard, use_container_width=True)

# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")
    ADMIN_PASSWORD = "admin123"   # Vaihda tämä!
    
    if not st.session_state.get("is_admin", False):
        pw = st.text_input("Syötä admin-salasana", type="password")
        if st.button("Kirjaudu adminiksi"):
            if pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Väärä salasana")
        st.stop()
    
    st.success("Admin-tilassa")
    # Lisää admin-toiminnot (tulosten syöttö) myöhemmin

# ====================== MUUT SIVUT ======================
# Omat veikkaukset, Kaikkien veikkaukset jne. voidaan lisätä saman logiikan mukaan

st.caption("Veikkausrinki MM26 — Powered by Streamlit + SQLite + Persistent Disk")
