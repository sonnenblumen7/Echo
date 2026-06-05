import asyncio
import logging
import time

from services.watchdog import get_watchdog_state, get_config, transition_state

logger = logging.getLogger(__name__)


async def watchdog_loop() -> None:
    """看门狗守护进程。30 秒轮询，SQLite 为唯一状态源。"""
    while True:
        await asyncio.sleep(30)
        try:
            _check_once()
        except Exception as e:
            logger.error("watchdog 检查异常: %s", e)


def _check_once() -> None:
    """单次检查逻辑。拆出便于测试。"""
    state = get_watchdog_state()
    config = get_config()

    if not state.get("last_heartbeat_ts"):
        return

    now_ts = int(time.time())
    elapsed = now_ts - state["last_heartbeat_ts"]
    current = state["state"]
    warning_threshold = config.get("warning_threshold", 2700)
    alert_threshold = config.get("alert_threshold", 3600)

    if elapsed >= alert_threshold and current != "alert":
        logger.warning("状态迁移: %s → alert (已 %d 秒无心跳)", current, elapsed)
        transition_state("alert")

    elif elapsed >= warning_threshold and current == "normal":
        logger.info("状态迁移: normal → warning (已 %d 秒无心跳)", elapsed)
        transition_state("warning")

    # warning → warning / alert → alert: 不重复触发
