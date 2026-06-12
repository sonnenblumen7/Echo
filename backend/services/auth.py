import httpx
import logging
from config import WX_APPID, WX_SECRET

logger = logging.getLogger(__name__)


async def code2session(code: str) -> dict:
    """用微信登录 code 换取 openid 和 session_key。

    Args:
        code: wx.login() 获取的临时凭证

    Returns:
        dict: {"openid": "xxx", "session_key": "xxx"} 或 {"error": "xxx"}
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WX_APPID,
        "secret": WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()

        if "errcode" in data and data["errcode"] != 0:
            logger.error("微信 code2session 失败: %s", data)
            return {"error": data.get("errmsg", "未知错误")}

        openid = data.get("openid")
        session_key = data.get("session_key")

        if not openid:
            logger.error("微信返回无 openid: %s", data)
            return {"error": "获取 openid 失败"}

        logger.info("微信登录成功: openid=%s", openid[:8] + "****")
        return {"openid": openid, "session_key": session_key}

    except httpx.TimeoutException:
        logger.error("微信接口超时")
        return {"error": "微信接口超时"}
    except Exception as e:
        logger.error("微信登录异常: %s", e)
        return {"error": str(e)}
