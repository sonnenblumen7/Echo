import asyncio
import logging
import time

from services.watchdog import get_watchdog_state, get_last_location, transition_state
from services.config import get_config
from services.alert import trigger_alert, process_alert_queue
from services.notification import send_direct_warning
from routers.sleep import get_sleep_until

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
    # 检查睡眠模式
    sleep_until = get_sleep_until()
    if sleep_until > 0:
        now_ts = int(time.time())
        if now_ts < sleep_until:
            remaining = sleep_until - now_ts
            logger.debug("睡眠模式中，剩余 %d 秒", remaining)
            return

    state = get_watchdog_state()
    config = get_config()

    # 每轮处理告警重试队列
    process_alert_queue()

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
        _on_alert()

    elif elapsed >= warning_threshold and current == "normal":
        logger.info("状态迁移: normal → warning (已 %d 秒无心跳)", elapsed)
        transition_state("warning")
        _on_warning()

    # warning → warning / alert → alert: 不重复触发


def _on_warning() -> None:
    """预警触发：占位日志，不发送实际通知。"""
    send_direct_warning("owner", "检测到您已长时间未更新状态，请问是否安全？")


def _on_alert() -> None:
    """告警触发：获取最后坐标，通知所有紧急联系人。"""
    # 获取最后一条心跳的 openid
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT wx_openid FROM heartbeat_log WHERE type = 'physical' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if not row or not row["wx_openid"]:
        logger.warning("无心跳记录或无 openid，跳过告警")
        return

    wx_openid = row["wx_openid"]
    loc = get_last_location()
    lat = loc.get("latitude", 0.0)
    lng = loc.get("longitude", 0.0)
    ts = loc.get("client_ts", int(time.time()))
    trigger_alert(wx_openid, lat, lng, ts, source="WATCHDOG_TIMEOUT")
