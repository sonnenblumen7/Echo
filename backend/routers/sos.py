import time
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from models.database import get_db
from services.watchdog import transition_state
from services.alert import trigger_alert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sos", tags=["SOS"])


class SosRequest(BaseModel):
    latitude: float
    longitude: float
    client_ts: int


@router.post("/")
async def sos(req: SosRequest):
    server_ts = int(time.time())

    # 1. 写入 heartbeat_log，type='sos'，留存铁证
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO heartbeat_log "
            "(device_id, latitude, longitude, client_ts, server_ts, type) "
            "VALUES (?, ?, ?, ?, ?, 'sos')",
            ("sos", req.latitude, req.longitude, req.client_ts, server_ts),
        )
        conn.commit()
    except Exception as e:
        logger.error("SOS heartbeat_log 写入失败: %s", e)
        return {"status": "error", "msg": "database write failed"}
    finally:
        conn.close()

    # 2. 强制切入告警态，防状态脑裂
    transition_state("alert")

    # 3. 立即触发告警
    result = trigger_alert(req.latitude, req.longitude, server_ts, source="SOS_BUTTON")

    logger.warning("SOS 触发: lat=%f, lng=%f, result=%s", req.latitude, req.longitude, result)
    return {"status": "alert_triggered", "reason": "sos"}
