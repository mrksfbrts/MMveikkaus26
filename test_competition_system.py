import os
import sqlite3
import tempfile
import unittest
from datetime import timedelta

import competition_system as cs


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.result = {"home_goals": 3, "away_goals": 1}

    def test_hockey_result_veto_exact_spec_cases(self):
        expected = {(3, 1): 12, (3, 2): 8, (2, 1): 8, (5, 1): 7, (3, 3): 0, (3, 4): 0}
        for score, points in expected.items():
            with self.subTest(score=score):
                self.assertEqual(points, cs.score_prediction("hockey_score", {"home_goals": score[0], "away_goals": score[1]}, self.result))

    def test_football_result_veto_and_doubling(self):
        expected = {(3, 1): 10, (3, 2): 7, (2, 1): 7, (5, 1): 6, (3, 3): 0, (3, 4): 0}
        for score, points in expected.items():
            prediction = {"home_goals": score[0], "away_goals": score[1]}
            with self.subTest(score=score):
                self.assertEqual(points, cs.score_prediction("football_score", prediction, self.result))
                self.assertEqual(points * 2, cs.score_prediction("football_score", prediction, self.result, "tuplaus"))

    def test_1x2_harava(self):
        result = {"home_goals": 2, "away_goals": 1}
        self.assertEqual(5, cs.score_prediction("result_1x2", {"mark": "1"}, result))
        self.assertEqual(0, cs.score_prediction("result_1x2", {"mark": "X"}, result))
        self.assertEqual(4, cs.score_prediction("result_1x2", {"marks": ["1", "X"]}, result, "harava"))
        self.assertEqual(0, cs.score_prediction("result_1x2", {"marks": ["X", "2"]}, result, "harava"))

    def test_multi_and_joker(self):
        result = {"home_goals": 5, "away_goals": 0}
        hockey = {"scores": [{"home_goals": i, "away_goals": i} for i in range(4)], "mark": "1"}
        football = {"scores": [{"home_goals": 2, "away_goals": 2}, {"home_goals": 3, "away_goals": 1}], "mark": "1"}
        self.assertEqual(1, cs.score_prediction("hockey_multi", hockey, result))
        hockey["joker_score"] = {"home_goals": 5, "away_goals": 0}
        self.assertEqual(11, cs.score_prediction("hockey_multi", hockey, result, "jokeri"))
        self.assertEqual(1, cs.score_prediction("football_multi", football, result))
        football["joker_score"] = {"home_goals": 5, "away_goals": 0}
        self.assertEqual(11, cs.score_prediction("football_multi", football, result, "jokeri"))
        hockey["scores"][0] = {"home_goals": 5, "away_goals": 0}
        hockey["mark"] = "X"
        self.assertEqual(10, cs.score_prediction("hockey_multi", hockey, result))
        football["scores"][1] = {"home_goals": 5, "away_goals": 0}
        self.assertEqual(11, cs.score_prediction("football_multi", football, result))


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "test.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_migration_is_idempotent_and_preserves_legacy_data(self):
        conn = sqlite3.connect(self.db)
        conn.executescript("""
          CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL);
          CREATE TABLE comments(id INTEGER PRIMARY KEY,username TEXT,text TEXT);
          CREATE TABLE comment_reactions(comment_id INTEGER,username TEXT,reaction TEXT);
          INSERT INTO users VALUES('old-user','hash');
          INSERT INTO comments VALUES(7,'old-user','keep this');
          INSERT INTO comment_reactions VALUES(7,'old-user','heart');
        """)
        conn.commit()
        conn.close()
        cs.init_competition_db(self.db)
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            self.assertEqual("hash", conn.execute("SELECT password_hash FROM users WHERE username='old-user'").fetchone()[0])
            self.assertEqual("keep this", conn.execute("SELECT text FROM comments WHERE id=7").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM comment_reactions").fetchone()[0])
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"competitions", "competition_lists", "competition_targets", "user_predictions", "token_assignments", "competition_bonuses"}.issubset(tables))

    def test_multiple_tokens_are_individually_allocated_and_refund_on_early_cancel(self):
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.execute("INSERT INTO users VALUES('player','x')")
        future = (cs._now() + timedelta(days=1)).replace(microsecond=0)
        cid = cs._create_competition(self.db,"Cup","",[{"name":"Harava","prediction_type":"result_1x2","harava":2}])
        with cs.connect(self.db) as conn:
            lid = conn.execute("SELECT id FROM competition_lists WHERE competition_id=?",(cid,)).fetchone()[0]
            for i in range(3):
                conn.execute("INSERT INTO competition_targets(list_id,home,away,start_iso,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                             (lid,"Home","Away",(future+timedelta(hours=i)).isoformat(),i,cs._stamp(),cs._stamp()))
            tids = [r[0] for r in conn.execute("SELECT id FROM competition_targets ORDER BY id").fetchall()]
            conn.execute("UPDATE competitions SET status='published' WHERE id=?",(cid,))
        cs._assign_token(self.db,"player",tids[0],"harava")
        cs._assign_token(self.db,"player",tids[1],"harava")
        with cs.connect(self.db) as conn:
            list_row=conn.execute("SELECT * FROM competition_lists WHERE id=?",(lid,)).fetchone()
            self.assertEqual(0,cs._available_tokens(conn,"player",list_row)["harava"])
        with self.assertRaises(ValueError):
            cs._assign_token(self.db,"player",tids[2],"harava")
        cs._cancel_target(self.db,tids[0])
        with cs.connect(self.db) as conn:
            list_row=conn.execute("SELECT * FROM competition_lists WHERE id=?",(lid,)).fetchone()
            self.assertEqual(1,cs._available_tokens(conn,"player",list_row)["harava"])
        cs._assign_token(self.db,"player",tids[2],"harava")

    def test_late_cancellation_spends_token_and_tbd_target_is_updated_in_place(self):
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.execute("INSERT INTO users VALUES('player','x')")
        future=(cs._now()+timedelta(days=1)).replace(microsecond=0)
        cid=cs._create_competition(self.db,"Tournament","",[{"name":"Bracket","prediction_type":"football_multi","jokeri":1}])
        with cs.connect(self.db) as conn:
            lid=conn.execute("SELECT id FROM competition_lists WHERE competition_id=?",(cid,)).fetchone()[0]
            conn.execute("INSERT INTO competition_targets(list_id,home,away,display_name,start_iso,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                         (lid,"TBD","TBD","Semifinaali",future.isoformat(),cs._stamp(),cs._stamp()))
            tid=conn.execute("SELECT id FROM competition_targets WHERE list_id=?",(lid,)).fetchone()[0]
        cs._publish(self.db,cid)
        with self.assertRaises(ValueError):
            cs._save_prediction(self.db,"player",tid,{"scores":[{"home_goals":1,"away_goals":0},{"home_goals":2,"away_goals":0}],"mark":"1"})
        cs._save_target(self.db,tid,lid,"Team A","Team B","Semifinaali",future.isoformat(),0)
        with cs.connect(self.db) as conn:
            self.assertEqual(tid,conn.execute("SELECT id FROM competition_targets WHERE list_id=?",(lid,)).fetchone()[0])
        cs._assign_token(self.db,"player",tid,"jokeri")
        with cs.connect(self.db) as conn:
            conn.execute("UPDATE competition_targets SET start_iso=? WHERE id=?",((cs._now()-timedelta(minutes=1)).isoformat(),tid))
        cs._cancel_target(self.db,tid)
        with cs.connect(self.db) as conn:
            list_row=conn.execute("SELECT * FROM competition_lists WHERE id=?",(lid,)).fetchone()
            self.assertEqual(0,cs._available_tokens(conn,"player",list_row)["jokeri"])
            self.assertEqual("spent",conn.execute("SELECT status FROM token_assignments WHERE target_id=?",(tid,)).fetchone()[0])

    def test_competition_bonus_changes_total_and_equal_scores_share_rank(self):
        cs.init_competition_db(self.db)
        with cs.connect(self.db) as conn:
            conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
            conn.executemany("INSERT INTO users VALUES(?, 'x')",[("Aino",),("Bertta",)])
        cid=cs._create_competition(self.db,"Finale","",[{"name":"Finalit","prediction_type":"football_score"}])
        past=(cs._now()-timedelta(hours=2)).replace(microsecond=0)
        with cs.connect(self.db) as conn:
            lid=conn.execute("SELECT id FROM competition_lists WHERE competition_id=?",(cid,)).fetchone()[0]
            conn.execute("INSERT INTO competition_targets(list_id,home,away,start_iso,result_home,result_away,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                         (lid,"Home","Away",past.isoformat(),2,1,cs._stamp(),cs._stamp()))
            tid=conn.execute("SELECT id FROM competition_targets WHERE list_id=?",(lid,)).fetchone()[0]
            for user in ("Aino","Bertta"):
                conn.execute("INSERT INTO user_predictions(username,target_id,prediction_data,created_at,updated_at) VALUES(?,?,?,?,?)",
                             (user,tid,'{"home_goals":2,"away_goals":1}',cs._stamp(),cs._stamp()))
            conn.execute("UPDATE competitions SET status='published' WHERE id=?",(cid,))
            _,_,rows=cs._competition_standings(conn,cid)
            self.assertEqual([1,1],[row["rank"] for row in rows])
            conn.execute("INSERT INTO competition_bonuses(competition_id,list_id,username,points,reason,created_at,created_by) VALUES(?,?,?,?,?,?,?)",
                         (cid,lid,"Bertta",5,"First",cs._stamp(),"admin"))
            _,_,rows=cs._competition_standings(conn,cid)
            ranking={row["username"]:row for row in rows}
            self.assertEqual(15,ranking["Bertta"]["points"])
            self.assertEqual(5,ranking["Bertta"]["bonus_points"])
            self.assertEqual(1,ranking["Bertta"]["rank"])
            self.assertEqual(2,ranking["Aino"]["rank"])


if __name__ == "__main__":
    unittest.main()
