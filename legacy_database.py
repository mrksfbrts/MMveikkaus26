"""Initialization and additive migrations for the legacy application tables."""
import sqlite3
import warnings


LEGACY_COLUMNS = {
    "users": {
        "username": ("TEXT", True, None),
        "password_hash": ("TEXT", True, None),
        "created_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
    },
    "predictions": {
        "username": ("TEXT", False, None),
        "match_id": ("TEXT", False, None),
        "prediction": ("TEXT", False, None),
        "is_special": ("INTEGER", False, "0"),
        "created_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
    },
    "point_adjustments": {
        "id": ("INTEGER", False, None),
        "username": ("TEXT", True, None),
        "points": ("INTEGER", True, None),
        "reason": ("TEXT", False, None),
        "created_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
        "created_by": ("TEXT", False, None),
    },
    "real_results": {
        "result_type": ("TEXT", False, None),
        "id": ("TEXT", False, None),
        "result": ("TEXT", False, None),
        "updated_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
    },
    "comments": {
        "id": ("INTEGER", False, None),
        "username": ("TEXT", True, None),
        "text": ("TEXT", True, None),
        "created_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
        "edited_at": ("TEXT", False, None),
        "parent_id": ("INTEGER", False, "NULL"),
    },
    "comment_reactions": {
        "comment_id": ("INTEGER", True, None),
        "username": ("TEXT", True, None),
        "reaction": ("TEXT", True, None),
        "created_at": ("TEXT", False, "CURRENT_TIMESTAMP"),
    },
    "matches": {
        "id": ("TEXT", False, None),
        "list_key": ("TEXT", True, None),
        "list_name": ("TEXT", True, None),
        "home": ("TEXT", True, None),
        "away": ("TEXT", True, None),
        "aika": ("TEXT", True, None),
        "start_iso": ("TEXT", True, None),
        "is_double": ("INTEGER", False, "0"),
        "sort_order": ("INTEGER", False, "0"),
        "pred_type": ("TEXT", False, "'normal'"),
    },
}

LEGACY_KEYS = {
    "users": ("username",),
    "predictions": ("username", "match_id", "is_special"),
    "point_adjustments": ("id",),
    "real_results": ("result_type", "id"),
    "comments": ("id",),
    "comment_reactions": ("comment_id", "username", "reaction"),
    "matches": ("id",),
}


def init_legacy_db(db_path):
    """Create the legacy schema and add missing columns without dropping data."""
    conn = sqlite3.connect(db_path, timeout=20)
    try:
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
            username TEXT,
            match_id TEXT,
            prediction TEXT,
            is_special INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (username, match_id, is_special)
        );
        CREATE TABLE IF NOT EXISTS point_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            points INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT
        );
        CREATE TABLE IF NOT EXISTS real_results (
            result_type TEXT,
            id TEXT,
            result TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (result_type, id)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edited_at TEXT,
            parent_id INTEGER DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS comment_reactions (
            comment_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            reaction TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (comment_id, username, reaction)
        );
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            list_key TEXT NOT NULL,
            list_name TEXT NOT NULL,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            aika TEXT NOT NULL,
            start_iso TEXT NOT NULL,
            is_double INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            pred_type TEXT DEFAULT 'normal'
        );
        """)

        missing_columns = {}
        for table, column_specs in LEGACY_COLUMNS.items():
            existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
            missing_columns[table] = existing
            row_count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for column, (column_type, not_null, default) in column_specs.items():
                if column in existing:
                    continue
                definition = column_type
                # SQLite cannot add a non-constant default such as CURRENT_TIMESTAMP.
                if default and default != "CURRENT_TIMESTAMP":
                    definition += f" DEFAULT {default}"
                if not_null and row_count == 0:
                    definition += " NOT NULL"
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

        # If the discriminator itself was absent, legacy result rows can safely
        # be classified as matches: all legacy writes use result_type='match'.
        # Do not rewrite values in any pre-existing column or invent historical
        # timestamps/prediction/result payloads.
        if "result_type" not in missing_columns["real_results"]:
            c.execute("UPDATE real_results SET result_type='match' WHERE result_type IS NULL")

        # Restore auto-generated IDs when an older partial table had no id column.
        for table in ("point_adjustments", "comments"):
            if "id" in missing_columns[table]:
                c.execute(f"UPDATE {table} SET id=rowid WHERE id IS NULL")
                trigger = f"trg_legacy_{table}_fill_id"
                c.execute(f"""CREATE TRIGGER IF NOT EXISTS {trigger}
                    AFTER INSERT ON {table} WHEN NEW.id IS NULL
                    BEGIN UPDATE {table} SET id=NEW.rowid WHERE rowid=NEW.rowid; END""")

        # Preserve original keys. If legacy duplicates exist, do not block app
        # startup or remove data: keep a lookup index and report that uniqueness
        # could not safely be restored without an explicit data repair.
        for table, key_columns in LEGACY_KEYS.items():
            primary_key = tuple(row[1] for row in sorted(
                (r for r in c.execute(f"PRAGMA table_info({table})") if r[5]), key=lambda r: r[5]
            ))
            if primary_key != key_columns:
                columns = ",".join(key_columns)
                duplicate = c.execute(
                    f"SELECT 1 FROM {table} GROUP BY {columns} HAVING COUNT(*) > 1 LIMIT 1"
                ).fetchone()
                if duplicate:
                    index = "idx_legacy_lookup_" + table
                    c.execute(f"CREATE INDEX IF NOT EXISTS {index} ON {table} ({columns})")
                    warnings.warn(
                        f"Legacy table {table} has duplicate key values for ({columns}); "
                        "preserving all rows and skipping its UNIQUE index.",
                        RuntimeWarning,
                    )
                else:
                    index = "idx_legacy_key_" + table
                    c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {index} ON {table} ({columns})")

        # Preserve created_at/updated_at defaults for inserts into old tables
        # where ALTER TABLE had to add the column without CURRENT_TIMESTAMP.
        for table, timestamp_column in (
            ("users", "created_at"), ("predictions", "created_at"),
            ("point_adjustments", "created_at"), ("real_results", "updated_at"),
            ("comments", "created_at"), ("comment_reactions", "created_at"),
        ):
            if timestamp_column not in missing_columns[table]:
                continue
            trigger = f"trg_legacy_{table}_{timestamp_column}_default"
            c.execute(f"""CREATE TRIGGER IF NOT EXISTS {trigger}
                AFTER INSERT ON {table}
                WHEN NEW.{timestamp_column} IS NULL OR NEW.{timestamp_column}=''
                BEGIN UPDATE {table} SET {timestamp_column}=CURRENT_TIMESTAMP
                      WHERE rowid=NEW.rowid; END""")

        c.executescript("""
        CREATE INDEX IF NOT EXISTS idx_pred_user_match ON predictions(username, match_id);
        CREATE INDEX IF NOT EXISTS idx_pred_match ON predictions(match_id);
        CREATE INDEX IF NOT EXISTS idx_results_id ON real_results(id);
        CREATE INDEX IF NOT EXISTS idx_adj_user ON point_adjustments(username);
        CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_id);
        CREATE INDEX IF NOT EXISTS idx_comments_created ON comments(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_matches_list ON matches(list_key, sort_order);
        """)
        conn.commit()
    finally:
        conn.close()
