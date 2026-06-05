import sqlite3
import threading
import os
from datetime import datetime
from parser.msg_parser import parse_msg_info


_db_lock = threading.Lock()
_ready_flags: dict[str, bool] = {}


def get_db_path(account_dir: str) -> str:
    return os.path.join(account_dir, 'date_index.db')


def _init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS date_index (
            contact_qq TEXT NOT NULL,
            date        TEXT NOT NULL,
            msg_count   INTEGER NOT NULL DEFAULT 0,
            first_msg_index INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (contact_qq, date)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS index_meta (
            contact_qq TEXT PRIMARY KEY,
            msg_info_mtime REAL NOT NULL
        )
    ''')
    conn.commit()
    return conn


def index_account_async(account_dir: str) -> threading.Thread:
    _ready_flags[account_dir] = False

    def _worker():
        db_path = get_db_path(account_dir)
        with _db_lock:
            conn = _init_db(db_path)

        try:
            for entry in os.listdir(account_dir):
                contact_dir = os.path.join(account_dir, entry)
                if not os.path.isdir(contact_dir):
                    continue
                msg_file = os.path.join(contact_dir, 'msg.info')
                if not os.path.isfile(msg_file):
                    continue

                try:
                    current_mtime = os.path.getmtime(msg_file)
                except OSError:
                    continue

                with _db_lock:
                    row = conn.execute(
                        'SELECT msg_info_mtime FROM index_meta WHERE contact_qq = ?',
                        (entry,)
                    ).fetchone()

                if row and abs(row[0] - current_mtime) < 1.0:
                    continue

                messages = parse_msg_info(msg_file)

                date_groups: dict[str, list[int]] = {}
                for i, msg in enumerate(messages):
                    try:
                        dt = datetime.fromtimestamp(msg.timestamp)
                    except (OSError, ValueError, OverflowError):
                        continue
                    date_str = dt.strftime('%Y-%m-%d')
                    if date_str not in date_groups:
                        date_groups[date_str] = []
                    date_groups[date_str].append(i)

                with _db_lock:
                    conn.execute(
                        'DELETE FROM date_index WHERE contact_qq = ?',
                        (entry,)
                    )
                    for date_str, indices in date_groups.items():
                        conn.execute(
                            'INSERT INTO date_index (contact_qq, date, msg_count, first_msg_index) VALUES (?, ?, ?, ?)',
                            (entry, date_str, len(indices), indices[0])
                        )
                    conn.execute(
                        'INSERT OR REPLACE INTO index_meta (contact_qq, msg_info_mtime) VALUES (?, ?)',
                        (entry, current_mtime)
                    )
                    conn.commit()
        finally:
            with _db_lock:
                try:
                    conn.close()
                except Exception:
                    pass
            _ready_flags[account_dir] = True

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def is_index_ready(account_dir: str) -> bool:
    return _ready_flags.get(account_dir, False)


def get_available_dates(account_dir: str, contact_qq: str) -> list[dict]:
    db_path = get_db_path(account_dir)
    if not os.path.isfile(db_path):
        return []

    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        rows = conn.execute(
            'SELECT date, msg_count FROM date_index WHERE contact_qq = ? ORDER BY date',
            (contact_qq,)
        ).fetchall()
        return [{'date': row[0], 'msg_count': row[1]} for row in rows]
    finally:
        conn.close()


def get_date_jump_index(account_dir: str, contact_qq: str, date: str) -> int | None:
    db_path = get_db_path(account_dir)
    if not os.path.isfile(db_path):
        return None

    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        row = conn.execute(
            'SELECT first_msg_index FROM date_index WHERE contact_qq = ? AND date = ?',
            (contact_qq, date)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
