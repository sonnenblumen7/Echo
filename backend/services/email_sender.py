import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

logger = logging.getLogger(__name__)


def send_alert_email(to_email: str, latitude: float, longitude: float,
                     last_heartbeat_ts: int) -> bool:
    """发送告警邮件到紧急联系人。

    Args:
        to_email: 收件人邮箱
        latitude: 纬度
        longitude: 经度
        last_heartbeat_ts: 最后心跳时间戳

    Returns:
        bool: 是否发送成功
    """
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        logger.warning("SMTP 配置不完整，跳过邮件发送")
        return False

    if not to_email:
        logger.warning("收件人邮箱为空，跳过发送")
        return False

    subject = "【Echo守护】联系人状态提醒"
    body = _build_email_body(latitude, longitude, last_heartbeat_ts)

    return _send_email(to_email, subject, body)


def _build_email_body(latitude: float, longitude: float,
                      last_heartbeat_ts: int) -> str:
    """构建邮件正文。"""
    time_str = datetime.fromtimestamp(last_heartbeat_ts).strftime("%Y-%m-%d %H:%M:%S")
    map_link = f"https://uri.amap.com/marker?position={longitude},{latitude}"

    return f"""系统检测到用户长时间未更新状态。

最近状态时间：
{time_str}

最近位置：
纬度：{latitude}
经度：{longitude}

高德地图查看：
{map_link}

请尽快通过电话、微信等方式联系确认情况。

此邮件由 Echo 自动发送。"""


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """通过 SMTP 发送邮件。"""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # QQ 邮箱使用 SSL
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        logger.info("告警邮件已发送: to=%s", to_email)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 认证失败，请检查用户名和授权码")
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP 发送失败: %s", e)
        return False
    except Exception as e:
        logger.error("邮件发送异常: %s", e)
        return False


def test_smtp_connection() -> bool:
    """测试 SMTP 连接是否正常。"""
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            logger.info("SMTP 连接测试成功")
            return True
    except Exception as e:
        logger.error("SMTP 连接测试失败: %s", e)
        return False
