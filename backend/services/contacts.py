import time
import logging
from models.database import get_db

logger = logging.getLogger(__name__)


def add_contact(phone: str = "", name: str = None, email: str = "") -> tuple:
    """添加联系人。返回 (contact_dict, duplicate_bool)。"""
    conn = get_db()
    try:
        # 检查手机号重复（如果有手机号）
        if phone:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE phone = ?", (phone,)
            ).fetchone()
            if existing:
                return None, True

        # 检查邮箱重复（如果有邮箱）
        if email:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                return None, True

        now = int(time.time())
        cursor = conn.execute(
            "INSERT INTO contacts (phone, name, email, created_at) VALUES (?, ?, ?, ?)",
            (phone, name, email, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "phone": phone, "name": name, "email": email, "created_at": now}, False
    finally:
        conn.close()


def get_contacts() -> list:
    """查询全部联系人。"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, phone, name, email, created_at FROM contacts ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_contacts_with_email() -> list:
    """查询有邮箱的联系人。"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, phone, name, email, created_at FROM contacts WHERE email != '' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_contact(contact_id: int) -> bool:
    """删除联系人。返回是否删除成功。"""
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
