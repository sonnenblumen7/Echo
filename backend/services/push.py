import logging
import requests

logger = logging.getLogger(__name__)

PUSHDEER_URL = "https://api2.pushdeer.com/message/push"
PUSHDEER_KEY = "PDU41972TRdj61c8JhDI3pokasKyKLd41yc49ZZxx"


def send_push_notification(title: str, message: str) -> bool:
    """通过 PushDeer 发送推送通知。失败只记录日志，不影响主流程。"""
    try:
        resp = requests.post(PUSHDEER_URL, data={
            "pushkey": PUSHDEER_KEY,
            "text": title,
            "desp": message,
            "type": "markdown",
        }, timeout=5)
        if resp.status_code == 200:
            logger.info("PushDeer 推送成功: %s", title)
            return True
        else:
            logger.warning("PushDeer 推送失败: status=%d, body=%s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.warning("PushDeer 推送异常: %s", e)
        return False
