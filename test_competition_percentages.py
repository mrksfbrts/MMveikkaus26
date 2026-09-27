import os
import tempfile
import unittest
from datetime import timedelta

import competition_system as cs


class CompetitionPercentageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.temp.name, "percentages.db")
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.execute("INSERT INTO users VALUES('player','x')")

    def tearDown(self):
        self.temp.cleanup()

    def make_target(self, list_id, home, away, prediction, token=None, result=None, cancelled=False, future=False):
        start = cs._now() + timedelta(days=1) if future else cs._now() - timedelta(hours=1)
        with cs.connect(self.db) as conn:
            target_id = conn.execute(
                """INSERT INTO competition_targets(list_id,home,away,start_iso,status,cancelled_before_start,
                   result_home,result_away,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (list_id, "Home", "Away", start.isoformat(), "cancelled" if cancelled else "scheduled",
                 0 if cancelled else None, result[0] if result else None, result[1] if result else None,
                 cs._stamp(), cs._stamp()),
            ).lastrowid
            if prediction is not None:
                import json
                conn.execute(
                    "INSERT INTO user_predictions(username,target_id,prediction_data,created_at,updated_at) VALUES(?,?,?,?,?)",
                    ("player", target_id, json.dumps(prediction), cs._stamp(), cs._stamp()),
                )
            if token:
                conn.execute(
                    """INSERT INTO token_assignments(username,list_id,token_type,token_slot,target_id,status,created_at,updated_at)
                       VALUES('player',?,?,?,?,?,?,?)""",
                    (list_id, token, 0, target_id, "assigned" if future else "spent", cs._stamp(), cs._stamp()),
                )
        return target_id

    def test_resolved_targets_weighted_percentage_ignores_unresolved_cancelled_and_bonus(self):
        cid = cs._create_competition(self.db, "Percentage", "", [{"name": "Kiekko", "prediction_type": "hockey_score"}])
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            list_id = conn.execute("SELECT id FROM competition_lists WHERE competition_id=?", (cid,)).fetchone()[0]
        self.make_target(list_id, 3, 1, {"home_goals": 3, "away_goals": 1}, result=(3, 1))  # 12 / 12
        self.make_target(list_id, 0, 0, {"home_goals": 3, "away_goals": 3}, result=(0, 0))  # 6 / 12
        self.make_target(list_id, None, None, {"home_goals": 4, "away_goals": 2})  # unresolved
        self.make_target(list_id, 3, 1, {"home_goals": 3, "away_goals": 1}, result=(3, 1), cancelled=True)
        with cs.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO competition_bonuses(competition_id,list_id,username,points,reason,created_at,created_by) VALUES(?,?,?,?,?,?,?)",
                (cid, list_id, "player", 5, "Bonus", cs._stamp(), "admin"),
            )
        stats = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual({"points": 18, "max_points": 24}, stats)
        self.assertEqual(75.0, 100 * stats["points"] / stats["max_points"])
        scoreboard = cs.get_competition_standings(self.db, cid)
        self.assertEqual(23, scoreboard["standings"][0]["points"])  # includes bonus; percent does not

    def test_one_resolved_half_score_is_fifty_percent(self):
        cid = cs._create_competition(self.db, "Half", "", [{"name": "Kiekko", "prediction_type": "hockey_score"}])
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            list_id = conn.execute("SELECT id FROM competition_lists WHERE competition_id=?", (cid,)).fetchone()[0]
        self.make_target(list_id, 0, 0, {"home_goals": 3, "away_goals": 3}, result=(0, 0))
        stats = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual({"points": 6, "max_points": 12}, stats)
        self.assertEqual(50.0, 100 * stats["points"] / stats["max_points"])

    def test_token_maxima_and_percentage_refresh_when_result_is_saved(self):
        specs = [
            {"name": "Tuplaus", "prediction_type": "hockey_score", "tuplaus": 1},
            {"name": "Harava", "prediction_type": "result_1x2", "harava": 1},
            {"name": "Jokeri", "prediction_type": "hockey_multi", "jokeri": 1},
        ]
        cid = cs._create_competition(self.db, "Tokens", "", specs)
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            lists = conn.execute("SELECT * FROM competition_lists WHERE competition_id=? ORDER BY sort_order", (cid,)).fetchall()
        tuplaus_id = self.make_target(lists[0]["id"], 3, 1, {"home_goals": 3, "away_goals": 1}, "tuplaus", (3, 1))
        harava_id = self.make_target(lists[1]["id"], 2, 1, {"marks": ["1", "X"]}, "harava", (2, 1))
        joker_id = self.make_target(
            lists[2]["id"], 5, 0,
            {"scores": [{"home_goals": 0, "away_goals": 0}] * 4, "mark": "1", "joker_score": {"home_goals": 5, "away_goals": 0}},
            "jokeri", (5, 0),
        )
        board = cs.get_competition_standings(self.db, cid)
        self.assertEqual(27, board["performance"]["overall"]["player"]["points"])
        self.assertEqual(28, board["performance"]["overall"]["player"]["max_points"])
        self.assertEqual(12, board["performance"]["lists"][lists[0]["id"]]["player"]["max_points"])
        self.assertEqual(5, board["performance"]["lists"][lists[1]["id"]]["player"]["max_points"])
        self.assertEqual(11, board["performance"]["lists"][lists[2]["id"]]["player"]["max_points"])
        self.assertEqual(12, board["performance"]["lists"][lists[0]["id"]]["player"]["points"])
        self.assertEqual(24, board["list_points"][lists[0]["id"]]["player"])
        self.assertEqual(100.0, 100 * board["performance"]["lists"][lists[0]["id"]]["player"]["points"] / 12)
        self.assertEqual(80.0, 100 * board["performance"]["lists"][lists[1]["id"]]["player"]["points"] / 5)

        # A scheduled target without a result contributes nothing; saving the result changes the ratio immediately.
        pending_id = self.make_target(lists[0]["id"], None, None, {"home_goals": 2, "away_goals": 1}, future=True)
        before = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual((27, 28), (before["points"], before["max_points"]))
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competition_targets SET start_iso=? WHERE id=?", ((cs._now() - timedelta(minutes=1)).isoformat(), pending_id))
        cs._save_result(self.db, pending_id, 2, 1)
        after = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual((39, 40), (after["points"], after["max_points"]))

    def test_tuplaus_does_not_double_percentage_points_on_partial_hit(self):
        cid = cs._create_competition(
            self.db, "Doubled partial", "",
            [{"name": "Kiekko", "prediction_type": "hockey_score", "tuplaus": 1}],
        )
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            list_id = conn.execute("SELECT id FROM competition_lists WHERE competition_id=?", (cid,)).fetchone()[0]
        self.make_target(list_id, 3, 1, {"home_goals": 3, "away_goals": 1}, "tuplaus", (3, 2))
        board = cs.get_competition_standings(self.db, cid)
        stats = board["performance"]["overall"]["player"]
        self.assertEqual({"points": 8, "max_points": 12}, stats)
        self.assertEqual(16, board["standings"][0]["points"])
        self.assertAlmostEqual(66.67, 100 * stats["points"] / stats["max_points"], places=2)

    def test_harava_and_result_veto_weight_to_fourteen_of_fifteen(self):
        cid = cs._create_competition(
            self.db, "Weighted", "",
            [
                {"name": "1X2", "prediction_type": "result_1x2", "harava": 1},
                {"name": "Jalkapallo", "prediction_type": "football_score"},
            ],
        )
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
            lists = conn.execute("SELECT * FROM competition_lists WHERE competition_id=? ORDER BY sort_order", (cid,)).fetchall()
        self.make_target(lists[0]["id"], 2, 1, {"marks": ["1", "X"]}, "harava", (2, 1))
        self.make_target(lists[1]["id"], 3, 1, {"home_goals": 3, "away_goals": 1}, result=(3, 1))
        stats = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual({"points": 14, "max_points": 15}, stats)
        self.assertAlmostEqual(93.33, 100 * stats["points"] / stats["max_points"], places=2)

    def test_no_resolved_targets_has_no_percentage_denominator(self):
        cid = cs._create_competition(self.db, "Waiting", "", [{"name": "Futis", "prediction_type": "football_score"}])
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competitions SET status='published' WHERE id=?", (cid,))
        stats = cs.get_competition_standings(self.db, cid)["performance"]["overall"]["player"]
        self.assertEqual({"points": 0, "max_points": 0}, stats)
        self.assertIsNone(100 * stats["points"] / stats["max_points"] if stats["max_points"] else None)


if __name__ == "__main__":
    unittest.main()
