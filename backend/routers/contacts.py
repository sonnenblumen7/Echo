import re
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from services.contacts import add_contact, get_contacts, delete_contact
from services.notification import send_test_sms

logger = logging.getLogger(__name__)
router = APIRouter()


class ContactRequest(BaseModel):
    phone: str
    name: str = None

    @model_validator(mode="after")
    def validate_phone(self):
        if not re.match(r"^1[3-9]\d{9}$", self.phone):
            raise ValueError("手机号格式错误：需为 11 位中国大陆手机号")
        return self


@router.post("/contacts")
async def create_contact(req: ContactRequest):
    contact, duplicate = add_contact(req.phone, req.name)
    if duplicate:
        raise HTTPException(status_code=409, detail="该手机号已存在")

    sms_result = send_test_sms(req.phone)
    return {
        "status": "ok",
        "contact": contact,
        "test_sms": sms_result,
    }


@router.get("/contacts")
async def list_contacts():
    return {"status": "ok", "contacts": get_contacts()}


@router.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: int):
    if not delete_contact(contact_id):
        raise HTTPException(status_code=404, detail="联系人不存在")
    return {"status": "ok", "msg": "deleted"}
