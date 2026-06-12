import sqlite3
import logging
from config import DB_PATH, DEFAULT_WARNING_THRESHOLD, DEFAULT_ALERT_THRESHOLD

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """创建数据库连接，强制 WAL + foreign_keys + Row factory。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """创建全部表结构（IF NOT EXISTS）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS heartbeat_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            client_ts INTEGER NOT NULL,
            server_ts INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'physical'
        );

        CREATE TABLE IF NOT EXISTS watchdog_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state TEXT NOT NULL DEFAULT 'normal',
            last_heartbeat_ts INTEGER,
            last_state_change_ts INTEGER,
            email_sent INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS watchdog_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            name TEXT,
            email TEXT DEFAULT '',
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alert_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            channel TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        );
    """)


def create_indexes(conn: sqlite3.Connection) -> None:
    """创建索引。"""
    conn.executescript("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_heartbeat_dedup
            ON heartbeat_log(device_id, client_ts);

        CREATE INDEX IF NOT EXISTS idx_heartbeat_server_ts
            ON heartbeat_log(server_ts);
    """)


def init_watchdog_state(conn: sqlite3.Connection) -> None:
    """确保 watchdog_state 单例行存在。"""
    conn.execute(
        "INSERT OR IGNORE INTO watchdog_state (id, state) VALUES (1, 'normal')"
    )


def init_watchdog_config(conn: sqlite3.Connection) -> None:
    """确保 watchdog_config 默认值存在。"""
    conn.executemany(
        "INSERT OR IGNORE INTO watchdog_config (key, value) VALUES (?, ?)",
        [
            ("warning_threshold", str(DEFAULT_WARNING_THRESHOLD)),
            ("alert_threshold", str(DEFAULT_ALERT_THRESHOLD)),
        ],
    )


def init_db() -> None:
    """编排函数：建表 → 建索引 → 初始化单例。由 FastAPI lifespan 显式调用。"""
    conn = get_connection()
    try:
        create_tables(conn)
        create_indexes(conn)
        init_watchdog_state(conn)
        init_watchdog_config(conn)
        conn.commit()
        logger.info("数据库初始化完成: %s", DB_PATH)
    finally:
        conn.close()


def get_db() -> sqlite3.Connection:
    """对外唯一入口：返回已初始化的请求级连接。调用方负责关闭。"""
    return get_connection()
