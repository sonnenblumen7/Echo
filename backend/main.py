import asyncio
import time
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from models.database import init_db, get_db
from services.watchdog import reset_watchdog, get_watchdog_state, get_remaining
from daemon.watchdog_daemon import watchdog_loop

logger = logging.getLogger(__name__)


# ── Pydantic 模型 ──────────────────────────────────────────────

class HeartbeatItem(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    client_ts: int
    type: str = "physical"


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(watchdog_loop())
    logger.info("Echo API 启动，watchdog_daemon 已启动")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Echo API 关闭")


# ── App ────────────────────────────────────────────────────────

app = FastAPI(title="Echo API", version="0.1.0", lifespan=lifespan)


# ── 路由 ───────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    state = get_watchdog_state()
    return {
        "state": state.get("state", "unknown"),
        "remaining_seconds": get_remaining(),
        "last_heartbeat_ts": state.get("last_heartbeat_ts"),
    }


@app.post("/heartbeat")
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

    return {"status": "ok", "received": len(items), "msg": "heartbeat processed"}
