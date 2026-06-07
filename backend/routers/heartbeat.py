import time
import logging
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from models.database import get_db
from services.watchdog import reset_watchdog

logger = logging.getLogger(__name__)
router = APIRouter()


class HeartbeatItem(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    client_ts: int
    type: str = "physical"


@router.post("/heartbeat")
async def heartbeat(items: List[HeartbeatItem]):
    if not items:
        return {"status": "ok", "received": 0, "msg": "empty batch"}

    server_ts = int(time.time())
    conn = get_db()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO heartbeat_log "
            "(device_id, latitude, longitude, client_ts, server_ts, type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (item.device_id, item.latitude, item.longitude,
                 item.client_ts, server_ts, item.type)
                for item in items
            ],
        )
        conn.commit()
    except Exception as e:
        logger.error("heartbeat 写入失败: %s", e)
        return {"status": "error", "msg": "database write failed"}
    finally:
        conn.close()

    try:
        reset_watchdog()
    except Exception as e:
        logger.error("reset_watchdog 失败: %s", e)
        return {"status": "error", "msg": "watchdog reset failed"}

    last = items[-1]
    logger.info("heartbeat: %d 条, lat=%.5f, lng=%.5f, device=%s",
                len(items), last.latitude, last.longitude, last.device_id)
    return {"status": "ok", "received": len(items), "msg": "heartbeat processed"}
