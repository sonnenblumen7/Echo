import logging

logger = logging.getLogger(__name__)

# ── 测试开关 ──────────────────────────────────────────────────
# True = 模拟发送成功，False = 模拟发送失败（触发重试逻辑）
MOCK_SMS_SUCCESS = True


def send_sms_alert(phone: str, message: str) -> dict:
    """发送告警短信。当前为 mock 实现，由 MOCK_SMS_SUCCESS 控制结果。"""
    if MOCK_SMS_SUCCESS:
        logger.info("send_sms_alert 成功: phone=%s", phone)
        return {"sent": True}
    else:
        logger.warning("send_sms_alert 失败: phone=%s", phone)
        return {"sent": False, "reason": "mock failure"}


def send_direct_warning(phone: str, message: str) -> dict:
    """预警消息直推占位。后续接 Server酱/SMS 时替换内部实现。"""
    logger.info("send_direct_warning 占位调用: phone=%s, message=%s", phone, message)
    return {"sent": False, "reason": "SMS not configured"}


def send_test_sms(phone: str) -> dict:
    """测试短信占位。"""
    logger.info("send_test_sms 占位调用: phone=%s", phone)
    return {"sent": False, "reason": "SMS not configured"}
