# Echo — ARCHITECTURE.md

> 最终架构设计文档（定稿 v4）

## 1. 系统总览

```
┌──────────────────────────────────────────────────────────┐
│                      微信小程序                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │ 前台定位采集  │  │ SOS 按钮     │  │ 紧急联系人设置页  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────────────┘  │
└─────────┼───────────────┼────────────────────────────────┘
          │               │
          ▼               ▼
┌──────────────────────────────────────────────────────────┐
│                    FastAPI 后端                           │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ /heartbeat    │  │ /sos         │  │ /internal/hb   │  │
│  │ (批量+去重)   │  │ (紧急阻断)    │  │ (AstrBot回调)  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                 │                   │           │
│         └────────┬────────┴───────────────────┘           │
│                  ▼                                        │
│         ┌──────────────────┐                              │
│         │  reset_watchdog() │  ← 唯一合法写入路径          │
│         │  services/        │                              │
│         │  watchdog.py      │                              │
│         └────────┬─────────┘                              │
│                  ▼                                        │
│         ┌──────────────────┐    ┌──────────────────────┐  │
│         │   SQLite (WAL)    │◄──│  watchdog_daemon      │  │
│         │   唯一真实状态源    │    │  30s 轮询            │  │
│         └──────────────────┘    │  lifespan 生命周期    │  │
│                                 └──────────┬───────────┘  │
│                                            │              │
│                                            ▼              │
│                                 ┌──────────────────────┐  │
│                                 │   状态迁移引擎         │  │
│                                 │   normal → warning    │  │
│                                 │   warning → alert     │  │
│                                 └──────────┬───────────┘  │
│                                            │              │
│                        ┌───────────────────┼──────┐       │
│                        ▼                   ▼      ▼       │
│               ┌──────────────┐  ┌────────┐ ┌──────────┐   │
│               │ send_direct_  │  │  SMS   │ │  Email   │   │
│               │ warning()     │  │        │ │          │   │
│               │ (预警直推)     │  │ (告警) │ │ (告警)   │   │
│               └──────────────┘  └────────┘ └──────────┘   │
└──────────────────────────────────────────────────────────┘
```

## 2. 看门狗状态机

### 2.1 三态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `normal` | 正常守护中 | 默认状态 / 收到任意心跳 |
| `warning` | 预警（用户可能异常） | 距最后心跳 ≥ warning_threshold（默认 2700s） |
| `alert` | 告警（判定失联） | 距最后心跳 ≥ alert_threshold（默认 3600s） |

### 2.2 状态迁移图

```
           收到心跳                    收到心跳                  收到心跳
  ┌──────────────────┐       ┌──────────────────┐      ┌──────────────────┐
  │                  │       │                  │      │                  │
  ▼                  │       ▼                  │      ▼                  │
┌────────┐  超阈值   │    ┌─────────┐  超阈值   │   ┌─────────┐           │
│ normal ├──────────►│    │ warning ├──────────►│   │  alert  │           │
│        │          │    │         │           │   │         │           │
└────────┘          │    └────┬────┘           │   └────┬────┘           │
    ▲               │         │               │        │                │
    │               │         │  收到心跳      │        │  收到心跳       │
    │               │         └───────────────►│        └────────────────│
    │               │                          │                         │
    └───────────────┴──────────────────────────┴─────────────────────────┘
```

### 2.3 动作触发规则

| 迁移 | 动作 | 防重发 |
|------|------|--------|
| `normal → warning` | 调用 `send_direct_warning()` | 记录 `last_state_change_ts` |
| `warning → alert` | 调用 `send_alert()`（SMS + 邮件） | 记录 `last_state_change_ts` |
| `warning → warning` | 无动作 | 跳过（同状态不重复触发） |
| `alert → alert` | 无动作 | 跳过（同状态不重复触发） |
| `任意 → normal` | 清除 `last_state_change_ts` | 心跳重置 |
| SOS 触发 | 无视状态，立即发告警 | 最高优先级 |

### 2.4 剩余时间计算

```python
def get_remaining_seconds(last_heartbeat_ts: int, alert_threshold: int) -> int:
    elapsed = now() - last_heartbeat_ts
    return max(0, alert_threshold - elapsed)
```

