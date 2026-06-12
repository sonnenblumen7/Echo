import time
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sleep"])


class SleepRequest(BaseModel):
    hours: int = 8


@router.post("/sleep")
async def set_sleep(req: SleepRequest):
    """设置睡眠模式：暂停守护 N 小时。"""
    if req.hours < 1 or req.hours > 24:
        return {"status": "error", "msg": "hours must be 1-24"}

    now_ts = int(time.time())
    sleep_until = now_ts + req.hours * 3600

    conn = get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchdog_config (key, value) VALUES ('sleep_until', ?)",
            (str(sleep_until),),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("睡眠模式已启用: %d 小时, sleep_until=%d", req.hours, sleep_until)
    return {"status": "ok", "sleep_until": sleep_until}


@router.get("/sleep")
async def get_sleep():
    """查询睡眠模式状态。"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT value FROM watchdog_config WHERE key = 'sleep_until'"
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return {"enabled": False, "sleep_until": 0}

    sleep_until = int(row["value"])
    now_ts = int(time.time())

    if now_ts >= sleep_until:
        # 已过期，清除
        _clear_sleep()
        return {"enabled": False, "sleep_until": 0}

    return {"enabled": True, "sleep_until": sleep_until}


@router.delete("/sleep")
async def cancel_sleep():
    """取消睡眠模式。"""
    _clear_sleep()
    logger.info("睡眠模式已取消")
    return {"status": "ok", "msg": "sleep cancelled"}


def _clear_sleep():
    """清除 sleep_until 配置。"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM watchdog_config WHERE key = 'sleep_until'")
        conn.commit()
    finally:
        conn.close()


def get_sleep_until() -> int:
    """获取 sleep_until 时间戳，未设置返回 0。"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT value FROM watchdog_config WHERE key = 'sleep_until'"
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return 0

    sleep_until = int(row["value"])
    now_ts = int(time.time())

    if now_ts >= sleep_until:
        _clear_sleep()
        return 0

    return sleep_until
