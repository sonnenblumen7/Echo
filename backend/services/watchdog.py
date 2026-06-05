import time
import logging
from models.database import get_db

logger = logging.getLogger(__name__)


def get_watchdog_state() -> dict:
    """读取 watchdog_state 单例行。"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT state, last_heartbeat_ts, last_state_change_ts "
            "FROM watchdog_state WHERE id = 1"
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_remaining() -> int:
    """计算距告警触发的剩余秒数。返回 0 表示已超时。"""
    conn = get_db()
    try:
        state = conn.execute(
            "SELECT last_heartbeat_ts FROM watchdog_state WHERE id = 1"
        ).fetchone()
        threshold = conn.execute(
            "SELECT value FROM watchdog_config WHERE key = 'alert_threshold'"
        ).fetchone()
    finally:
        conn.close()

    if not state or not state["last_heartbeat_ts"]:
        return 0

    alert_threshold = int(threshold["value"]) if threshold else 3600
    elapsed = int(time.time()) - state["last_heartbeat_ts"]
    return max(0, alert_threshold - elapsed)


def reset_watchdog() -> None:
    """重置看门狗：更新 last_heartbeat_ts，state 复位为 normal。

    异常向上传播，由调用方决定如何处理。
    """
    now_ts = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            "UPDATE watchdog_state "
            "SET last_heartbeat_ts = ?, state = 'normal', last_state_change_ts = NULL "
            "WHERE id = 1",
            (now_ts,),
        )
        conn.commit()
    finally:
        conn.close()


def get_config() -> dict:
    """读取 watchdog_config 全部配置，返回 dict。"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT key, value FROM watchdog_config").fetchall()
        return {row["key"]: int(row["value"]) for row in rows}
    finally:
        conn.close()


def transition_state(new_state: str) -> None:
    """执行状态迁移，记录 last_state_change_ts。由 daemon 调用。"""
    now_ts = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            "UPDATE watchdog_state "
            "SET state = ?, last_state_change_ts = ? "
            "WHERE id = 1",
            (new_state, now_ts),
        )
        conn.commit()
    except Exception as e:
        logger.error("transition_state 失败: %s", e)
    finally:
        conn.close()
