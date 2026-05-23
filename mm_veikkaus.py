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
    {"id": "most_goals", "name": "1. Mikä maa tekee alkulohkoissa eniten maaleja?", "points": 5, "type": "select"},
    {"id": "most_cards", "name": "2. Mikä maa saa alkulohkoissa eniten varoituksia?", "points": 5, "type": "select"},
    {"id": "top_scorer", "name": "3. Paras maalintekijä", "points": 10, "type": "text"},
    {"id": "top_scorer_goals", "name": "4. Millä maalimäärällä voitetaan maalintekijäkuninkuus?", "points": 5, "type": "number"},
    {"id": "champion", "name": "5. Maailmanmestari", "points": 10, "type": "select"},
]

for letter in "ABCDEFGHIJKL":
    special_bets.append({"id": f"group_{letter.lower()}", "name": f"Lohko {letter} voittaja", "points": 3, "type": "select"})

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
    """
    pred ja real ovat listoja: [kotimaali, vierasmaali]
    """
    if not pred or not real:
        return 0
    
    p_home, p_away = pred
    r_home, r_away = real
    
    # 1. Täysin oikein
    if p_home == r_home and p_away == r_away:
        return 8
    
    # Oikea voittaja?
    p_winner = 0 if p_home > p_away else 1 if p_home < p_away else 2
    r_winner = 0 if r_home > r_away else 1 if r_home < r_away else 2
    
    if p_winner != r_winner:
        return 0  # Väärä voittaja = 0 pistettä
    
    # ====================== OIKEA VOITTAJA ======================
    
    # 2. Väärä tasapeli (veikkasit tasapelin, mutta väärä maalimäärä)
    if p_winner == 2:
        return 4
    
    # Oikea voittaja, lasketaan maaliero
    home_diff = abs(p_home - r_home)
    away_diff = abs(p_away - r_away)
    
    # 3. 6 pistettä: toisen joukkueen maalit täysin oikein, toisen vain yhdellä väärin
    if (home_diff == 0 and away_diff == 1) or (home_diff == 1 and away_diff == 0):
        return 6
    
    # 4. 5 pistettä: vain toisen joukkueen maalit oikein (toinen ero >1)
    if home_diff == 0 or away_diff == 0:
        return 5
    
    # 5. 3 pistettä: vain oikea voittaja, molemmat maalimäärät väärin
    return 3



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
    Pisteitä saa ainoastaan, kun on veikannut oikeaa tulosta (1X2). Lopullisen veikkauskohteen pistemäärän määrittelee se, kuinka lähelle oikeaa tulosta veikkasit. 
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
    Yksittäinen veikkauskohde/ottelu sulkeutuu aina 15 minuuttia ennen pelin alkamista. Voit muokata omaa veikkaustasi siihen asti aivan vapaasti. Kun kohde sulkeutuu se poistuu veikattavien kohteiden listalta ja ylimpänä näkyy aina seuraavaksi sulkeutuva kohde. Erikoiskohteet sulkeutuvat kaikki samanaikaisesti 15 minuuttia ennen kisojen ensimmäisen pelin alkua. Pisteet päivittyvät automaattisesti. Näet omat veikkauksesi heti valikon kohdasta "Omat veikkaukset" kun olet ne veikannut, kaikkien muiden veikkaukset tulevat vertailtavaksi näkyviin vasta kun pelikohde on mennyt kiinni ja tulos kirjattu sivulle. 
    """)


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
                            home_score = st.number_input("", 0, 10, 0, key=f"h_{match_id}")
                        with col_away:
                            away_score = st.number_input("", 0, 10, 0, key=f"a_{match_id}")
                        
                        if st.button("Tallenna veikkaus", key=f"save_{match_id}", use_container_width=True):
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
        
        # Tarkistetaan onko erikoiskohteissa YHTÄÄN lukittua tulosta
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
                    # Veikkauslomake
                    if bet["id"] in ["most_goals", "most_cards", "champion"]:
                        value = st.selectbox("Valitse maa", options=countries, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet["id"] == "top_scorer":
                        value = st.text_input("Pelaajan nimi", key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet["id"] == "top_scorer_goals":
                        value = st.selectbox("Maalimäärä", options=list(range(1,21)), 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
                    elif bet["id"].startswith("group_"):
                        group_letter = bet["id"].split("_")[1].upper()
                        group_matches = [m for m in matches if m.get("group") == group_letter]
                        group_teams = sorted(set([m["home"] for m in group_matches] + [m["away"] for m in group_matches]))
                        value = st.selectbox("Lohkovoittaja", options=group_teams, 
                                           key=f"spec_{bet_id}", label_visibility="collapsed")
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

        # ====================== TAB 2: ERIKOISKOHTEET ======================
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
                    st.markdown(f"**{m['home']} — {m['away']}** ({m.get('group', '')})")
                    st.success(f"Tulos: **{real[0]}–{real[1]}**")
                    
                    for u in sorted(users.keys()):
                        pred = predictions.get(u, {}).get(match_id)
                        if pred:
                            pts = calculate_match_points(pred, real)
                            st.markdown(f"**{u}**: {pred[0]}–{pred[1]} <span style='color:#00ff9d'>(+{pts}p)</span>", unsafe_allow_html=True)
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
                    # Suomenkielinen otsikko
                    if bet_id == "most_goals":
                        question = "Mikä maa tekee alkulohkojen peleissä eniten maaleja?"
                    elif bet_id == "most_cards":
                        question = "Mikä maa saa alkulohkojen peleissä eniten varoituksia (keltaiset + punaiset)?"
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
                        question = bet.get('question') or bet.get('text', bet_id.replace("_", " ").title())
                    
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
                                st.markdown(f"**{u}**: {user_pred} <span style='color:#00ff9d'>(+{pts})</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**{u}**: {user_pred}", unsafe_allow_html=True)
                    
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