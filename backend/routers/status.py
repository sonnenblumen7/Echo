import logging

from fastapi import APIRouter

from services.watchdog import get_watchdog_state, get_remaining

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def status():
    state = get_watchdog_state()
    return {
        "state": state.get("state", "unknown"),
        "remaining_seconds": get_remaining(),
        "last_heartbeat_ts": state.get("last_heartbeat_ts"),
    }
