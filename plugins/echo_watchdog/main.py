import time
import httpx
from astrbot.api import logger
from astrbot.api.star import Star, Context
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, MessageChain

class EchoWatchdog(Star):
    """Echo 防失联看门狗情感心跳插件"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.fastapi_url = "http://127.0.0.1:8000/internal/heartbeat"
        self.sos_url = "http://127.0.0.1:8000/sos/"
        self.bind_url = "http://127.0.0.1:8000/bind_openid"
        logger.info("EchoWatchdog 插件已加载")

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
    async def on_private_message(self, event: AstrMessageEvent):
        """用户发私聊消息时触发情感心跳"""
        try:
            # 获取消息内容
            message = event.message_str.strip()

            # 获取真实的 openid（从消息事件中提取）
            openid = self._get_openid_from_event(event)

            # 检查是否是绑定命令
            if message.startswith("绑定"):
                await self._handle_bind_command(event, openid, message)
                return  # 拦截消息，不传递给 AI

            # 检查是否是 SOS 关键词
            if self._is_sos_keyword(message):
                logger.info("检测到 SOS 关键词，触发 SOS 告警")
                await self._trigger_sos(event, openid)
                return  # 拦截消息，不传递给 AI

            # 正常情感心跳
            async with httpx.AsyncClient() as client:
                response = await client.post(self.fastapi_url, json={
                    "user_id": openid,
                    "source": "astrbot",
                    "ts": int(time.time())
                }, timeout=5.0)

            if response.status_code == 200:
                logger.info("情感心跳已发送")
            else:
                logger.warning("情感心跳失败: %s", response.status_code)
        except Exception as e:
            logger.error("情感心跳异常: %s", e)

        # 不拦截消息，继续正常处理（不 yield，让消息传递给下一个处理器）

    def _get_openid_from_event(self, event: AstrMessageEvent) -> str:
        """从消息事件中获取真实的 openid"""
        try:
            # 尝试从 session_id 获取 openid
            session_id = event.session.session_id
            if session_id and "@" in session_id:
                # 格式：o9cq8029Z0clgYpSkAnSCQQ9a0ms@im.wechat
                openid = session_id.split("@")[0]
                logger.info("从 session_id 获取 openid: %s", openid[:8] + "****")
                return openid

            # 如果获取不到，返回默认值
            logger.warning("无法从 session_id 获取 openid，使用默认值")
            return "default"
        except Exception as e:
            logger.error("获取 openid 异常: %s", e)
            return "default"

    def _is_sos_keyword(self, message: str) -> bool:
        """检查消息是否是 SOS 关键词"""
        sos_keywords = [
            "sos", "SOS", "Sos",
            "求救", "救命", "紧急", "危险",
            "help", "HELP", "Help",
            "救救我", "我需要帮助", "紧急求救"
        ]
        return message in sos_keywords

    async def _handle_bind_command(self, event: AstrMessageEvent, openid: str, message: str):
        """处理绑定命令"""
        try:
            # 解析绑定命令：绑定 <小程序openid>
            parts = message.split()
            if len(parts) < 2:
                # 格式错误，发送帮助信息
                await self._send_message(event, "绑定格式错误！请使用：绑定 <小程序openid>\n\n例如：绑定 oIXbjxXU19e809U_LAV5eOBxwt80")
                return

            miniprogram_openid = parts[1]
            logger.info("用户 %s 请求绑定小程序 openid: %s", openid[:8] + "****", miniprogram_openid[:8] + "****")

            # 调用后端接口绑定 openid
            async with httpx.AsyncClient() as client:
                response = await client.post(self.bind_url, json={
                    "astrbot_openid": openid,
                    "miniprogram_openid": miniprogram_openid
                }, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    await self._send_message(event, "绑定成功！现在可以通过微信发送 SOS 触发告警了。")
                else:
                    await self._send_message(event, "绑定失败：" + data.get("msg", "未知错误"))
            else:
                await self._send_message(event, "绑定失败：服务器错误")
        except Exception as e:
            logger.error("处理绑定命令异常: %s", e)
            await self._send_message(event, "绑定失败：发生异常")

    async def _send_message(self, event: AstrMessageEvent, message: str):
        """发送消息给用户"""
        try:
            # 使用 AstrBot 的消息发送机制
            event.set_result(MessageChain([Plain(message)]))
        except Exception as e:
            logger.error("发送消息异常: %s", e)

    async def _trigger_sos(self, event: AstrMessageEvent, openid: str):
        """触发 SOS 告警"""
        try:
            # 获取用户位置（如果有）
            # 这里暂时使用默认位置，后续可以集成位置获取
            latitude = 0.0
            longitude = 0.0
            client_ts = int(time.time())

            # 从数据库获取小程序的 openid
            miniprogram_openid = await self._get_miniprogram_openid(openid)
            if not miniprogram_openid:
                logger.warning("用户 %s 未绑定小程序，使用默认 openid", openid[:8] + "****")
                miniprogram_openid = openid

            async with httpx.AsyncClient() as client:
                response = await client.post(self.sos_url, json={
                    "latitude": latitude,
                    "longitude": longitude,
                    "client_ts": client_ts,
                    "wx_openid": miniprogram_openid
                }, timeout=10.0)

            if response.status_code == 200:
                logger.info("SOS 告警已触发，openid=%s", miniprogram_openid[:8] + "****")
            else:
                logger.warning("SOS 告警失败: %s", response.status_code)
        except Exception as e:
            logger.error("SOS 告警异常: %s", e)

    async def _get_miniprogram_openid(self, astrbot_openid: str) -> str:
        """从数据库获取小程序的 openid"""
        try:
            # 调用后端接口查询绑定关系
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/bind_openid/{astrbot_openid}",
                    timeout=5.0
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    return data.get("miniprogram_openid")

            return None
        except Exception as e:
            logger.error("获取小程序 openid 异常: %s", e)
            return None
