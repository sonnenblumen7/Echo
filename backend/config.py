import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

# 数据库路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "echo.db")

# 看门狗默认阈值（秒）
DEFAULT_WARNING_THRESHOLD = 2700   # 45 分钟
DEFAULT_ALERT_THRESHOLD = 3600     # 60 分钟

# PushDeer 保底通知通道
PUSHDEER_KEY = os.getenv("PUSHDEER_KEY", "")

# SMTP 邮件配置
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# 微信小程序配置
WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")
