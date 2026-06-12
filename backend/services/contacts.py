import time
import logging
from models.database import get_db

logger = logging.getLogger(__name__)


def add_contact(wx_openid: str, phone: str = "", name: str = None, email: str = "") -> tuple:
    """添加联系人。返回 (contact_dict, duplicate_bool)。"""
    conn = get_db()
    try:
        # 检查手机号重复（在同一用户下）
        if phone:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE wx_openid = ? AND phone = ?",
                (wx_openid, phone)
            ).fetchone()
            if existing:
                return None, True

        # 检查邮箱重复（在同一用户下）
        if email:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE wx_openid = ? AND email = ?",
                (wx_openid, email)
            ).fetchone()
            if existing:
                return None, True

        now = int(time.time())
        cursor = conn.execute(
            "INSERT INTO contacts (wx_openid, phone, name, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (wx_openid, phone, name, email, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "phone": phone, "name": name, "email": email, "created_at": now}, False
    finally:
        conn.close()


def get_contacts(wx_openid: str) -> list:
    """查询指定用户的联系人。"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, phone, name, email, created_at FROM contacts WHERE wx_openid = ? ORDER BY id",
            (wx_openid,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_contacts_with_email(wx_openid: str) -> list:
    """查询指定用户有邮箱的联系人。"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, phone, name, email, created_at FROM contacts WHERE wx_openid = ? AND email != '' ORDER BY id",
            (wx_openid,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_contact(contact_id: int, wx_openid: str) -> bool:
    """删除联系人（只能删除自己的）。返回是否删除成功。"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM contacts WHERE id = ? AND wx_openid = ?",
            (contact_id, wx_openid)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
