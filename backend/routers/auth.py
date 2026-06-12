import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.auth import code2session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    code: str


@router.post("/login")
async def login(req: LoginRequest):
    """微信登录：用 code 换取 openid。

    前端调用 wx.login() 获取 code，发送到此接口。
    后端用 code 换取 openid，返回给前端存储。
    """
    if not req.code:
        raise HTTPException(status_code=400, detail="code 不能为空")

    result = await code2session(req.code)

    if "error" in result:
        logger.warning("登录失败: %s", result["error"])
        raise HTTPException(status_code=401, detail=result["error"])

    # 只返回 openid，不返回 session_key（安全考虑）
    return {
        "status": "ok",
        "openid": result["openid"],
    }
