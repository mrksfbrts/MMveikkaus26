import contextlib
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import competition_system as cs


class StopRerun(Exception):
    pass


class FakeStreamlit(types.ModuleType):
    def __init__(self, selected=None, values=None, pressed=None):
        super().__init__("streamlit")
        self.selected = selected or {}
        self.values = values or {}
        self.pressed = pressed
        self.labels = []
        self.output = []
        self.selectboxes = []

    def container(self, **kwargs):
        return contextlib.nullcontext()

    def columns(self, spec):
        return [contextlib.nullcontext() for _ in range(spec if isinstance(spec, int) else len(spec))]

    def tabs(self, labels):
        self.output.extend(labels)
        return [contextlib.nullcontext() for _ in labels]

    def markdown(self, value, **kwargs):
        self.output.append(str(value))

    def caption(self, value, **kwargs):
        self.output.append(str(value))

    def info(self, value, **kwargs):
        self.output.append(str(value))

    def success(self, value, **kwargs):
        self.output.append(str(value))

    def error(self, value, **kwargs):
        raise AssertionError(value)

    def selectbox(self, label, options, index=0, key=None, format_func=None, **kwargs):
        self.selectboxes.append((label, list(options), format_func, key))
        return self.selected.get(key, options[index])

    def number_input(self, label, *args, **kwargs):
        self.labels.append(label)
        return self.values.get(kwargs.get("key"), kwargs.get("value", args[2] if len(args) > 2 else 0))

    def button(self, label, key=None, **kwargs):
        return key == self.pressed

    def rerun(self):
        raise StopRerun()


def render_with(db_path, username, selected=None):
    fake = FakeStreamlit(selected=selected)
    with patch.dict(sys.modules, {"streamlit": fake}):
        cs.render_user_predictions(db_path, username)
    return fake


class CompetitionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "integration.db")
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.execute("INSERT INTO users VALUES('player','hash')")

    def tearDown(self):
        self.temp.cleanup()

    def test_own_predictions_results_ranking_correction_and_cancellations(self):
        old_id = cs._create_competition(self.db, "Older active", "", [{"name": "Old", "prediction_type": "hockey_score"}])
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (old_id,))
        finished_id = cs._create_competition(self.db, "Finished", "", [{"name": "History", "prediction_type": "hockey_score"}])
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='finished' WHERE id=?", (finished_id,))

        specs = [
            {"name": "Jääkiekko", "prediction_type": "hockey_score", "tuplaus": 3},
            {"name": "Jalkapallo", "prediction_type": "football_score", "tuplaus": 1},
            {"name": "1X2", "prediction_type": "result_1x2", "harava": 1},
            {"name": "Jääkiekon moniveto", "prediction_type": "hockey_multi", "jokeri": 1},
            {"name": "Jalkapallon moniveto", "prediction_type": "football_multi", "jokeri": 1},
        ]
        cid = cs._create_competition(self.db, "Testikisa", "Testikuvaus", specs)
        now = cs._now()
        targets = []
        with cs.connect(self.db) as conn:
            lists = conn.execute("SELECT * FROM competition_lists WHERE competition_id=? ORDER BY sort_order", (cid,)).fetchall()
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            for index, lst in enumerate(lists):
                start = now + timedelta(days=2)
                cur = conn.execute(
                    "INSERT INTO competition_targets(list_id,home,away,start_iso,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (lst["id"], "Home", "Away", start.isoformat(), cs._stamp(), cs._stamp()),
                )
                target_id = cur.lastrowid
                targets.append(target_id)
        predictions = [
            {"home_goals": 3, "away_goals": 1},
            {"home_goals": 2, "away_goals": 1},
            {"marks": ["1", "X"]},
            {"scores": [{"home_goals": 0, "away_goals": 0}] * 4, "mark": "1", "joker_score": {"home_goals": 5, "away_goals": 0}},
            {"scores": [{"home_goals": 0, "away_goals": 0}, {"home_goals": 1, "away_goals": 1}], "mark": "1", "joker_score": {"home_goals": 3, "away_goals": 1}},
        ]
        tokens = ["tuplaus", "tuplaus", "harava", "jokeri", "jokeri"]
        for target_id, prediction, token in zip(targets, predictions, tokens):
            cs._assign_token(self.db, "player", target_id, token)
            cs._save_prediction(self.db, "player", target_id, prediction)

        own = render_with(self.db, "player")
        self.assertIn("### Testikisa", own.output)
        self.assertTrue(all(any(spec["name"] in item for item in own.output) for spec in specs))
        self.assertEqual(5, sum(1 for item in own.output if item in {s["name"] for s in specs}))
        self.assertTrue(any("Tuplaus" in item for item in own.output))
        self.assertTrue(any("Harava" in item for item in own.output))
        self.assertTrue(any("Jokeri" in item for item in own.output))
        self.assertEqual(1, len(own.selectboxes))
        self.assertEqual([0, 1], own.selectboxes[0][1])  # finished competition excluded

        # Admin's dedicated result UI stores exact results in competition_targets.
        results = [(3, 1), (2, 1), (2, 1), (5, 0), (3, 1)]
        for index, target_id in enumerate(targets):
            with cs.connect(self.db) as conn:
                conn.execute("UPDATE competition_targets SET start_iso=? WHERE id=?", ((now - timedelta(hours=1)).isoformat(), target_id))
            selected = {"competition_result_competition": 0, f"competition_result_list_{cid}": index}
            values = {f"competition_result_home_{target_id}": results[index][0], f"competition_result_away_{target_id}": results[index][1]}
            if index == 2:
                selected[f"result_outcome_{target_id}"] = "1"
            ui = FakeStreamlit(selected=selected, values=values, pressed=f"competition_save_result_{target_id}")
            with patch.dict(sys.modules, {"streamlit": ui}):
                with self.assertRaises(StopRerun):
                    cs.render_admin_competition_results(self.db)

        board = cs.get_competition_standings(self.db, cid)
        self.assertEqual(70, board["standings"][0]["points"])
        self.assertEqual(70, board["list_points"][lists[0]["id"]]["player"] + board["list_points"][lists[1]["id"]]["player"] + board["list_points"][lists[2]["id"]]["player"] + board["list_points"][lists[3]["id"]]["player"] + board["list_points"][lists[4]["id"]]["player"])

        own = render_with(self.db, "player")
        self.assertTrue(any("Pisteet: 24" in item for item in own.output))
        self.assertTrue(any("Pelimerkki: Tuplaus" in item for item in own.output))

        # Correcting a result through Admin updates the shared result columns and ranking immediately.
        target_id = targets[0]
        values = {f"competition_result_home_{target_id}": 3, f"competition_result_away_{target_id}": 2}
        ui = FakeStreamlit(selected={"competition_result_competition": 0, f"competition_result_list_{cid}": 0}, values=values, pressed=f"competition_save_result_{target_id}")
        with patch.dict(sys.modules, {"streamlit": ui}):
            with self.assertRaises(StopRerun):
                cs.render_admin_competition_results(self.db)
        corrected = cs.get_competition_standings(self.db, cid)
        self.assertEqual(62, corrected["standings"][0]["points"])
        self.assertEqual(16, corrected["list_points"][lists[0]["id"]]["player"])

        # Before-start cancellation refunds; after-start cancellation spends.
        early_id = cs._save_target(self.db, None, lists[0]["id"], "A", "B", "", (now + timedelta(days=3)).isoformat(), 10)
        # _save_target creates rows but returns no id, so retrieve the latest target in this list.
        with cs.connect(self.db) as conn:
            early_id = conn.execute("SELECT id FROM competition_targets WHERE list_id=? ORDER BY id DESC LIMIT 1", (lists[0]["id"],)).fetchone()[0]
        cs._assign_token(self.db, "player", early_id, "tuplaus")
        cs._cancel_target(self.db, early_id)
        with cs.connect(self.db) as conn:
            self.assertEqual(2, cs._available_tokens(conn, "player", lists[0])["tuplaus"])
        late_id = cs._save_target(self.db, None, lists[0]["id"], "C", "D", "", (now + timedelta(days=4)).isoformat(), 11)
        with cs.connect(self.db) as conn:
            late_id = conn.execute("SELECT id FROM competition_targets WHERE list_id=? ORDER BY id DESC LIMIT 1", (lists[0]["id"],)).fetchone()[0]
        cs._assign_token(self.db, "player", late_id, "tuplaus")
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competition_targets SET start_iso=? WHERE id=?", ((now - timedelta(hours=1)).isoformat(), late_id))
        cs._cancel_target(self.db, late_id)
        with cs.connect(self.db) as conn:
            self.assertEqual("spent", conn.execute("SELECT status FROM token_assignments WHERE target_id=?", (late_id,)).fetchone()[0])
            self.assertEqual(1, cs._available_tokens(conn, "player", lists[0])["tuplaus"])


if __name__ == "__main__":
    unittest.main()

