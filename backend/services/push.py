import logging
import requests
from config import PUSHDEER_KEY

logger = logging.getLogger(__name__)

PUSHDEER_URL = "https://api2.pushdeer.com/message/push"


def send_push_notification(title: str, message: str) -> bool:
    """通过 PushDeer 发送推送通知。失败只记录日志，不影响主流程。"""
    if not PUSHDEER_KEY:
        logger.warning("PushDeer Key 未配置，跳过推送")
        return False

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
