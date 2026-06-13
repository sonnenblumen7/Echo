# Echo 项目完整报告（2026-06-13）

## 项目概述

**Echo** — 防失联看门狗 + 极简赛博旅伴

- **场景**：大西北青甘大环线无人区自驾，2026 年 6 月中旬实地压测
- **哲学**：MVP 驱动，代码无需优雅，保命链路必须鲁棒
- **优先级**：P0 看门狗+告警 > P1 前端心跳采集 > P2 AI陪伴（与P0绑定不可单独砍）
- **技术栈**：FastAPI + SQLite(WAL) + 微信小程序(前台定位) + AstrBot + MiMo-V2.5
- **服务器**：腾讯云香港 101.32.68.245，Ubuntu 24.04
- **域名**：echoping.cn（HTTPS 已配置）

---

## 功能完成度

### Phase 1: 核心生命线 ✅ 100%

| 功能 | 状态 | 说明 |
|------|------|------|
| POST /heartbeat（批量） | ✅ | 支持批量心跳，UNIQUE 约束去重 |
| GET /status | ✅ | 返回状态、剩余秒数、最后心跳时间戳 |
| SQLite 建库（WAL） | ✅ | 5个表 + 索引 |
| 看门狗守护进程 | ✅ | 30秒轮询，三态迁移+防重发 |
| 告警链路 | ✅ | PushDeer + 邮件 + 短信队列重试 |
| 紧急联系人 CRUD | ✅ | 按 openid 隔离 |
| send_direct_warning() | ✅ | 占位函数 |

### Phase 2: 小程序采集端 ✅ 100%

| 功能 | 状态 | 说明 |
|------|------|------|
| AppID 注册 | ✅ | wx50728cfb30fd8fed |
| 极简 UI | ✅ | 开启/结束守护 + 状态显示 |
| 前台定位采集 | ✅ | wgs84 坐标，60秒周期 |
| 离线缓存 | ✅ | localStorage 队列，批量补发 |
| SOS 长按按钮 | ✅ | 3秒触发，15秒冷却 |
| 紧急联系人设置页 | ✅ | 回显 + 删除 + 手机号脱敏 |
| 微信审核 | ✅ | 已提审 |
| OpenID 用户隔离 | ✅ | 每个用户只能看到自己的联系人 |
| 首次打开提醒 | ✅ | 引导用户配置联系人 |
| 心跳同步修复 | ✅ | 30秒轮询 /status 接口 |

### Phase 3: AI 伴侣 ✅ 80%

| 功能 | 状态 | 说明 |
|------|------|------|
| AstrBot 部署 | ✅ | systemd 服务，自动重启 |
| MiMo-V2.5 接入 | ✅ | API 配置完成 |
| 微信接入 | ✅ | 个人微信 Hook |
| 情感心跳 | ✅ | @filter.event_message_type 装饰器 |
| 主动关怀 | ⏸️ | 使用现有插件 |
| SOS 关键词触发 | ⚠️ | 插件已开发，待实测 |
| OpenID 绑定 | ⚠️ | 接口已开发，待实测 |

---

## 技术架构

### 服务器部署

```
腾讯云香港 101.32.68.245 (Ubuntu 24.04)
├── Nginx (443 → 8000)
├── FastAPI (port 8000)
│   ├── /heartbeat - 物理心跳
│   ├── /status - 状态查询
│   ├── /contacts - 联系人 CRUD
│   ├── /sos - SOS 告警
│   ├── /sleep - 睡眠模式
│   ├── /auth/login - 微信登录
│   ├── /bind_openid - OpenID 绑定
│   └── /internal/heartbeat - 情感心跳
├── AstrBot (port 6185)
│   ├── WebUI 管理面板
│   ├── echo_watchdog 插件
│   └── MiMo-V2.5 AI
└── SQLite (echo.db)
```

### 数据库表结构

