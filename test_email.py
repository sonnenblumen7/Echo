#!/usr/bin/env python3
"""
邮件通知系统测试脚本

使用方法：
    cd backend
    source .venv/bin/activate
    python ../test_email.py
"""

import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv()

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
from services.email_sender import test_smtp_connection, send_alert_email


def print_config():
    """打印当前 SMTP 配置。"""
    print("\n=== SMTP 配置 ===")
    print(f"SMTP_HOST: {SMTP_HOST}")
    print(f"SMTP_PORT: {SMTP_PORT}")
    print(f"SMTP_USER: {SMTP_USER}")
    print(f"SMTP_PASSWORD: {'*' * 8 if SMTP_PASSWORD else '未配置'}")
    print()


def test_connection():
    """测试 SMTP 连接。"""
    print("\n=== 测试 1: SMTP 连接 ===")
    if test_smtp_connection():
        print("✅ SMTP 连接成功")
        return True
    else:
        print("❌ SMTP 连接失败")
        print("请检查：")
        print("  1. .env 文件中的 SMTP 配置")
        print("  2. QQ邮箱 SMTP 是否已开启")
        print("  3. 授权码是否正确")
        return False


def test_send_email():
    """测试发送邮件。"""
    print("\n=== 测试 2: 发送告警邮件 ===")

    # 使用配置中的邮箱作为测试收件人
    test_email = SMTP_USER

    print(f"收件人: {test_email}")
    print("发送中...")

    # 模拟数据
    latitude = 39.9042
    longitude = 116.4074
    last_heartbeat_ts = 1718123456

    if send_alert_email(test_email, latitude, longitude, last_heartbeat_ts):
        print("✅ 邮件发送成功")
        print(f"请检查 {test_email} 的收件箱（可能在垃圾邮件中）")
        return True
    else:
        print("❌ 邮件发送失败")
        return False


def main():
    """主测试流程。"""
    print("=" * 50)
    print("Echo 邮件通知系统测试")
    print("=" * 50)

    print_config()

    # 检查配置
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        print("❌ SMTP 配置不完整！")
        print("\n请在 .env 文件中添加以下配置：")
        print("SMTP_HOST=smtp.qq.com")
        print("SMTP_PORT=465")
        print("SMTP_USER=你的QQ邮箱@qq.com")
        print("SMTP_PASSWORD=你的QQ邮箱授权码")
        print("\n获取授权码：")
        print("1. 登录 QQ 邮箱")
        print("2. 设置 → 账户")
        print("3. POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务")
        print("4. 开启 POP3/SMTP 服务")
        print("5. 生成授权码")
        return

    # 测试连接
    if not test_connection():
        return

    # 测试发送
    test_send_email()

    print("\n=== 测试完成 ===")
    print("\n如果邮件发送成功，可以进行以下测试：")
    print("1. 在小程序中添加带邮箱的联系人")
    print("2. 等待看门狗进入 critical 状态")
    print("3. 检查是否收到告警邮件")


if __name__ == "__main__":
    main()