无 `countdown` 字段。`last_heartbeat_ts` 是唯一事实源。

## 3. 双轨心跳

### 3.1 物理心跳

- **来源**：微信小程序前台
- **触发**：用户打开小程序，60 秒间隔自动上报
- **内容**：`{ device_id, latitude, longitude, client_ts }`
- **入口**：`POST /heartbeat` → `reset_watchdog("physical", lat, lng)`

### 3.2 情感心跳

- **来源**：用户与 AstrBot 对话
- **触发**：用户发送任意消息
- **内容**：`{ device_id, type: "emotional" }`
- **入口**：AstrBot 回调 `POST /internal/heartbeat` → `reset_watchdog("emotional")`

### 3.3 统一入口

```python
# services/watchdog.py
def reset_watchdog(heartbeat_type: str, latitude: float = None,
                   longitude: float = None, device_id: str = "default"):
    """
    所有心跳的唯一合法写入路径。
    heartbeat_type: "physical" | "emotional"
    """
    ts = now()
    update_heartbeat_log(device_id, heartbeat_type, latitude, longitude, ts)
    update_watchdog_state(last_heartbeat_ts=ts, state="normal")
```

**约束**：禁止任何业务代码绕过此函数直接修改 `watchdog_state` 表。

## 4. 数据库设计

### 4.1 初始化

```python
import sqlite3

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn
```

### 4.2 表结构

```sql
-- 心跳日志（永久保留）
CREATE TABLE IF NOT EXISTS heartbeat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    client_ts INTEGER NOT NULL,
    server_ts INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT 'physical'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_heartbeat_dedup
    ON heartbeat_log(device_id, client_ts);
CREATE INDEX IF NOT EXISTS idx_heartbeat_server_ts
    ON heartbeat_log(server_ts);

-- 看门狗状态（单行）
CREATE TABLE IF NOT EXISTS watchdog_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL DEFAULT 'normal',
    last_heartbeat_ts INTEGER,
    last_state_change_ts INTEGER
);

-- 看门狗配置
CREATE TABLE IF NOT EXISTS watchdog_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR IGNORE INTO watchdog_config (key, value) VALUES
    ('warning_threshold', '2700'),
    ('alert_threshold', '3600');

-- 紧急联系人
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    name TEXT,
    created_at INTEGER NOT NULL
);

-- 告警队列
CREATE TABLE IF NOT EXISTS alert_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    channel TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
```

### 4.3 heartbeat_log 去重策略

```sql
INSERT OR IGNORE INTO heartbeat_log
    (device_id, latitude, longitude, client_ts, server_ts, type)
VALUES (?, ?, ?, ?, ?, ?);
```

`UNIQUE(device_id, client_ts)` 保证同一条心跳不会重复写入。离线缓存批量补发时天然幂等。

## 5. 看门狗守护进程

### 5.1 生命周期

```python
# daemon/watchdog_daemon.py

async def watchdog_loop():
    """FastAPI lifespan 启动的后台任务，30 秒轮询。"""
    while True:
        await asyncio.sleep(30)
        state = get_watchdog_state()
        config = get_watchdog_config()
        remaining = get_remaining_seconds(
            state["last_heartbeat_ts"],
            config["alert_threshold"]
        )

        if remaining <= 0 and state["state"] != "alert":
            # normal/warning → alert
            transition_to("alert")
            await send_alert()

        elif remaining <= config["alert_threshold"] - config["warning_threshold"] \
                and state["state"] == "normal":
            # normal → warning
            transition_to("warning")
            await send_direct_warning()

        # warning → warning 或 alert → alert：跳过，不重复触发
```

### 5.2 启动恢复

```python
# main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：从 SQLite 恢复状态，启动 daemon
    init_db(DB_PATH)
    task = asyncio.create_task(watchdog_loop())
    yield
    # 关闭：优雅停止
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Echo API", lifespan=lifespan)
```

启动时从 SQLite 读取 `watchdog_state`，自动恢复到正确状态。不需要额外恢复逻辑——daemon 的下一次 30 秒轮询会基于数据库中的真实状态做出正确判断。

