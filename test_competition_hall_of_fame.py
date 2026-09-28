import json
import os
import tempfile
import unittest
from datetime import timedelta

import competition_system as cs


class HallOfFameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.temp.name, "hall-of-fame.db")
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.executemany(
                "INSERT INTO users(username,password_hash) VALUES(?, 'x')",
                [(name,) for name in ("Markus", "Tommi", "Tekoäly", "Neljäs", "Viides")],
            )
        self.competition_id, self.list_id, self.target_id = self.make_competition()

    def tearDown(self):
        self.temp.cleanup()

    def make_competition(self):
        cid = cs._create_competition(
            self.db, "Hall of Fame Cup", "",
            [{"name": "Tulosveto", "prediction_type": "hockey_score", "tuplaus": 1}],
        )
        with cs.connect(self.db) as conn:
            list_id = conn.execute(
                "SELECT id FROM competition_lists WHERE competition_id=?", (cid,)
            ).fetchone()[0]
            target_id = conn.execute(
                """INSERT INTO competition_targets
                   (list_id,home,away,start_iso,result_home,result_away,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (list_id, "Home", "Away", (cs._now() - timedelta(hours=1)).isoformat(),
                 3, 1, cs._stamp(), cs._stamp()),
            ).lastrowid
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            predictions = {
                "Markus": {"home_goals": 3, "away_goals": 1},
                "Tommi": {"home_goals": 3, "away_goals": 1},
                "Tekoäly": {"home_goals": 3, "away_goals": 2},
                "Neljäs": {"home_goals": 2, "away_goals": 1},
                "Viides": {"home_goals": 3, "away_goals": 4},
            }
            for username, prediction in predictions.items():
                conn.execute(
                    """INSERT INTO user_predictions
                       (username,target_id,prediction_data,created_at,updated_at)
                       VALUES(?,?,?,?,?)""",
                    (username, target_id, json.dumps(prediction), cs._stamp(), cs._stamp()),
                )
            conn.execute(
                """INSERT INTO token_assignments
                   (username,list_id,token_type,token_slot,target_id,status,created_at,updated_at)
                   VALUES('Markus',?,'tuplaus',0,?,'spent',?,?)""",
                (list_id, target_id, cs._stamp(), cs._stamp()),
            )
        return cid, list_id, target_id

    def test_live_top_three_updates_and_keeps_ties(self):
        live = cs.get_competition_hall_of_fame(self.db)["live"][0]
        initial = {row["username"]: row for row in live["players"]}
        self.assertEqual((1, 24), (initial["Markus"]["rank"], initial["Markus"]["points"]))
        self.assertEqual(100.0, initial["Markus"]["percentage"])
        self.assertEqual((3, 8), (initial["Tekoäly"]["rank"], initial["Tekoäly"]["points"]))
        self.assertEqual(3, initial["Neljäs"]["rank"])

        with cs.connect(self.db) as conn:
            conn.execute(
                "UPDATE user_predictions SET prediction_data=? WHERE username='Tommi' AND target_id=?",
                ('{"home_goals":3,"away_goals":4}', self.target_id),
            )
        updated = cs.get_competition_hall_of_fame(self.db)["live"][0]
        updated_rows = {row["username"]: row for row in updated["players"]}
        self.assertNotIn("Tommi", updated_rows)
        self.assertEqual({"Markus", "Tekoäly", "Neljäs"}, set(updated_rows))

    def test_final_snapshot_includes_bonus_and_tuplaus_but_percent_excludes_them(self):
        with cs.connect(self.db) as conn:
            conn.execute(
                """INSERT INTO competition_bonuses
                   (competition_id,list_id,username,points,reason,created_at,created_by)
                   VALUES(?,?,?,?,?,?,?)""",
                (self.competition_id, self.list_id, "Markus", 5, "Bonus", cs._stamp(), "admin"),
            )
        board = cs.get_competition_standings(self.db, self.competition_id)
        perf = board["performance"]["overall"]["Markus"]
        self.assertEqual(12, perf["points"])  # base points; Tuplaus and bonus excluded
        self.assertEqual(29, board["standings"][0]["points"])  # Tuplaus + bonus
        self.assertEqual(100.0, 100 * perf["points"] / perf["max_points"])

        cs.finish_competition(self.db, self.competition_id)
        history = cs.get_competition_hall_of_fame(self.db)["history"]
        archived = next(item for item in history if item["competition_id"] == self.competition_id)
        rows = {row["username"]: row for row in archived["players"]}
        self.assertEqual("Hall of Fame Cup", rows["Markus"]["competition_name"])
        self.assertEqual(29, rows["Markus"]["points"])
        self.assertEqual(100.0, rows["Markus"]["percentage"])
        self.assertEqual(3, rows["Tekoäly"]["rank"])
        self.assertEqual(3, rows["Neljäs"]["rank"])
        self.assertTrue(rows["Markus"]["ended_at"])

    def test_archiving_and_removing_competition_keeps_history_and_new_cup_is_separate(self):
        cs.finish_competition(self.db, self.competition_id)
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET name='Changed name' WHERE id=?", (self.competition_id,))
        cs.archive_competition(self.db, self.competition_id)
        with cs.connect(self.db) as conn:
            conn.execute("DELETE FROM competition_bonuses WHERE competition_id=?", (self.competition_id,))
            conn.execute("DELETE FROM user_predictions WHERE target_id=?", (self.target_id,))
            conn.execute("DELETE FROM token_assignments WHERE target_id=?", (self.target_id,))
            conn.execute("DELETE FROM competition_targets WHERE id=?", (self.target_id,))
            conn.execute("DELETE FROM competition_lists WHERE competition_id=?", (self.competition_id,))
            conn.execute("DELETE FROM competitions WHERE id=?", (self.competition_id,))

        second_id = cs._create_competition(
            self.db, "Second Cup", "", [{"name": "Lista", "prediction_type": "hockey_score"}]
        )
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (second_id,))
        cs.finish_competition(self.db, second_id)
        history = cs.get_competition_hall_of_fame(self.db)["history"]
        original = next(item for item in history if item["competition_id"] == self.competition_id)
        second = next(item for item in history if item["competition_id"] == second_id)
        self.assertEqual("Hall of Fame Cup", original["competition_name"])
        self.assertEqual(24, next(row["points"] for row in original["players"] if row["username"] == "Markus"))
        self.assertEqual({self.competition_id, second_id}, {item["competition_id"] for item in history})

    def test_existing_legacy_hall_of_fame_top_three_is_preserved(self):
        self.assertEqual(
            [("Markus", 386), ("Tommi", 354), ("Tekoäly", 346)],
            [(row["username"], row["points"]) for row in cs.LEGACY_HALL_OF_FAME],
        )


if __name__ == "__main__":
    unittest.main()
