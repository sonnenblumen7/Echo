import time
import httpx
from astrbot.api import logger
from astrbot.api.star import Star

class EchoWatchdog(Star):
    """Echo 防失联看门狗情感心跳插件"""

    def __init__(self, context):
        super().__init__(context)
        self.fastapi_url = "http://127.0.0.1:8000/internal/heartbeat"
        logger.info("EchoWatchdog 插件已加载")

    async def on_message(self, event):
        """用户发消息时触发情感心跳"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.fastapi_url, json={
                    "user_id": "default",
                    "source": "astrbot",
                    "ts": int(time.time())
                }, timeout=5.0)

            if response.status_code == 200:
                logger.info("情感心跳已发送")
            else:
                logger.warning("情感心跳失败: %s", response.status_code)
        except Exception as e:
            logger.error("情感心跳异常: %s", e)

        # 不拦截消息，继续正常处理
        return True
