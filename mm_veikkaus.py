import streamlit as st
import pandas as pd
import json
import hashlib
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="MM 2026 Veikkaus", layout="wide", page_icon="🏆")

st.markdown("""
    <style>
        .stApp { background-color: #0a0f1c; color: #e0e0e0; }
        
        /* Etusivun tyylit */
        .etusivu_text { 
            text-align: center; 
            font-size: 5.5rem; 
            font-weight: 900; 
            color: #00ff9d; 
            text-shadow: 0 0 40px rgba(0, 255, 157, 0.7);
            margin: 80px 0 20px 0;
        }
        .welcome_text { 
            text-align: center; 
            font-size: 5.5rem; 
            font-weight: 900; 
            color: #ffffff; 
            margin-bottom: 60px;
        }
        
        /* Omat veikkaukset -tyylit */
        .pred-box { 
            background-color: #3a1f1f; 
            color: #ff8888;
            padding: 12px 20px; 
            border-radius: 8px; 
            font-weight: 600;
            font-size: 1.1rem;
            width: 160px;
            text-align: center;
            margin: 3px 0;
        }
        .result-box { 
            background-color: #1f3a2a; 
            color: #88ffaa;
            padding: 12px 20px; 
            border-radius: 8px; 
            font-weight: 600;
            font-size: 1.1rem;
            width: 160px;
            text-align: center;
            margin: 3px 0;
        }
        .points-box { 
            background-color: #2a2a4a; 
            color: #ffff88;
            padding: 18px 24px; 
            border-radius: 50px; 
            font-weight: 700;
            font-size: 1.4rem;
            text-align: center;
            width: 85px;
            height: 85px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(255, 255, 136, 0.5);
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# ====================== TIEDOSTOT ======================
USERS_FILE = "users.json"
PREDICTIONS_FILE = "predictions.json"
RESULTS_FILE = "real_results.json"

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

users = load_json(USERS_FILE, {})
predictions = load_json(PREDICTIONS_FILE, {})
real_results = load_json(RESULTS_FILE, {})

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

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

# ====================== 72 OTTELUA - YLEN MUKAAN ======================
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
    {"id": "most_goals", "name": "1. Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 6, "type": "select"},
    {"id": "most_cards", "name": "2. Mikä maa saa alkulohkoissa eniten varoituksia?", "points": 6, "type": "select"},
    {"id": "top_scorer", "name": "3. Paras maalintekijä", "points": 6, "type": "text"},
    {"id": "top_scorer_goals", "name": "4. Millä maalimäärällä voitetaan maalintekijäkuninkuus?", "points": 6, "type": "number"},
    {"id": "champion", "name": "5. Maailmanmestari", "points": 6, "type": "select"},
]

for letter in "ABCDEFGHIJKL":
    special_bets.append({"id": f"group_{letter.lower()}", "name": f"Lohko {letter} voittaja", "points": 6, "type": "select"})

# ====================== FUNKTIOT ======================
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

def calculate_match_points(pred, real):
    if not pred or not real:
        return 0
    ph, pa = pred
    rh, ra = real
    if ph == rh and pa == ra:
        return 8
    if ph == pa and rh == ra:
        return 5
    p_win = 1 if ph > pa else 2 if pa > ph else 0
    r_win = 1 if rh > ra else 2 if ra > rh else 0
    if p_win == r_win and p_win != 0:
        if ph == rh or pa == ra:
            return 5
        return 3
    return 0

# ====================== NAVIGOINTI ======================
if st.session_state.logged_in_user:
    st.sidebar.success(f"👤 {st.session_state.logged_in_user}")
    if st.sidebar.button("Kirjaudu ulos"):
        st.session_state.logged_in_user = None
        st.rerun()

page = st.sidebar.radio("Valikko", [
    "Etusivu", "Kirjaudu / Rekisteröidy", "VEIKKAA OTTELUITA", 
    "VEIKKAA ERIKOISKOHTEITA", "Veikkaustilanne", "Omat veikkaukset", 
    "Kaikkien veikkaukset", "Admin"
])

# ====================== ETUSIVU ======================
if page == "Etusivu":
    # Taustatyylit
    st.markdown("""
        <style>
            .etusivu_text { 
                text-align: center; 
                font-size: 8.2rem; 
                font-weight: 900; 
                color: #00ff9d; 
                text-shadow: 0 0 50px rgba(0, 255, 157, 0.8);
                margin: 80px 0 30px 0;
                position: relative;
                z-index: 2;
            }
            .welcome_text { 
                text-align: center; 
                font-size: 5.7rem; 
                font-weight: 700; 
                color: #e0e0e0; 
                margin-bottom: 100px;
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

    # Sikin sokin maat taustalle
    st.markdown("""
        <div class="background-countries">
            Argentiina Brasilia Ranska Saksa Espanja Englanti Portugali Hollanti Belgia Italia Uruguay Kolumbia Meksiko USA Japani Etelä-Korea Australia Marokko Senegal Norsunluurannikko Ghana Kroatia Sveitsi Ruotsi Tanska Puola Algeria Egypti Nigeria Tunisia Saudi-Arabia Qatar Iran Irak Jordania Panama Kanada Paraguay Ecuador Peru Chile Venezuela Bolivia
        </div>
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

# ====================== VEIKKAA OTTELUITA ======================
if page == "VEIKKAA OTTELUITA":
    if not st.session_state.logged_in_user:
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"VEIKKAA OTTELUITA")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Ottelut 1-18", "Ottelut 19-36", "Ottelut 37-54", "Ottelut 55-72"])
        tabs_list = [tab1, tab2, tab3, tab4]
        
        for tab_idx, tab in enumerate(tabs_list):
            with tab:
                start = tab_idx * 18
                end = min(start + 18, len(matches))
                
                for i in range(start, end):
                    m = matches[i]
                    match_id = str(m['id'])
                    key = f"match_{match_id}"
                    
                    st.write(f"**{m['home']} — {m['away']}**  ({m.get('group', '')})")
                    
                    real = real_results.get("matches", {}).get(match_id)
                    countdown = get_countdown(m)
                    if isinstance(countdown, tuple):
                        countdown = countdown[0]
                    
                    if real:
                        st.markdown("🔒 **Kohde lukittu**", unsafe_allow_html=True)
                    elif countdown == "Suljettu" or "Suljettu" in str(countdown):
                        st.markdown("🔴 **Veikkaus on suljettu**", unsafe_allow_html=True)
                    else:
                        st.markdown(f"🟢 **{countdown}**", unsafe_allow_html=True)
                    
                    # Veikkauslomake (lukittu jos tulos on jo tallennettu)
                    disabled = real is not None
                    
                    col_home, col_away = st.columns(2)
                    with col_home:
                        home_score = st.number_input("Kotimaali", min_value=0, max_value=10, value=0, 
                                                   key=f"{key}_home", label_visibility="collapsed", disabled=disabled)
                    with col_away:
                        away_score = st.number_input("Vierasmaali", min_value=0, max_value=10, value=0, 
                                                   key=f"{key}_away", label_visibility="collapsed", disabled=disabled)
                    
                    if st.button("TALLENNA VEIKKAUS", key=f"save_{key}", use_container_width=True, disabled=disabled):
                        if user not in predictions:
                            predictions[user] = {}
                        predictions[user][match_id] = [home_score, away_score]
                        save_json(PREDICTIONS_FILE, predictions)
                        st.success(f"Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                    
                    st.divider()

# ====================== VEIKKAA ERIKOISKOHTEITA ======================
if page == "VEIKKAA ERIKOISKOHTEITA":
    if not st.session_state.logged_in_user:
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"VEIKKAA ERIKOISKOHTEITA")
        
        countdown = get_special_bets_countdown() if 'get_special_bets_countdown' in globals() else "Aika ei saatavilla"
        if isinstance(countdown, tuple):
            countdown = countdown[0]
        
        if countdown == "Suljettu" or "Suljettu" in str(countdown):
            st.markdown("🔴 **Erikoiskohteiden veikkaus on suljettu**", unsafe_allow_html=True)
        else:
            st.markdown(f"🟢 **{countdown}**", unsafe_allow_html=True)
        
        st.divider()
        
        user_special = predictions.get(user, {}).get("special", {})
        real_special = real_results.get("special", {})
        
        for bet in special_bets:
            real_val = real_special.get(bet["id"])
            st.write(f"**{bet['name']}** ({bet.get('points', 6)} pistettä)")
            
            if real_val:
                st.markdown("🔒 **Kohde lukittu**", unsafe_allow_html=True)
                st.write(f"Toteutunut tulos: **{real_val}**")
                st.divider()
                continue
            
            col_input, col_button = st.columns([3.5, 1])
            
            with col_input:
                if bet["id"] == "most_goals" or bet["id"] == "most_cards":
                    value = st.selectbox("Valitse maa", options=countries, 
                                       key=f"special_{bet['id']}", label_visibility="collapsed")
                elif bet["id"] == "top_scorer":
                    value = st.text_input("Pelaajan nimi", key=f"special_{bet['id']}", label_visibility="collapsed")
                elif bet["id"] == "top_scorer_goals":
                    value = st.selectbox("Maalimäärä", options=list(range(1, 21)), 
                                       key=f"special_{bet['id']}", label_visibility="collapsed")
                elif bet["id"] == "champion":
                    value = st.selectbox("Valitse maa", options=countries, 
                                       key=f"special_{bet['id']}", label_visibility="collapsed")
                elif bet["id"].startswith("group_"):
                    group_letter = bet["id"].split("_")[1].upper()
                    group_matches = [m for m in matches if m.get("group") == group_letter]
                    group_teams = sorted(set([m["home"] for m in group_matches] + [m["away"] for m in group_matches]))
                    value = st.selectbox("Lohkovoittaja", options=group_teams, 
                                       key=f"special_{bet['id']}", label_visibility="collapsed")
                else:
                    value = st.text_input("Vastaus", key=f"special_{bet['id']}", label_visibility="collapsed")
            
            with col_button:
                if st.button("TALLENNA VEIKKAUS", key=f"save_{bet['id']}", use_container_width=True):
                    if user not in predictions:
                        predictions[user] = {"special": {}}
                    if "special" not in predictions[user]:
                        predictions[user]["special"] = {}
                    predictions[user]["special"][bet["id"]] = str(value).strip()
                    save_json(PREDICTIONS_FILE, predictions)
                    st.success("Tallennettu!")
            
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
                total_points += calculate_match_points(pred, real)
        
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
        c1, c2, c3 = st.columns([0.8, 1.2, 1.2])
        
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
    if not st.session_state.logged_in_user:
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"OMAT VEIKKAUKSET")
        
        tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
        
        # ====================== TAB 1: OTTELUVEIKKAUKSET ======================
        with tab1:
            
            for m in matches:
                pred = predictions.get(user, {}).get(str(m['id']))
                real = real_results.get("matches", {}).get(str(m['id']))
                
                st.write(f"**{m['home']} — {m['away']}**")
                
                col1, col2 = st.columns([2.8, 1.2])
                
                with col1:
                    if pred:
                        st.markdown(f'<div class="pred-box">{pred[0]}–{pred[1]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="pred-box">–</div>', unsafe_allow_html=True)
                    
                    if real:
                        st.markdown(f'<div class="result-box">{real[0]}–{real[1]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="result-box">–</div>', unsafe_allow_html=True)
                
                with col2:
                    if real and pred:
                        pts = calculate_match_points(pred, real)
                        st.markdown(f'<div class="points-box">+{pts}</div>', unsafe_allow_html=True)
                    elif real:
                        st.markdown('<div class="points-box">0</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="points-box">–</div>', unsafe_allow_html=True)
                
                st.divider()

        # ====================== TAB 2: ERIKOISKOHTEET ======================
        with tab2:
            
            user_special = predictions.get(user, {}).get("special", {})
            real_special = real_results.get("special", {})
            
            for bet in special_bets:
                pred_value = user_special.get(bet["id"], None)
                real_value = real_special.get(bet["id"])
                
                st.write(f"**{bet['name']}**")
                
                col1, col2 = st.columns([2.8, 1.2])
                
                with col1:
                    if pred_value:
                        st.markdown(f'<div class="pred-box">{pred_value}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="pred-box">–</div>', unsafe_allow_html=True)
                    
                    if real_value:
                        st.markdown(f'<div class="result-box">{real_value}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="result-box">–</div>', unsafe_allow_html=True)
                
                with col2:
                    if real_value and pred_value:
                        user_str = str(pred_value).lower().strip()
                        real_list = [x.strip().lower() for x in str(real_value).split(",")]
                        pts = bet["points"] if user_str in real_list else 0
                        st.markdown(f'<div class="points-box">+{pts}</div>', unsafe_allow_html=True)
                    elif real_value:
                        st.markdown('<div class="points-box">0</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="points-box">–</div>', unsafe_allow_html=True)
                
                st.divider()

# ====================== KAIKKIEN VEIKKAUKSET ======================
if page == "Kaikkien veikkaukset":
    st.subheader("KAIKKIEN VEIKKAUKSET")
    
    st.divider()  # <-- Viiva otsikon ja ensimmäisen ottelun väliin
    
    for m in matches:
        match_id = str(m['id'])
        real = real_results.get("matches", {}).get(match_id)
        
        # Ottelu isommalla fontilla
        st.markdown(f"**{m['home']} — {m['away']}**  ({m.get('group', '')})", unsafe_allow_html=True)
        
        if real:
            st.markdown(f"**Toteutunut tulos:** {real[0]}–{real[1]}", unsafe_allow_html=True)
        
        # Pelaajien veikkaukset
        has_predictions = False
        for u in users.keys():
            pred = predictions.get(u, {}).get(match_id)
            if pred:
                has_predictions = True
                if real:
                    pts = calculate_match_points(pred, real)
                    st.markdown(f"**{u}**: {pred[0]}–{pred[1]}  <span style='color:#00ff9d'>({pts}p)</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{u}**: {pred[0]}–{pred[1]}", unsafe_allow_html=True)
        
        if not has_predictions:
            st.caption("Ei vielä veikkauksia tähän otteluun.")
        
        st.divider()  # Viiva otteluiden väliin

# ====================== ADMIN ======================
if page == "Admin":
    pw = st.text_input("Admin-salasana", type="password")
    if pw == "admin123":
        st.success("✅ Admin auki")
        tab1, tab2 = st.tabs(["Ottelutulokset", "Erikoiskohteet"])
        with tab1:
            for m in matches:
                st.write(f"{m['home']} — {m['away']}")
                c1, c2 = st.columns(2)
                with c1: h = st.number_input("Koti", min_value=0, key=f"rh_{m['id']}")
                with c2: a = st.number_input("Vieras", min_value=0, key=f"ra_{m['id']}")
                if st.button("Tallenna tulos", key=f"save_match_{m['id']}"):
                    if "matches" not in real_results:
                        real_results["matches"] = {}
                    real_results["matches"][str(m['id'])] = (h, a)
                    save_json(RESULTS_FILE, real_results)
                st.divider()
        with tab2:
            for bet in special_bets:
                st.write(f"**{bet['name']}**")
                current = real_results.get("special", {}).get(bet["id"], "")
                val = st.text_input("Hyväksytyt vastaukset (pilkulla eroteltuna)", value=current, key=f"admin_{bet['id']}")
                if st.button("Tallenna", key=f"save_admin_{bet['id']}"):
                    if "special" not in real_results:
                        real_results["special"] = {}
                    real_results["special"][bet["id"]] = val
                    save_json(RESULTS_FILE, real_results)
                    st.success("Tallennettu!")
                st.divider()