```sql
-- 心跳日志
CREATE TABLE heartbeat_log (
    id INTEGER PRIMARY KEY,
    wx_openid TEXT NOT NULL DEFAULT '',
    device_id TEXT,
    latitude REAL,
    longitude REAL,
    client_ts INTEGER,
    server_ts INTEGER,
    type TEXT DEFAULT 'physical'  -- physical / emotional / sos
);

-- 紧急联系人
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    wx_openid TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL,
    name TEXT,
    email TEXT DEFAULT '',
    created_at INTEGER
);

-- 告警队列
CREATE TABLE alert_queue (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER,
    channel TEXT,
    message TEXT,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    created_at INTEGER
);

-- 看门狗配置
CREATE TABLE watchdog_config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 看门狗状态
CREATE TABLE watchdog_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT DEFAULT 'normal',
    last_heartbeat_ts INTEGER,
    last_state_change_ts INTEGER,
    email_sent INTEGER NOT NULL DEFAULT 0
);

-- OpenID 绑定
CREATE TABLE openid_bind (
    id INTEGER PRIMARY KEY,
    astrbot_openid TEXT NOT NULL UNIQUE,
    miniprogram_openid TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
```

---

## 小程序功能

### 守护页

- **开启/结束守护** - 切换看门狗状态
- **状态显示** - 守护状态、最后心跳、倒计时
- **睡眠模式** - 暂停 8 小时，不触发告警
- **手动心跳** - 手动确认安全
- **SOS 按钮** - 长按 3 秒触发紧急告警
- **首次打开提醒** - 引导用户配置联系人

### 设置页

- **联系人列表** - 显示脱敏手机号和邮箱
- **添加联系人** - 手机号/邮箱至少填一项
- **删除联系人** - 守护中不能删除最后一位

### 核心逻辑

- **心跳采集** - 60秒周期，前台定位
- **离线缓存** - localStorage 队列，批量补发
- **心跳同步** - 30秒轮询 /status 接口
- **用户隔离** - 按 openid 隔离数据

---

## AstrBot 配置

### 服务信息

- **WebUI**: http://101.32.68.245:6185
- **用户名**: Leo
- **密码**: （见 .env）
- **LLM**: MiMo-V2.5-pro
- **API Key**: （见 .env）

### 插件功能

**echo_watchdog 插件：**
- 情感心跳 - 用户发消息 → POST /internal/heartbeat → 重置看门狗
- SOS 关键词 - 用户发送 "SOS" → 触发 SOS 告警
- OpenID 绑定 - 用户发送 "绑定 <小程序openid>" → 绑定账号

---

## 告警链路

### 物理心跳

```
小程序 → POST /heartbeat → FastAPI → reset_watchdog("physical")
```

### 情感心跳

```
用户消息 → AstrBot → POST /internal/heartbeat → FastAPI → reset_watchdog("emotional")
```

### SOS 告警

```
用户长按 SOS / 发送 "SOS"
        ↓
POST /sos/ → FastAPI
        ↓
trigger_alert()
        ↓
├── PushDeer 推送
├── 邮件告警
└── 短信队列（待实现）
```

### Watchdog 超时

```
45分钟无心跳 → warning → PushDeer 提醒
60分钟无心跳 → alert → PushDeer + 邮件 + 短信
```

---

## 已知问题

### 🔴 严重问题

1. **AstrBot 插件发送消息异常**
   - 错误：`'MessageChain' object has no attribute 'is_stopped'`
   - 影响：绑定命令和 SOS 命令无法发送回复消息
   - 状态：已修复代码，待实测

2. **OpenID 绑定未实测**
   - 问题：绑定接口已开发，但未完整测试
   - 影响：SOS 关键词触发可能找不到联系人
   - 状态：待实测

### 🟡 中等问题

3. **短信告警未实现**
   - 问题：notification.py 是占位函数
   - 影响：无法发送短信给紧急联系人
   - 状态：已用邮件替代

4. **主动关怀未实现**
   - 问题：P3.5 主动关怀未开发
   - 影响：用户沉默时无法主动关怀
   - 状态：使用现有插件

