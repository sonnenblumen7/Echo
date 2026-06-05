import os

# 数据库路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "echo.db")

# 看门狗默认阈值（秒）
DEFAULT_WARNING_THRESHOLD = 2700   # 45 分钟
DEFAULT_ALERT_THRESHOLD = 3600     # 60 分钟
