import time
import logging
from models.database import get_db
from services.contacts import get_contacts, get_contacts_with_email
from services.notification import send_sms_alert
from services.push import send_push_notification
from services.email_sender import send_alert_email
from services.watchdog import is_email_sent, mark_email_sent

logger = logging.getLogger(__name__)

MAX_RETRY = 5


def trigger_alert(wx_openid: str, latitude: float, longitude: float, timestamp: int,
                  source: str = "WATCHDOG_TIMEOUT") -> dict:
    """触发告警：遍历联系人发送 SMS，失败则写入 alert_queue。

    source: "SOS_BUTTON" | "WATCHDOG_TIMEOUT"
    """
    contacts = get_contacts(wx_openid)
    if not contacts:
        logger.warning("trigger_alert: 无紧急联系人，跳过")
        return {"sent": 0, "queued": 0, "reason": "no contacts"}

    message = _build_message(latitude, longitude, timestamp, source)
    sent = 0
    queued = 0

    for contact in contacts:
        # 短信发送（如果有手机号）
        if contact.get("phone"):
            result = send_sms_alert(contact["phone"], message)
            if result.get("sent"):
                sent += 1
            else:
                _queue_alert(contact["id"], contact["phone"], message)
                queued += 1

    logger.info("trigger_alert 完成 [%s]: sent=%d, queued=%d", source, sent, queued)

    # PushDeer 推送（额外通道，失败不影响主流程）
    _push_deer(source, latitude, longitude, timestamp)

    # 邮件告警（SOS 和 Watchdog 都发送，避免重复）
    if not is_email_sent():
        _send_email_alerts(wx_openid, latitude, longitude, timestamp)

    return {"sent": sent, "queued": queued}


def _send_email_alerts(wx_openid: str, latitude: float, longitude: float, timestamp: int) -> None:
    """发送邮件告警给所有有邮箱的联系人。"""
    contacts = get_contacts_with_email(wx_openid)
    if not contacts:
        logger.info("无邮箱联系人，跳过邮件告警")
        return

    email_sent_count = 0
    for contact in contacts:
        if send_alert_email(contact["email"], latitude, longitude, timestamp):
            email_sent_count += 1

    if email_sent_count > 0:
        mark_email_sent()
        logger.info("邮件告警已发送给 %d 位联系人", email_sent_count)
    else:
        logger.warning("邮件告警发送失败")


def process_alert_queue() -> dict:
    """处理告警队列：重试发送，超过 MAX_RETRY 标记为 failed。"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, contact_id, channel, message, retry_count "
            "FROM alert_queue WHERE status = 'pending'"
        ).fetchall()
    finally:
        conn.close()

    retried = 0
    failed = 0

    for row in rows:
        alert_id = row["id"]
        phone = _get_phone_by_contact_id(row["contact_id"])
        new_retry = row["retry_count"] + 1

        if new_retry >= MAX_RETRY:
            _update_alert(alert_id, "failed", new_retry)
            failed += 1
            logger.warning("告警 %d 达到最大重试次数，标记 failed", alert_id)
            continue

        result = send_sms_alert(phone, row["message"])
        if result.get("sent"):
            _update_alert(alert_id, "sent", new_retry)
            logger.info("告警 %d 重试成功 (第 %d 次)", alert_id, new_retry)
        else:
            _update_alert(alert_id, "pending", new_retry)
            logger.info("告警 %d 重试失败 (第 %d 次)，保留在队列", alert_id, new_retry)

        retried += 1

    return {"retried": retried, "failed": failed}


# ── 内部函数 ──────────────────────────────────────────────────

def _build_message(latitude: float, longitude: float, timestamp: int,
                   source: str) -> str:
    map_link = f"https://uri.amap.com/marker?position={longitude},{latitude}"

    if source == "SOS_BUTTON":
        return (
            f"【Echo 主动求救】\n"
            f"用户已按下 SOS 按钮，可能遭遇紧急危险！\n"
            f"最后已知位置：{latitude}, {longitude}\n"
            f"求救时间：{timestamp}\n"
            f"高德地图查看：{map_link}\n"
            f"请立即联系此人，必要时报警。"
        )
    else:
        return (
            f"【Echo 防失联告警】\n"
            f"用户已超过 60 分钟未响应，可能处于失联状态。\n"
            f"最后已知位置：{latitude}, {longitude}\n"
            f"最后活跃时间：{timestamp}\n"
            f"高德地图查看：{map_link}\n"
            f"请立即尝试联系此人，必要时报警。"
        )


def _queue_alert(contact_id: int, phone: str, message: str) -> None:
    now = int(time.time())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO alert_queue (contact_id, channel, message, status, retry_count, created_at) "
            "VALUES (?, ?, ?, 'pending', 0, ?)",
            (contact_id, "sms", message, now),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info("告警已入队: contact_id=%d, phone=%s", contact_id, phone)


def _update_alert(alert_id: int, status: str, retry_count: int) -> None:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE alert_queue SET status = ?, retry_count = ? WHERE id = ?",
            (status, retry_count, alert_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_phone_by_contact_id(contact_id: int) -> str:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT phone FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        return row["phone"] if row else "unknown"
    finally:
        conn.close()


def _push_deer(source: str, latitude: float, longitude: float, timestamp: int) -> None:
    """PushDeer 推送，失败只记日志。"""
    import datetime
    map_link = f"https://uri.amap.com/marker?position={longitude},{latitude}"
    time_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    if source == "SOS_BUTTON":
        title = "🚨 Echo SOS"
    else:
        title = "⚠️ Echo Watchdog Alert"

    message = (
        f"**来源**: {source}\n"
        f"**时间**: {time_str}\n"
        f"**坐标**: {latitude}, {longitude}\n"
        f"**地图**: [高德导航]({map_link})"
    )

    send_push_notification(title, message)
