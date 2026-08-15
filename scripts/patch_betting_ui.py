from pathlib import Path
import re

path = Path('mm_veikkaus.py')
text = path.read_text(encoding='utf-8')

new_1x2 = '''        def render_1x2_match(m, prefix, settings, all_matches):
            now = datetime.now(HELSINKI)
            is_closed = now >= m["start"]
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = bool(saved and ("mark_opts" in saved or "mark" in saved))
            token_limit = int(settings.get("double_marks", 0))
            used = player_token_count(all_matches, "double_mark", m["id"])

            title_color = "#94a3b8" if is_closed else "#f1f5f9"
            closed_badge = ' <span style="background:#334155;color:#f87171;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔒 SULJETTU</span>' if is_closed else ""
            token_badge = ' <span style="background:#2563eb;color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔀 TUPLAMERKKI</span>' if saved and len(saved.get("mark_opts", [])) == 2 else ""
            st.markdown(
                f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:{title_color};">{m["home"]} – {m["away"]}</span>{token_badge}{closed_badge}</div>'
                f'<div style="font-size:0.88rem;color:#94a3b8;margin-bottom:2px;">{m["aika"]}</div>', unsafe_allow_html=True
            )
            if not is_closed:
                render_countdown(m["id"], m["start"])

            with st.container(border=True):
                if is_closed:
                    if has:
                        opts = saved.get("mark_opts", [saved.get("mark", "X")])
                        st.markdown(
                            f'<div style="text-align:center;background:#0f172a;border:1px solid #334155;border-radius:12px;padding:16px;">'
                            f'<div style="font-size:0.72rem;color:#94a3b8;margin-bottom:6px;">TALLENNETTU VEIKKAUS</div>'
                            f'<div style="font-size:1.55rem;font-weight:700;color:#94a3b8;">{"  /  ".join(opts)}</div></div>', unsafe_allow_html=True
                        )
                    else:
                        st.info("Ei veikkausta")
                else:
                    saved_opts = saved.get("mark_opts", []) if saved else []
                    if not saved_opts and saved and saved.get("mark"):
                        saved_opts = [saved.get("mark")]
                    saved_opts = [x for x in ["1", "X", "2"] if x in saved_opts]
                    use_double = bool(saved_opts and len(saved_opts) == 2)
                    if token_limit:
                        use_double = st.checkbox(
                            "Käytä tuplamerkki",
                            value=use_double,
                            key=f"{prefix}_{m['id']}_double_mark",
                            help="Tuplamerkki käyttää yhden käytettävissä olevan tuplamerkin ja sallii kaksi valintaa tässä kohteessa."
                        )
                    if use_double:
                        default_opts = saved_opts[:2] if len(saved_opts) == 2 else saved_opts[:1]
                        try:
                            opts = st.pills("Valitse kaksi merkkiä", ["1", "X", "2"], selection_mode="multi", default=default_opts, key=f"{prefix}_{m['id']}_marks") or []
                        except (AttributeError, TypeError):
                            opts = st.multiselect("Valitse kaksi merkkiä", ["1", "X", "2"], default=default_opts, max_selections=2, key=f"{prefix}_{m['id']}_marks")
                        st.caption(f"Valittu {len(opts)}/2 merkkiä · Tuplamerkkejä käytetty {used}/{token_limit}")
                    else:
                        default_one = saved_opts[0] if saved_opts else "X"
                        try:
                            opts = st.pills("Valitse merkki", ["1", "X", "2"], selection_mode="single", default=default_one, key=f"{prefix}_{m['id']}_mark")
                        except (AttributeError, TypeError):
                            opts = st.radio("Valitse merkki", ["1", "X", "2"], index=["1", "X", "2"].index(default_one), horizontal=True, key=f"{prefix}_{m['id']}_mark")
                        opts = [opts] if opts else []
                        if token_limit:
                            st.caption(f"Tuplamerkkejä käytetty {used}/{token_limit}")

                    if st.button("Päivitä veikkaus" if has else "Tallenna veikkaus", type="secondary" if has else "primary", key=f"{prefix}_save_{m['id']}", use_container_width=True):
                        current_used = player_token_count(all_matches, "double_mark", m["id"])
                        if len(opts) == 0:
                            st.error("Valitse 1, X tai 2.")
                        elif len(opts) > 2:
                            st.error("Valitse enintään kaksi merkkiä.")
                        elif len(opts) == 2 and not use_double:
                            st.error("Kahden merkin valinta vaatii tuplamerkin.")
                        elif len(opts) == 2 and current_used >= token_limit and not (saved and len(saved.get("mark_opts", [])) == 2):
                            st.error(f"Olet jo käyttänyt kaikki {token_limit} tuplamerkkiä.")
                        elif use_double and len(opts) != 2:
                            st.error("Valitse tuplamerkillä tasan kaksi merkkiä.")
                        else:
                            ordered = sorted(set(opts), key=["1", "X", "2"].index)
                            save_prediction(st.session_state.logged_in_user, m["id"], {"kind":"1x2", "mark_opts": ordered})
                            clear_points_cache(); st.toast("Veikkaus tallennettu!"); st.rerun()
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
'''

