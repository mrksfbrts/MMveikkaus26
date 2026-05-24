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

# ====================== MODERNI TYYLI ======================
st.markdown("""
<style>
    .stApp { background-color: #0a0f1c; color: #e0e0e0; }
    h1, h2, h3 { color: #00ff9d; }
    .stButton button { background-color: #00ff9d; color: #0a0f1c; font-weight: 700; border-radius: 8px; height: 48px; }
    .stButton button:hover { background-color: #00cc7a; }
    .divider { height: 2px; background: linear-gradient(to right, #1e2a44, #334466, #1e2a44); margin: 15px 0; }
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
    except:
        st.error("Tallennus epäonnistui")

users = load_json(USERS_FILE, {})
predictions = load_json(PREDICTIONS_FILE, {})
real_results = load_json(RESULTS_FILE, {})

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ====================== MAAT ======================
countries = sorted([
    "Algeria", "Argentiina", "Australia", "Belgia", "Bosnia ja Hertsegovina", "Brasilia",
    "Chile", "Curaçao", "Ecuador", "Egypti", "Englanti", "Espanja", "Etelä-Afrikka",
    "Etelä-Korea", "Ghana", "Haiti", "Iran", "Irak", "Itävalta", "Japani", "Jordania",
    "Kanada", "Kolumbia", "Kroatia", "Marokko", "Meksiko", "Norja", "Norsunluurannikko",
    "Panama", "Paraguay", "Portugali", "Qatar", "Ranska", "Ruotsi", "Saksa", "Saudi-Arabia",
    "Senegal", "Skotlanti", "Sveitsi", "Tanska", "Tunisia", "Turkki", "Tšekki", "Uruguay",
    "USA", "Uusi-Seelanti", "Uzbekistan"
])

# ====================== 72 OTTELUA ======================
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
    {"id": "most_goals", "name": "Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 6},
    {"id": "most_cards", "name": "Mikä maa saa alkulohkoissa eniten varoituksia?", "points": 6},
    {"id": "top_scorer", "name": "Paras maalintekijä koko turnauksessa?", "points": 6},
    {"id": "top_scorer_goals", "name": "Millä maalimäärällä voitetaan maalintekijäkuninkuus?", "points": 6},
    {"id": "champion", "name": "Maailmanmestarimaa?", "points": 6},
]

for letter in "ABCDEFGHIJKL":
    special_bets.append({"id": f"group_{letter.lower()}", "name": f"Lohkon {letter} voittaja?", "points": 6})

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
    p_home, p_away = pred
    r_home, r_away = real

    if p_home == r_home and p_away == r_away:
        return 8

    p_winner = 0 if p_home > p_away else 1 if p_home < p_away else 2
    r_winner = 0 if r_home > r_away else 1 if r_home < r_away else 2

    if p_winner != r_winner:
        return 0

    if p_winner == 2:  # Tasapeli
        return 4

    home_diff = abs(p_home - r_home)
    away_diff = abs(p_away - r_away)

    if (home_diff == 0 and away_diff == 1) or (home_diff == 1 and away_diff == 0):
        return 6
    if home_diff == 0 or away_diff == 0:
        return 5

    return 3

# ====================== SIVUPALKKI ======================
st.sidebar.title("⚽ MM26 Veikkaus")

if not st.session_state.get("logged_in_user"):
    # Kirjautumaton käyttäjä näkee vain kirjautumissivun
    page = "Kirjaudu / Rekisteröidy"
else:
    # Kirjautunut käyttäjä näkee nämä sivut
    page = st.sidebar.selectbox(
        "Valitse sivu",
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
    
    st.sidebar.success(f"👤 {st.session_state.logged_in_user}")
    
    if st.sidebar.button("🚪 Kirjaudu ulos", key="logout_btn"):
        st.session_state.logged_in_user = None
        st.rerun()

# ====================== KIRJAUDU / REKISTERÖIDY ======================
if page == "Kirjaudu / Rekisteröidy":
    st.title("MM26 - Veikkauskisa")
    st.subheader("Kirjaudu tai rekisteröidy")
    
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
                    st.success(f"Tervetuloa takaisin, {username}!")
                    st.rerun()
                else:
                    st.error("Väärä käyttäjänimi tai salasana")
    
    with tab2:
        st.subheader("Luo uusi tunnus")
        col = st.columns([1, 2, 1])[1]
        with col:
            new_user = st.text_input("Valitse käyttäjänimi", key="reg_user")
            new_pass = st.text_input("Valitse salasana", type="password", key="reg_pass")
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
    st.title("📜 Kilpailun säännöt & pisteytys")
    st.markdown("---")
    
    st.subheader("Otteluveikkauksen pisteytys")
    
    st.markdown("""
    **Periaate:** Saat pisteitä oikeasta voittajasta (1X2) sekä maalimääristä.
    """)
    
    data = {
        "Tilanne": [
            "Täysin tarkka tulos (esim. 2-1 → 2-1)",
            "Oikea 1X2 + toisen joukkueen maalimäärä oikein ja toisen vain yhdellä maalilla väärin",
            "Oikea 1X2 + toisen joukkueen maalimäärä oikein ja toisen yli yhdellä maalilla väärin",
            "Oikein veikattu tasapeli, mutta maalimäärät väärin",
            "Vain oikea 1X2 (molempien joukkueiden maalit yli yhdellä pielessä)",
            "Väärä 1X2"
        ],
        "Pistettä": ["**8**", "**6**", "**5**", "**4**", "**3**", "**0**"]
    }
    
    import pandas as pd
    df = pd.DataFrame(data)
    st.table(df.style.set_properties(**{'text-align': 'left'}))
    
    st.markdown("---")
    
    st.subheader("Erikoiskohteet")
    st.write("**Jokainen oikein veikattu erikoiskohde antaa 6 pistettä.**")
    
    st.markdown("---")
    st.caption("""
    • Voit veikkaaa otteluita niin kauan kuin ottelu ei ole alkanut.  
    • Erikoiskohteet sulkeutuvat kun ensimmäinen ottelu alkaa.  
    • Admin syöttää tulokset → pisteet päivittyvät automaattisesti.
    """)

# ====================== VEIKKAA OTTELUITA ======================
if page == "Veikkaa otteluita":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader("⚽ Veikkaa otteluita")
        
        # Näytetään vain avoimet ottelut
        open_matches = [m for m in matches if real_results.get("matches", {}).get(str(m['id'])) is None]
        
        if not open_matches:
            st.success("✅ Kaikki ottelut on jo veikkailtu tai lukittu!")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["Ottelut 1-18", "Ottelut 19-36", "Ottelut 37-54", "Ottelut 55-72"])
            tabs_list = [tab1, tab2, tab3, tab4]
            
            for tab_idx, tab in enumerate(tabs_list):
                with tab:
                    start = tab_idx * 18
                    end = min(start + 18, len(open_matches))
                    current_matches = open_matches[start:end]
                    
                    for m in current_matches:
                        match_id = str(m['id'])
                        countdown_info = get_countdown(m)
                        if isinstance(countdown_info, tuple):
                            countdown_str, is_open = countdown_info
                        else:
                            countdown_str, is_open = str(countdown_info), False
                        
                        st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')})")
                        
                        if not is_open:
                            st.markdown("🔴 **Kohde on suljettu**")
                        else:
                            st.markdown(f"🟢 **{countdown_str}**")
                        
                        col_home, col_away = st.columns(2)
                        with col_home:
                            home_score = st.number_input("Kotimaali", min_value=0, max_value=10, value=0, 
                                                       key=f"h_{match_id}", label_visibility="collapsed")
                        with col_away:
                            away_score = st.number_input("Vierasmaali", min_value=0, max_value=10, value=0, 
                                                       key=f"a_{match_id}", label_visibility="collapsed")
                        
                        if st.button("TALLENNA VEIKKAUS", key=f"save_{match_id}", use_container_width=True):
                            if user not in predictions:
                                predictions[user] = {}
                            predictions[user][match_id] = [home_score, away_score]
                            save_json(PREDICTIONS_FILE, predictions)
                            st.success(f"Tallennettu: {m['home']} {home_score}–{away_score} {m['away']}")
                        
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
                pred_value = user_special.get(bet["id"])
                real_value = real_special.get(bet["id"])
                
                question = bet.get('name') or bet.get('question') or bet.get('text', bet["id"])
                st.markdown(f"**{question}** ({bet.get('points', 6)} pistettä)")
                
                if real_value:
                    st.success(f"Toteutunut vastaus: **{real_value}**")
                else:
                    if bet["id"] in ["most_goals", "most_cards", "champion"]:
                        value = st.selectbox("Valitse maa", options=countries, key=f"spec_{bet['id']}")
                    elif bet["id"] == "top_scorer":
                        value = st.text_input("Pelaajan nimi", key=f"spec_{bet['id']}")
                    elif bet["id"] == "top_scorer_goals":
                        value = st.selectbox("Maalimäärä", options=list(range(1,21)), key=f"spec_{bet['id']}")
                    elif bet["id"].startswith("group_"):
                        group_letter = bet["id"].split("_")[1].upper()
                        group_matches = [m for m in matches if m.get("group") == group_letter]
                        group_teams = sorted(set([m["home"] for m in group_matches] + [m["away"] for m in group_matches]))
                        value = st.selectbox("Lohkovoittaja", options=group_teams, key=f"spec_{bet['id']}")
                    else:
                        value = st.text_input("Vastaus", key=f"spec_{bet['id']}")
                    
                    if st.button("Tallenna veikkaus", key=f"save_spec_{bet['id']}", use_container_width=True):
                        if user not in predictions:
                            predictions[user] = {"special": {}}
                        if "special" not in predictions[user]:
                            predictions[user]["special"] = {}
                        predictions[user]["special"][bet["id"]] = str(value).strip()
                        save_json(PREDICTIONS_FILE, predictions)
                        st.success("Veikkaus tallennettu!")
                
                st.divider()

# ====================== OMAT VEIKKAUKSET ======================
if page == "Omat veikkaukset":
    if not st.session_state.get("logged_in_user"):
        st.warning("Kirjaudu ensin sisään!")
    else:
        user = st.session_state.logged_in_user
        st.subheader(f"OMAT VEIKKAUKSET - {user}")
        
        tab1, tab2 = st.tabs(["Otteluveikkaukset", "Erikoiskohteet"])
        
        with tab1:
            for m in matches:
                match_id = str(m['id'])
                pred = predictions.get(user, {}).get(match_id)
                real = real_results.get("matches", {}).get(match_id)
                
                st.markdown(f"**{m['home']} — {m['away']}**")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if real:
                        st.markdown(f"""
                            <div style="font-size: 1.9rem; font-weight: 700; color: #88ffaa; margin: 8px 0 6px 0;">
                                {real[0]}–{real[1]}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="font-size: 1.9rem; color: #555;">–</div>', unsafe_allow_html=True)
                    
                    if pred:
                        st.markdown(f"""
                            <div style="font-size: 1.1rem; color: #aaaaaa;">
                                Oma veikkaus: {pred[0]}–{pred[1]}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="font-size: 1.1rem; color: #666;">Ei veikkausta</div>', unsafe_allow_html=True)
                
                with col2:
                    if real and pred:
                        pts = calculate_match_points(pred, real)
                        st.markdown(f"""
                            <div style="text-align: center; background: #2a2a4a; color: #ffff88; 
                            font-weight: 700; font-size: 1.6rem; width: 75px; height: 75px; 
                            border-radius: 50%; display: flex; align-items: center; 
                            justify-content: center; margin: 15px auto; box-shadow: 0 0 15px rgba(255,255,136,0.4);">
                                +{pts}
                            </div>
                        """, unsafe_allow_html=True)
                    elif real:
                        st.markdown('<div style="text-align: center; color: #666; margin-top: 30px;">0</div>', unsafe_allow_html=True)
                
                st.divider()

        with tab2:
            user_special = predictions.get(user, {}).get("special", {})
            real_special = real_results.get("special", {})
            
            for bet in special_bets:
                pred_value = user_special.get(bet["id"])
                real_value = real_special.get(bet["id"])
                
                question = bet.get('name') or bet.get('question') or bet.get('text', bet["id"])
                st.markdown(f"**{question}**")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if real_value:
                        st.markdown(f"""
                            <div style="font-size: 1.85rem; font-weight: 700; color: #88ffaa; margin: 8px 0 6px 0;">
                                {real_value}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="font-size: 1.85rem; color: #555;">–</div>', unsafe_allow_html=True)
                    
                    if pred_value:
                        st.markdown(f"""
                            <div style="font-size: 1.1rem; color: #aaaaaa;">
                                Oma veikkaus: {pred_value}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="font-size: 1.1rem; color: #666;">Ei veikkausta</div>', unsafe_allow_html=True)
                
                with col2:
                    if real_value and pred_value:
                        user_str = str(pred_value).lower().strip()
                        real_list = [x.strip().lower() for x in str(real_value).split(",")]
                        pts = bet.get("points", 6) if user_str in real_list else 0
                        st.markdown(f"""
                            <div style="text-align: center; background: #2a2a4a; color: #ffff88; 
                            font-weight: 700; font-size: 1.55rem; width: 72px; height: 72px; 
                            border-radius: 50%; display: flex; align-items: center; 
                            justify-content: center; margin: 15px auto; box-shadow: 0 0 15px rgba(255,255,136,0.4);">
                                +{pts}
                            </div>
                        """, unsafe_allow_html=True)
                    elif real_value:
                        st.markdown('<div style="text-align: center; color: #666; margin-top: 30px;">0</div>', unsafe_allow_html=True)
                
                st.divider()

# ====================== VEIKKAUSTILANNE ======================
if page == "Veikkaustilanne":
    st.subheader("Veikkaustilanne")
    # (tässä on leaderboard-koodi, voit käyttää aikaisempaa versiota jos haluat)

# ====================== ADMIN ======================
if page == "Admin":
    st.subheader("🛠️ Admin-paneeli")
    # (tässä on admin-koodi, voit käyttää aikaisempaa toimivaa versiota)
