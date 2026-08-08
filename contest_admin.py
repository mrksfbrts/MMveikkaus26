import re


def render_contest_admin(st, get_db, clear_matches_cache, clear_points_cache):
    st.write("### 🏆 Kisojen hallinta")
    st.caption("Luo ja hallitse veikkauskisoja. Muutokset tehdään vain tähän Kehitys-versioon.")

    with get_db() as conn:
        for col, ddl in [
            ("list_name", "TEXT DEFAULT ''"),
            ("pred_type", "TEXT DEFAULT 'normal'"),
            ("sort_order", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE list_settings ADD COLUMN {col} {ddl}")
            except Exception:
                pass
        conn.commit()

    with get_db() as conn:
        rows = conn.execute(
            "SELECT list_key, COALESCE(list_name,'') AS list_name, COALESCE(pred_type,'normal') AS pred_type, "
            "double_points, double_marks, joker_count, COALESCE(sort_order,0) AS sort_order "
            "FROM list_settings ORDER BY sort_order, list_key"
        ).fetchall()

    with st.expander("➕ Luo uusi kisa", expanded=True):
        with st.form("create_contest_form", clear_on_submit=True):
            name = st.text_input("Kisan nimi", placeholder="esim. Lauantain NHL-moniveto")
            key = st.text_input("Kisan tunnus", placeholder="esim. nhl_la")
            pred_type = st.selectbox(
                "Veikkaustyyppi",
                ["normal", "1x2", "moniveto", "nhl"],
                format_func=lambda x: {
                    "normal": "Tulosveto",
                    "1x2": "1X2",
                    "moniveto": "Moniveto",
                    "nhl": "NHL 1X2 + Moniveto",
                }[x],
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                double_points = st.checkbox("Tuplapisteet käytössä", value=False)
            with c2:
                double_marks = st.number_input("Tuplakohteiden määrä", min_value=0, value=0, step=1)
            with c3:
                joker_count = 0
                if pred_type in ("moniveto", "nhl"):
                    joker_count = st.number_input("Jokereiden määrä", min_value=0, value=0, step=1)
                else:
                    st.caption("Jokereita ei käytetä tässä veikkaustyypissä.")

            sort_order = st.number_input("Järjestys", min_value=0, value=len(rows) + 1, step=1)

            if st.form_submit_button("Luo kisa", type="primary", use_container_width=True):
                clean_key = re.sub(r"[^a-zA-Z0-9_-]", "", key.strip())
                clean_name = name.strip()
                if not clean_key or not clean_name:
                    st.error("Anna sekä kisan nimi että tunnus.")
                else:
                    # Varmistetaan myös palvelinpuolella, ettei väärä arvo pääse
                    # tietokantaan, vaikka lomakkeen käyttöliittymä joskus muuttuisi.
                    safe_joker_count = int(joker_count) if pred_type in ("moniveto", "nhl") else 0
                    safe_double_marks = int(double_marks) if double_points else 0

                    with get_db() as conn:
                        exists = conn.execute("SELECT 1 FROM list_settings WHERE list_key=?", (clean_key,)).fetchone()
                        if exists:
                            st.error(f"Kisan tunnus '{clean_key}' on jo käytössä.")
                        else:
                            conn.execute(
                                "INSERT INTO list_settings (list_key,list_name,pred_type,double_points,double_marks,joker_count,sort_order) VALUES (?,?,?,?,?,?,?)",
                                (clean_key, clean_name, pred_type, int(double_points), safe_double_marks, safe_joker_count, int(sort_order)),
                            )
                            conn.commit()
                            clear_matches_cache()
                            clear_points_cache()
                            st.success(f"Kisa luotu: {clean_name}")
                            st.rerun()

    st.markdown("---")
    st.write("#### Nykyiset kisat")
    if not rows:
        st.info("Ei vielä erikseen luotuja kisoja.")
    else:
        for row in rows:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{row['list_name'] or row['list_key']}**")
                    st.caption(f"Tunnus: `{row['list_key']}` · Tyyppi: {row['pred_type']}")
                with c2:
                    st.caption(
                        f"Tuplapisteet: {'kyllä' if row['double_points'] else 'ei'} · "
                        f"Tuplakohteita: {row['double_marks']} · Jokereita: {row['joker_count']}"
                    )
                with c3:
                    if st.button("Poista", key=f"delete_contest_{row['list_key']}"):
                        with get_db() as conn:
                            conn.execute("DELETE FROM list_settings WHERE list_key=?", (row['list_key'],))
                        clear_matches_cache()
                        clear_points_cache()
                        st.toast("Kisa poistettu")
                        st.rerun()