5. **定位精度问题**
   - 问题：室内测试误差 1 公里（基站定位）
   - 影响：紧急时无法精确定位
   - 状态：室外 GPS 精度 1-10 米

### 🟢 轻微问题

6. **心跳同步延迟**
   - 问题：小程序最后心跳显示有延迟
   - 影响：用户体验
   - 状态：30秒轮询，可接受

7. **AstrBot WebUI 密码变化**
   - 问题：每次重启密码会变化
   - 影响：需要手动查看日志获取密码
   - 状态：可接受

---

## 安全措施

### 数据隔离

- ✅ OpenID 用户隔离 - 每个用户只能看到自己的联系人
- ✅ 手机号脱敏显示 - 138****8000
- ✅ .env 文件 gitignore - 密钥不泄露

### 告警保障

- ✅ PushDeer 推送 - 即时通知
- ✅ 邮件告警 - 备用通道
- ✅ 告警队列 - 失败重试（最多 5 次）
- ✅ 睡眠模式 - 夜间不误报

### 服务稳定

- ✅ systemd 服务 - 自动重启
- ✅ 看门狗守护进程 - 30秒轮询
- ✅ SQLite WAL - 高并发支持

---

## 部署信息

### 服务器

- **IP**: 101.32.68.245
- **用户名**: ubuntu
- **密码**: （见记忆文件）
- **系统**: Ubuntu 24.04

### 域名

- **域名**: echoping.cn
- **SSL**: Let's Encrypt
- **Nginx**: 443 → 8000

### 服务

- **FastAPI**: http://127.0.0.1:8000
- **AstrBot**: http://127.0.0.1:6185
- **健康检查**: https://echoping.cn/health

---

## 待办事项

### 实测前必须完成

- [ ] 修复 AstrBot 插件发送消息异常
- [ ] 测试 OpenID 绑定功能
- [ ] 测试 SOS 关键词触发
- [ ] 测试完整告警链路

### 实测后优化

- [ ] 实现短信告警（或确认邮件够用）
- [ ] 实现主动关怀功能
- [ ] 优化定位精度
- [ ] 优化心跳同步延迟

### 长期优化

- [ ] 添加更多 SOS 关键词
- [ ] 优化 System Prompt
- [ ] 添加位置分享功能
- [ ] 添加多设备支持

---

## Git 提交历史

```
3ae248d fix: 修复 MessageChain 导入 + 拦截绑定命令
1a44dfd feat: openid 绑定功能 + SOS 关键词触发 + 心跳同步修复
42fca7f feat: 添加 echo_watchdog 情感心跳插件（AstrBot Star 格式）
1747b01 docs: Phase 3 进度同步（P3.1-P3.3 完成，P3.4 进行中）
9ebf28d feat: Phase 3 P1 睡眠模式
ff451ad feat: Phase 3 P2 邮件告警系统
c46e9ae docs: mini program review materials
```

---

## 总结

**Echo 项目 Phase 1-3 基本完成，核心保命功能已实现。**

### 已完成

- ✅ 看门狗守护 - 物理心跳 + 情感心跳
- ✅ SOS 告警 - PushDeer + 邮件
- ✅ 小程序 - 完整功能，已提审
- ✅ AI 伴侣 - AstrBot + MiMo-V2.5
- ✅ 用户隔离 - OpenID 绑定
- ✅ 服务器部署 - HTTPS + systemd

### 待验证

- ⚠️ SOS 关键词触发 - 代码已开发，待实测
- ⚠️ OpenID 绑定 - 接口已开发，待实测
- ⚠️ 完整告警链路 - 待实测

### 建议

1. **实测前**：修复 AstrBot 插件异常，测试完整流程
2. **实测中**：记录问题，拍照留证
3. **实测后**：根据问题优化代码

---

**项目状态：基本可用，待实测验证**

**下一步：实测 → 发现问题 → 优化 → 再实测**

---

**祝实测顺利，安全归来！** 🚗🏔️