## 6. 告警链路

### 6.1 预警（warning 阶段）

```
FastAPI → send_direct_warning()
  → 调用微信订阅消息 / Server酱 / SMS
  → 纯文本："检测到您已 45 分钟未更新状态，请问是否安全？"
  → 不经过 AstrBot
```

### 6.2 告警（alert 阶段）

```
FastAPI → send_alert()
  → 提取 SQLite 中最后一条 physical heartbeat 的坐标
  → 拼接告警短信模板
  → 发送 SMS（5 秒超时，指数退避，最多 3 次）
    → 成功 → 结束
    → 失败 → 写入 alert_queue
      → 后台每 30 秒重试，最多 5 次
      → 5 次全失败 → 尝试备用通道（邮件/Webhook）
  → 进程重启后自动从 alert_queue 捞起未发送告警
```

### 6.3 告警短信模板

```
【Echo 防失联告警】

{username} 已超过 {threshold} 分钟未响应，可能处于失联状态。

最后已知位置：{latitude}, {longitude}
最后活跃时间：{timestamp}
高德地图查看：https://uri.amap.com/marker?position={longitude},{latitude}

请立即尝试联系此人，必要时报警。
```

### 6.4 SOS 紧急阻断

```
小程序长按 SOS 3 秒 → POST /sos
  → 无视当前看门狗状态
  → 立刻抓取当前最新坐标
  → 直接调用 send_alert() 发送给紧急联系人
  → 最高优先级，不经过状态机
```

## 7. 接口清单

| 方法 | 路径 | 说明 | 来源 |
|------|------|------|------|
| POST | /heartbeat | 接收心跳（支持 JSON 数组批量） | 小程序 |
| GET | /status | 查询当前守护状态 | 小程序 |
| POST | /config | 更新看门狗阈值配置 | 小程序 |
| POST | /contacts | 添加紧急联系人 | 小程序 |
| GET | /contacts | 查询紧急联系人 | 小程序 |
| DELETE | /contacts/{id} | 删除紧急联系人 | 小程序 |
| POST | /sos | SOS 紧急触发 | 小程序 |
| POST | /internal/heartbeat | 情感心跳（AstrBot 回调） | AstrBot |

## 8. 离线缓存策略

### 小程序端

```javascript
// 心跳写入本地缓存
function cacheHeartbeat(data) {
  const cached = wx.getStorageSync('pending_heartbeats') || [];
  cached.push(data);
  wx.setStorageSync('pending_heartbeats', cached);
}

// 网络恢复后批量上传
async function flushHeartbeats() {
  const cached = wx.getStorageSync('pending_heartbeats') || [];
  if (cached.length === 0) return;
  await wx.request({ url: '/heartbeat', method: 'POST', data: cached });
  wx.setStorageSync('pending_heartbeats', []);
}
```

### 服务端

```python
# POST /heartbeat 接收 JSON 数组
# 逐条 INSERT OR IGNORE，基于 (device_id, client_ts) 去重
```

## 9. 紧急联系人管理

### 流程

```
用户首次开启守护
  → 检查 contacts 表是否为空
  → 为空 → 强制跳转设置页
  → 输入手机号 → 保存
  → 服务端自动发测试短信："【Echo】您已被设为 xxx 的紧急联系人"
  → 页面回显号码 + 发送状态（✓ 已送达 / ✗ 发送失败）
  → 验证通过 → 允许开启守护
```

### 短信验证

- 保存时自动发送测试短信
- 不需要用户输入验证码
- 发送失败不阻塞保存，但显示警告

## 10. AstrBot 集成

### 角色

- 情感心跳来源（用户发消息 → 回调 FastAPI）
- 情绪陪伴（对话交互）
- **不负责预警下发**（预警由 FastAPI 直推）

### 回调流程

```
用户发消息给 AstrBot
  → AstrBot 处理消息
  → AstrBot 回调 POST /internal/heartbeat
  → reset_watchdog("emotional")
  → watchdog_state 回退到 normal
```

### 模型

- MiMo-V2.5（直接接入，跳过旧版，规避 6/30 停服风险）
- System Prompt：递进式关怀话术，引导自然交互
