# DAILY_SYNC.md

> Claude 每日上下文同步文件。新会话启动时阅读此文件可快速恢复项目状态。

---

## 项目：Echo

防失联看门狗 + 极简赛博旅伴。青甘大环线无人区单人自驾，2026 年 6 月中旬压测。

**第一原则**：AI 允许失败。告警不允许失败。

---

## 当前进度：Phase 1 完成，Phase 2 待启动

### Phase 1 已完成（43/43 测试通过）

| 模块 | 文件 | 状态 |
|------|------|------|
| SQLite 初始化 | models/database.py | ✅ |
| watchdog service | services/watchdog.py | ✅ |
| config service | services/config.py | ✅ |
| contacts service | services/contacts.py | ✅ |
| alert service | services/alert.py | ✅ |
| notification 占位 | services/notification.py | ✅ |
| POST /heartbeat（批量+去重） | routers/heartbeat.py | ✅ |
| GET /status | routers/status.py | ✅ |
| POST /config | routers/config.py | ✅ |
| POST/GET/DELETE /contacts | routers/contacts.py | ✅ |
| POST /sos（紧急阻断） | routers/sos.py | ✅ |
| watchdog_daemon | daemon/watchdog_daemon.py | ✅ |
| main.py（瘦入口 39 行） | main.py | ✅ |
| Phase 1 Review | docs/PHASE1_REVIEW.md | ✅ |

### Phase 2 待开发（Day 4-6）

1. 微信小程序 AppID 注册
2. 极简 UI（开启/结束守护 + 状态栏）
3. 前台定位采集 + 离线缓存
4. SOS 长按按钮
5. 紧急联系人设置页
6. **Day 6 强制提审**

### P1 技术债（Phase 2 期间同步处理）

- send_sms_alert() 是 mock，需接入真实 SMS API
- send_direct_warning() 是占位，warning 阶段无实际触达
- 无备用通知通道（邮件/Webhook）

---

## 架构关键约束（详见 AGENTS.md + ARCHITECTURE.md）

- watchdog_state 只能通过 services/watchdog.py 修改
- 所有心跳必须经过 reset_watchdog()
- trigger_alert 必须传 source（SOS_BUTTON / WATCHDOG_TIMEOUT）
- POST /sos 必须调用 transition_state("alert")，防状态脑裂
- SQLite WAL 模式，heartbeat_log 永久保留
- 预警由 FastAPI 直推，不经过 AstrBot

---

## 项目结构

```
backend/
├── main.py (39行，瘦入口)
├── config.py
├── models/database.py
├── routers/ (heartbeat, status, config, contacts, sos)
├── services/ (watchdog, config, contacts, alert, notification)
├── daemon/watchdog_daemon.py
```

## 技术栈

FastAPI + SQLite (WAL) + 微信小程序 + AstrBot + MiMo-V2.5 + GCP

## Git 状态

```
(待提交) Phase 1 全部完成
12d99a7 feat: Phase 1 core
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

---

## 下次会话第一件事

阅读此文件 → git status → 开始 Phase 2 小程序开发。
