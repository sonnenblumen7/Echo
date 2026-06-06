import logging
from models.database import get_db

logger = logging.getLogger(__name__)


def get_config() -> dict:
    """读取 watchdog_config 全部配置，返回 dict。"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value FROM watchdog_config").fetchall()
        return {row["key"]: int(row["value"]) for row in rows}
    finally:
        conn.close()


def update_config(warning_threshold: int, alert_threshold: int) -> dict:
    """更新看门狗阈值配置。异常向上传播。"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchdog_config (key, value) VALUES (?, ?)",
            ("warning_threshold", str(warning_threshold)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO watchdog_config (key, value) VALUES (?, ?)",
            ("alert_threshold", str(alert_threshold)),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("配置已更新: warning=%d, alert=%d", warning_threshold, alert_threshold)
    return {"warning_threshold": warning_threshold, "alert_threshold": alert_threshold}
