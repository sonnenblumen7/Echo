import time
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from services.watchdog import reset_watchdog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


class EmotionalHeartbeat(BaseModel):
    user_id: str = "default"
    source: str = "astrbot"
    ts: int = None


@router.post("/heartbeat")
async def internal_heartbeat(req: EmotionalHeartbeat):
    try:
        reset_watchdog()
    except Exception as e:
        logger.error("internal heartbeat reset_watchdog 失败: %s", e)
        return {"status": "error", "msg": "watchdog reset failed"}

    logger.info("情感心跳: user=%s, source=%s", req.user_id, req.source)
    return {"status": "ok"}
