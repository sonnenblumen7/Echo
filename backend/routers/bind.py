import logging

from fastapi import APIRouter
from pydantic import BaseModel

from models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["bind"])


class BindRequest(BaseModel):
    astrbot_openid: str
    miniprogram_openid: str


@router.post("/bind_openid")
async def bind_openid(req: BindRequest):
    """绑定 AstrBot openid 和小程序 openid"""
    conn = get_db()
    try:
        # 检查是否已存在绑定关系
        existing = conn.execute(
            "SELECT id FROM openid_bind WHERE astrbot_openid = ?",
            (req.astrbot_openid,)
        ).fetchone()

        if existing:
            # 更新绑定关系
            conn.execute(
                "UPDATE openid_bind SET miniprogram_openid = ? WHERE astrbot_openid = ?",
                (req.miniprogram_openid, req.astrbot_openid)
            )
        else:
            # 创建新的绑定关系
            conn.execute(
                "INSERT INTO openid_bind (astrbot_openid, miniprogram_openid) VALUES (?, ?)",
                (req.astrbot_openid, req.miniprogram_openid)
            )

        conn.commit()
        logger.info("openid 绑定成功: %s -> %s", req.astrbot_openid[:8] + "****", req.miniprogram_openid[:8] + "****")
        return {"status": "ok", "msg": "绑定成功"}
    except Exception as e:
        logger.error("openid 绑定失败: %s", e)
        return {"status": "error", "msg": "绑定失败"}
    finally:
        conn.close()


@router.get("/bind_openid/{astrbot_openid}")
async def get_bind_openid(astrbot_openid: str):
    """获取绑定的小程序 openid"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT miniprogram_openid FROM openid_bind WHERE astrbot_openid = ?",
            (astrbot_openid,)
        ).fetchone()

        if row:
            return {"status": "ok", "miniprogram_openid": row["miniprogram_openid"]}
        else:
            return {"status": "error", "msg": "未找到绑定关系"}
    except Exception as e:
        logger.error("获取绑定关系失败: %s", e)
        return {"status": "error", "msg": "查询失败"}
    finally:
        conn.close()