new_moni = '''        def render_moniveto_match(m, prefix, settings, all_matches, nhl_mode=False):
            now = datetime.now(HELSINKI)
            is_closed = now >= m["start"]
            saved = load_prediction(st.session_state.logged_in_user, m["id"])
            has = bool(saved and saved.get("kind") in ("moniveto", "nhl") and saved.get("score_opts"))
            token_limit = int(settings.get("joker_count", 0))
            used = player_token_count(all_matches, "joker", m["id"])
            title_color = "#94a3b8" if is_closed else "#f1f5f9"
            closed_badge = ' <span style="background:#334155;color:#f87171;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🔒 SULJETTU</span>' if is_closed else ""
            joker_badge = ' <span style="background:#a855f7;color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-left:8px;">🃏 JOKERI</span>' if saved and saved.get("joker") else ""
            st.markdown(f'<div style="margin-bottom:4px;"><span style="font-size:1.25rem;font-weight:700;color:{title_color};">{m["home"]} – {m["away"]}</span>{joker_badge}{closed_badge}</div><div style="font-size:0.88rem;color:#94a3b8;margin-bottom:2px;">{m["aika"]}</div>', unsafe_allow_html=True)
            if not is_closed:
                render_countdown(m["id"], m["start"])

            list_type = str(settings.get("pred_type") or "").lower()
            base_count = 2 if list_type == "moniveto_football" else 4
            if nhl_mode or list_type in ("moniveto", "moniveto_hockey", "nhl"):
                base_count = 4

            with st.container(border=True):
                if is_closed:
                    if has:
                        labels = [f"{h}–{a}" for h, a in saved.get("score_opts", [])]
                        mark_text = f" · 1X2: {saved.get('mark')}" if nhl_mode and saved.get("mark") else ""
                        joker_text = " · 🃏 Jokeri" if saved.get("joker") else ""
                        st.markdown(f'<div style="text-align:center;background:#0f172a;border:1px solid #334155;border-radius:12px;padding:14px;"><div style="font-size:1rem;font-weight:700;">Moniveto{mark_text}</div><div style="color:#22c55e;margin-top:5px;">{", ".join(labels)}</div><div style="color:#a855f7;margin-top:5px;">{joker_text}</div></div>', unsafe_allow_html=True)
                    else:
                        st.info("Ei veikkausta")
                else:
                    joker_value = bool(saved.get("joker")) if saved else False
                    if token_limit:
                        joker_value = st.checkbox(f"🃏 Jokeri tässä kohteessa ({used}/{token_limit} käytetty)", value=joker_value, key=f"{prefix}_{m['id']}_joker", help="Jokeri on pelaajan oma valinta. Ylläpitäjä määrittää vain jokerien kokonaismäärän.")
                    allowed_count = base_count + (1 if joker_value else 0)
                    mark = None
                    if nhl_mode:
                        saved_mark = saved.get("mark", "X") if saved else "X"
                        try:
                            mark = st.pills("1X2", ["1", "X", "2"], selection_mode="single", default=saved_mark, key=f"{prefix}_{m['id']}_mark")
                        except (AttributeError, TypeError):
                            mark = st.radio("1X2", ["1", "X", "2"], index=["1", "X", "2"].index(saved_mark), horizontal=True, key=f"{prefix}_{m['id']}_mark")

                    saved_scores = [f"{h}-{a}" for h, a in (saved.get("score_opts", []) if saved else [])]
                    default_text = ", ".join(saved_scores[:allowed_count])
                    score_text = st.text_input(f"Kirjoita {allowed_count} tarkkaa tulosta", value=default_text, placeholder="esim. 2-1, 3-1, 2-0, 1-0", key=f"{prefix}_{m['id']}_scores_text", help="Kirjoita tulokset pilkuilla eroteltuna. Esimerkiksi 2-1, 3-1, 2-0, 1-0.")
                    st.caption(f"Tarvitaan tasan {allowed_count} tulosta. Erottele tulokset pilkuilla.")

                    if st.button("Päivitä veikkaus" if has else "Tallenna veikkaus", type="secondary" if has else "primary", key=f"{prefix}_save_{m['id']}", use_container_width=True):
                        current_used = player_token_count(all_matches, "joker", m["id"])
                        if joker_value and current_used >= token_limit and not (saved and saved.get("joker")):
                            st.error(f"Olet jo käyttänyt kaikki {token_limit} jokeria.")
                        else:
                            raw_parts = [p.strip() for p in re.split(r"[,;\\n]+", score_text) if p.strip()]
                            parsed = []
                            invalid = []
                            for part in raw_parts:
                                mm = re.fullmatch(r"(\\d+)\\s*[-–:]\\s*(\\d+)", part)
                                if not mm:
                                    invalid.append(part)
                                else:
                                    parsed.append((int(mm.group(1)), int(mm.group(2))))
                            parsed = list(dict.fromkeys(parsed))
                            if invalid:
                                st.error("Virheellinen tulosmuoto: " + ", ".join(invalid) + ". Käytä esimerkiksi 2-1.")
                            elif len(parsed) != allowed_count:
                                st.error(f"Kirjoita tasan {allowed_count} eri tulosta.")
                            else:
                                pred = {"kind":"nhl" if nhl_mode else "moniveto", "score_opts": parsed, "joker": bool(joker_value)}
                                if nhl_mode:
                                    pred["mark"] = mark
                                save_prediction(st.session_state.logged_in_user, m["id"], pred)
                                clear_points_cache(); st.toast("Veikkaus tallennettu!"); st.rerun()
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
'''

p1 = r'        def render_1x2_match\(.*?(?=\n        def render_moniveto_match\()'
p2 = r'        def render_moniveto_match\(.*?(?=\n        for ti, \(name, matches\) in enumerate\(all_lists\):)'
text, n1 = re.subn(p1, lambda m: new_1x2 + '\n', text, count=1, flags=re.S)
if n1 != 1:
    raise SystemExit('1X2 block not found')
text, n2 = re.subn(p2, lambda m: new_moni + '\n', text, count=1, flags=re.S)
if n2 != 1:
    raise SystemExit('Moniveto block not found')
path.write_text(text, encoding='utf-8')
print('patched', n1, n2)
