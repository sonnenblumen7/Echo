import re
import logging

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, model_validator
from typing import Optional

from services.contacts import add_contact, get_contacts, delete_contact
from services.notification import send_test_sms

logger = logging.getLogger(__name__)
router = APIRouter()


class ContactRequest(BaseModel):
    phone: str = ""
    name: str = None
    email: str = ""

    @model_validator(mode="after")
    def validate_contact(self):
        # 手机号和邮箱至少填一个
        if not self.phone and not self.email:
            raise ValueError("手机号和邮箱至少填写一项")

        # 验证手机号格式（如果填写了）
        if self.phone and not re.match(r"^1[3-9]\d{9}$", self.phone):
            raise ValueError("手机号格式错误：需为 11 位中国大陆手机号")

        # 验证邮箱格式（如果填写了）
        if self.email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", self.email):
            raise ValueError("邮箱格式错误")

        return self


@router.post("/contacts")
async def create_contact(req: ContactRequest, x_wx_openid: Optional[str] = Header(None)):
    if not x_wx_openid:
        raise HTTPException(status_code=401, detail="缺少用户标识")

    contact, duplicate = add_contact(x_wx_openid, req.phone, req.name, req.email)
    if duplicate:
        raise HTTPException(status_code=409, detail="该手机号或邮箱已存在")

    # 如果有手机号，发送测试短信
    sms_result = None
    if req.phone:
        sms_result = send_test_sms(req.phone)

    return {
        "status": "ok",
        "contact": contact,
        "test_sms": sms_result,
    }


@router.get("/contacts")
async def list_contacts(x_wx_openid: Optional[str] = Header(None)):
    if not x_wx_openid:
        raise HTTPException(status_code=401, detail="缺少用户标识")

    return {"status": "ok", "contacts": get_contacts(x_wx_openid)}


@router.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: int, x_wx_openid: Optional[str] = Header(None)):
    if not x_wx_openid:
        raise HTTPException(status_code=401, detail="缺少用户标识")

    if not delete_contact(contact_id, x_wx_openid):
        raise HTTPException(status_code=404, detail="联系人不存在")
    return {"status": "ok", "msg": "deleted"}
