"""Regression tests for additive repairs of incomplete legacy SQLite schemas."""
import os
import sqlite3
import tempfile
import unittest
import warnings
import zipfile
from contextlib import contextmanager

from competition_system import init_competition_db
from legacy_database import LEGACY_COLUMNS, init_legacy_db


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "legacy.db")

    def tearDown(self):
        self.tmp.cleanup()

    def columns(self, conn, table):
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    @contextmanager
    def connection(self, db_path=None):
        conn = sqlite3.connect(db_path or self.db)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def assert_full_legacy_schema(self, conn):
        for table, specs in LEGACY_COLUMNS.items():
            self.assertTrue(set(specs).issubset(self.columns(conn, table)), table)

    def test_empty_database_creates_full_legacy_schema_and_queries_work(self):
        init_legacy_db(self.db)
        with self.connection() as conn:
            self.assert_full_legacy_schema(conn)
            conn.execute("SELECT username, match_id, prediction FROM predictions WHERE is_special='0'").fetchall()
            conn.execute("SELECT id, result FROM real_results WHERE result_type='match'").fetchall()
            self.assertEqual(("username",), self.primary_key(conn, "users"))
            self.assertEqual(("username", "match_id", "is_special"), self.primary_key(conn, "predictions"))
            self.assertEqual(("result_type", "id"), self.primary_key(conn, "real_results"))

    @staticmethod
    def primary_key(conn, table):
        return tuple(row[1] for row in sorted(
            (row for row in conn.execute(f"PRAGMA table_info({table})") if row[5]),
            key=lambda row: row[5],
        ))

    def test_partial_tables_are_repaired_idempotently_without_losing_rows(self):
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL);
                INSERT INTO users VALUES ('alice', 'hash-a');
                CREATE TABLE predictions (username TEXT, match_id TEXT, is_special INTEGER, created_at TEXT);
                INSERT INTO predictions VALUES ('alice', 'match-1', 0, '2001-02-03T04:05:06');
                CREATE TABLE point_adjustments (username TEXT, points INTEGER);
                INSERT INTO point_adjustments VALUES ('alice', 3);
                CREATE TABLE real_results (id TEXT, result TEXT);
                INSERT INTO real_results VALUES ('match-1', '{"home_goals":1,"away_goals":0}');
                CREATE TABLE comments (id INTEGER PRIMARY KEY, username TEXT, text TEXT);
                INSERT INTO comments VALUES (9, 'alice', 'keep comment');
                CREATE TABLE comment_reactions (comment_id INTEGER, username TEXT, reaction TEXT);
                INSERT INTO comment_reactions VALUES (9, 'alice', 'heart');
                CREATE TABLE matches (id TEXT PRIMARY KEY, list_key TEXT, home TEXT, away TEXT);
                INSERT INTO matches VALUES ('match-1', 'list-a', 'Home', 'Away');
            """)

        init_legacy_db(self.db)
        init_legacy_db(self.db)
        with self.connection() as conn:
            self.assert_full_legacy_schema(conn)
            self.assertEqual(('hash-a',), conn.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone())
            self.assertEqual(('2001-02-03T04:05:06',), conn.execute("SELECT created_at FROM predictions WHERE match_id='match-1'").fetchone())
            self.assertEqual((None,), conn.execute("SELECT prediction FROM predictions WHERE match_id='match-1'").fetchone())
            self.assertEqual((0,), conn.execute("SELECT is_special FROM predictions WHERE match_id='match-1'").fetchone())
            self.assertEqual((3,), conn.execute("SELECT points FROM point_adjustments WHERE username='alice'").fetchone())
            self.assertEqual(('match', '{"home_goals":1,"away_goals":0}'), conn.execute("SELECT result_type,result FROM real_results WHERE id='match-1'").fetchone())
            self.assertEqual(('keep comment',), conn.execute("SELECT text FROM comments WHERE id=9").fetchone())
            self.assertEqual((None,), conn.execute("SELECT parent_id FROM comments WHERE id=9").fetchone())
            self.assertEqual((1,), (conn.execute("SELECT COUNT(*) FROM comment_reactions").fetchone()[0],))
            self.assertEqual(('Home', 'Away', 0, 0, 'normal'), conn.execute("SELECT home,away,is_double,sort_order,pred_type FROM matches WHERE id='match-1'").fetchone())
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def test_backup_restore_round_trip_keeps_legacy_and_competition_schemas(self):
        init_legacy_db(self.db)
        init_competition_db(self.db)
        restored = os.path.join(self.tmp.name, "restored.db")
        backup = os.path.join(self.tmp.name, "backup.zip")
        with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(self.db, arcname="veikkaus.db")
        with zipfile.ZipFile(backup) as archive, open(restored, "wb") as output:
            output.write(archive.read("veikkaus.db"))
        with self.connection(restored) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue(set(LEGACY_COLUMNS).issubset(tables))
            self.assertTrue({"competitions", "competition_lists", "competition_targets", "user_predictions", "token_assignments", "competition_bonuses"}.issubset(tables))
            self.assert_full_legacy_schema(conn)

    def test_duplicate_keys_preserve_rows_and_do_not_abort_migration(self):
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE users (username TEXT, password_hash TEXT);
                INSERT INTO users VALUES ('dup-user', 'hash-1'), ('dup-user', 'hash-2');
                CREATE TABLE predictions (username TEXT, match_id TEXT, is_special INTEGER);
                INSERT INTO predictions VALUES ('dup-user', 'm1', 0), ('dup-user', 'm1', 0);
                CREATE TABLE point_adjustments (id INTEGER, username TEXT, points INTEGER);
                INSERT INTO point_adjustments VALUES (7, 'dup-user', 2), (7, 'dup-user', 3);
                CREATE TABLE real_results (id TEXT, result TEXT);
                INSERT INTO real_results VALUES ('m1', '1-0'), ('m1', '2-0');
                CREATE TABLE comments (id INTEGER, username TEXT, text TEXT);
                INSERT INTO comments VALUES (8, 'dup-user', 'first'), (8, 'dup-user', 'second');
                CREATE TABLE comment_reactions (comment_id INTEGER, username TEXT, reaction TEXT);
                INSERT INTO comment_reactions VALUES (8, 'dup-user', 'heart'), (8, 'dup-user', 'heart');
                CREATE TABLE matches (id TEXT, list_key TEXT, home TEXT, away TEXT);
                INSERT INTO matches VALUES ('m1', 'list', 'A', 'B'), ('m1', 'list', 'C', 'D');
            """)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            init_legacy_db(self.db)
            init_legacy_db(self.db)
        self.assertTrue(caught)
        with self.connection() as conn:
            self.assert_full_legacy_schema(conn)
            expected_counts = {
                "users": 2, "predictions": 2, "point_adjustments": 2,
                "real_results": 2, "comments": 2,
                "comment_reactions": 2, "matches": 2,
            }
            for table, count in expected_counts.items():
                self.assertEqual(count, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], table)
            for table in ("users", "predictions", "point_adjustments", "real_results", "comments", "comment_reactions", "matches"):
                indexes = list(conn.execute(f"PRAGMA index_list({table})"))
                unique_indexes = [row[1] for row in indexes if row[2]]
                self.assertFalse(any(name.startswith("idx_legacy_key_") for name in unique_indexes), table)
                self.assertTrue(any(row[1].startswith("idx_legacy_lookup_") and not row[2] for row in indexes), table)


if __name__ == "__main__":
    unittest.main()
