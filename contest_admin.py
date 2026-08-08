import re


def render_contest_admin(st, get_db, clear_matches_cache, clear_points_cache):
    """Admin UI for creating and editing contest/list settings."""
    st.write("### 🏆 Kisojen hallinta")
    st.caption("Luo uusi veikkauslista ja määritä sen perusasetukset. Ottelut lisätään tämän jälkeen Otteluiden hallinta -osiossa.")

    with get_db() as conn:
        rows = conn.execute(
            "SELECT list_key, list_name, pred_type, double_points, double_marks, joker_count "
            "FROM list_settings ORDER BY sort_order, list_key"
        ).fetchall()

    st.write("#### Nykyiset kisat")
    if not rows:
        st.info("Ei vielä erikseen määriteltyjä kisoja.")
    else:
        for row in rows:
            key = row["list_key"]
            with st.expander(f"{row['list_name']} · {key}"):
                st.caption(
                    f"Tyyppi: {row['pred_type']} · "
                    f"Tuplapisteet: {'käytössä' if row['double_points'] else 'ei käytössä'} · "
                    f"Tuplakohteita: {row['double_marks']} · Jokerit: {row['joker_count']}"
                )
                ec1, ec2, ec3 = st.columns([2, 1, 1])
                with ec1:
                    new_name = st.text_input("Nimi", value=row["list_name"], key=f"contest_name_{key}")
                with ec2:
                    new_double = st.checkbox(
                        "Tuplapisteet",
                        value=bool(row["double_points"]),
                        key=f"contest_double_{key}",
                    )
                with ec3:
                    new_marks = st.number_input(
                        "Tuplakohteita",
                        min_value=0,
                        max_value=99,
                        value=int(row["double_marks"]),
                        step=1,
                        key=f"contest_marks_{key}",
                    )
                new_jokers = st.number_input(
                    "Jokereita",
                    min_value=0,
                    max_value=99,
                    value=int(row["joker_count"]),
                    step=1,
                    key=f"contest_jokers_{key}",
                )
                if st.button("Tallenna asetukset", key=f"contest_save_{key}", type="primary"):
                    if not new_name.strip():
                        st.error("Kisan nimi ei voi olla tyhjä.")
                    elif not new_double and new_marks > 0:
                        st.error("Tuplakohteiden määrä voi olla yli 0 vain, jos tuplapisteet ovat käytössä.")
                    else:
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE list_settings SET list_name=?, double_points=?, double_marks=?, joker_count=? WHERE list_key=?",
                                (new_name.strip(), 1 if new_double else 0, int(new_marks), int(new_jokers), key),
                            )
                            conn.execute(
                                "UPDATE matches SET list_name=? WHERE list_key=?",
                                (new_name.strip(), key),
                            )
                        clear_matches_cache()
                        clear_points_cache()
                        st.success("Kisan asetukset tallennettu.")
                        st.rerun()

    st.markdown("---")
    st.write("#### ➕ Luo uusi kisa")
    with st.form("create_contest_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            list_key = st.text_input(
                "Kisan avain",
                placeholder="esim. liiga2",
                help="Tekninen yksilöllinen tunniste. Käytä pieniä kirjaimia, numeroita, alaviivaa tai yhdysmerkkiä.",
            )
            list_name = st.text_input("Kisan nimi", placeholder="esim. Lokakuun palloilupaketti")
        with c2:
            pred_type = st.selectbox("Veikkaustyyppi", ["normal", "nhl"], format_func=lambda x: "Normaali tulos" if x == "normal" else "NHL 1X2 + moniveto")
            double_points = st.checkbox("Tuplapisteet käytössä", value=True)
            double_marks = st.number_input("Tuplakohteiden määrä", min_value=0, max_value=99, value=1, step=1)
            joker_count = st.number_input("Jokereiden määrä", min_value=0, max_value=99, value=0, step=1)
        submitted = st.form_submit_button("🚀 Luo uusi kisa", type="primary", use_container_width=True)

    if submitted:
        key = list_key.strip().lower()
        name = list_name.strip()
        if not re.fullmatch(r"[a-z0-9_-]{2,40}", key):
            st.error("Kisan avaimen pitää olla 2–40 merkkiä ja sisältää vain a–z, 0–9, _ tai -.")
        elif not name:
            st.error("Anna kisalle nimi.")
        elif not double_points and double_marks > 0:
            st.error("Tuplakohteiden määrä voi olla yli 0 vain, jos tuplapisteet ovat käytössä.")
        else:
            try:
                with get_db() as conn:
                    exists = conn.execute("SELECT 1 FROM list_settings WHERE list_key=?", (key,)).fetchone()
                    if exists:
                        st.error(f"Kisan avain '{key}' on jo käytössä.")
                    else:
                        max_order = conn.execute(
                            "SELECT COALESCE(MAX(sort_order), 0) FROM list_settings"
                        ).fetchone()[0]
                        conn.execute(
                            "INSERT INTO list_settings "
                            "(list_key, list_name, pred_type, double_points, double_marks, joker_count, sort_order) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (key, name, pred_type, 1 if double_points else 0, int(double_marks), int(joker_count), int(max_order) + 1),
                        )
                        clear_matches_cache()
                        clear_points_cache()
                        st.success(f"✅ Kisa '{name}' luotu. Lisää nyt ottelut Otteluiden hallinta -osiossa.")
                        st.rerun()
            except Exception as e:
                st.error(f"Kisan luonti epäonnistui: {e}")
