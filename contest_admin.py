import re


def render_contest_admin(st, get_db, clear_matches_cache, clear_points_cache):
    st.write("### 🏆 Kisojen hallinta")
    st.caption("Luo ja hallitse veikkauslistoja. Jokaisella listalla on yksi pelityyppi.")

    with get_db() as conn:
        for col, ddl in [("list_name", "TEXT DEFAULT ''"), ("pred_type", "TEXT DEFAULT 'normal'"), ("sort_order", "INTEGER DEFAULT 0")]:
            try:
                conn.execute(f"ALTER TABLE list_settings ADD COLUMN {col} {ddl}")
            except Exception:
                pass
        conn.commit()

    with get_db() as conn:
        conn.execute("UPDATE list_settings SET double_marks=0, joker_count=0 WHERE COALESCE(pred_type,'normal')='normal'")
        conn.execute("UPDATE list_settings SET double_points=0, joker_count=0 WHERE COALESCE(pred_type,'normal')='1x2'")
        conn.execute("UPDATE list_settings SET double_points=0, double_marks=0 WHERE COALESCE(pred_type,'normal') IN ('moniveto','moniveto_hockey','moniveto_football','nhl')")
        conn.commit()

    with get_db() as conn:
        rows = conn.execute("SELECT list_key, COALESCE(list_name,'') AS list_name, COALESCE(pred_type,'normal') AS pred_type, double_points, double_marks, joker_count, COALESCE(sort_order,0) AS sort_order FROM list_settings ORDER BY sort_order, list_key").fetchall()

    labels = {
        "normal": "Tulosveto",
        "1x2": "1X2",
        "moniveto": "Moniveto – jääkiekko",
        "moniveto_hockey": "Moniveto – jääkiekko",
        "moniveto_football": "Moniveto – jalkapallo",
        "nhl": "NHL 1X2 + Moniveto",
    }

    with st.expander("➕ Luo uusi lista", expanded=True):
        pred_type = st.selectbox("Pelityyppi", list(labels), format_func=lambda x: labels[x], key="new_contest_pred_type")
        with st.form("create_contest_form", clear_on_submit=True):
            name = st.text_input("Listan nimi", placeholder="esim. Lauantain NHL-moniveto")
            key = st.text_input("Listan tunnus", placeholder="esim. nhl_la")
            double_points = st.number_input("Tuplapistekohteiden määrä", min_value=0, value=0, step=1) if pred_type == "normal" else 0
            double_marks = st.number_input("Tuplamerkkien määrä", min_value=0, value=0, step=1) if pred_type == "1x2" else 0
            joker_count = st.number_input("Jokereiden määrä", min_value=0, value=0, step=1) if pred_type in ("moniveto", "moniveto_hockey", "moniveto_football", "nhl") else 0
            sort_order = st.number_input("Järjestys", min_value=0, value=len(rows) + 1, step=1)
            if st.form_submit_button("Luo lista", type="primary", use_container_width=True):
                clean_key = re.sub(r"[^a-zA-Z0-9_-]", "", key.strip())
                clean_name = name.strip()
                if not clean_key or not clean_name:
                    st.error("Anna sekä listan nimi että tunnus.")
                else:
                    with get_db() as conn:
                        exists = conn.execute("SELECT 1 FROM list_settings WHERE list_key=?", (clean_key,)).fetchone()
                        if exists:
                            st.error(f"Listan tunnus '{clean_key}' on jo käytössä.")
                        else:
                            conn.execute("INSERT INTO list_settings (list_key,list_name,pred_type,double_points,double_marks,joker_count,sort_order) VALUES (?,?,?,?,?,?,?)", (clean_key, clean_name, pred_type, int(double_points) if pred_type == "normal" else 0, int(double_marks) if pred_type == "1x2" else 0, int(joker_count) if pred_type in ("moniveto","moniveto_hockey","moniveto_football","nhl") else 0, int(sort_order)))
                            conn.commit(); clear_matches_cache(); clear_points_cache(); st.success(f"Lista luotu: {clean_name}"); st.rerun()

    st.markdown("---")
    st.write("#### Nykyiset listat")
    if not rows:
        st.info("Ei vielä erikseen luotuja listoja.")
    else:
        for row in rows:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{row['list_name'] or row['list_key']}**")
                    st.caption(f"Tunnus: `{row['list_key']}` · Tyyppi: {labels.get(row['pred_type'], row['pred_type'])}")
                with c2:
                    if row['pred_type'] == 'normal': txt = f"Tuplapistekohteita: {row['double_points']}"
                    elif row['pred_type'] == '1x2': txt = f"Tuplamerkkejä: {row['double_marks']}"
                    else: txt = f"Jokereita: {row['joker_count']}"
                    st.caption(txt)
                with c3:
                    if st.button("Poista", key=f"delete_contest_{row['list_key']}"):
                        with get_db() as conn: conn.execute("DELETE FROM list_settings WHERE list_key=?", (row['list_key'],))
                        clear_matches_cache(); clear_points_cache(); st.rerun()
