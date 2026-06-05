# DAILY_SYNC.md

> Claude 每日上下文同步文件。新会话启动时阅读此文件可快速恢复项目状态。

---

## 项目：Echo

防失联看门狗 + 极简赛博旅伴。青甘大环线无人区单人自驾，2026 年 6 月中旬压测。

**第一原则**：AI 允许失败。告警不允许失败。

---

## 当前进度：Phase 1 进行中（Day 1-3）

### 已完成

| 模块 | 文件 | 状态 |
|------|------|------|
| SQLite 初始化 | backend/models/database.py | ✅ |
| watchdog service | backend/services/watchdog.py | ✅ |
| POST /heartbeat | backend/main.py | ✅ |
| GET /status | backend/main.py | ✅ |
| watchdog daemon | backend/daemon/watchdog_daemon.py | ✅ |
| 架构审查 + C1 修复 | — | ✅ |
| 文档生成 | docs/*.md + AGENTS.md | ✅ |

### 待开发（按优先级）

1. POST /config — 看门狗阈值配置读写
2. POST /contacts — 紧急联系人 CRUD
3. services/alert.py — 告警发送 + SQLite 重试队列
4. services/notification.py — send_direct_warning() 占位
5. POST /sos — SOS 紧急触发

### 已知技术债

- W2: heartbeat 写入与 watchdog 重置不在同一事务
- W3: main.py 需在路由增多后拆分 routers/
- W4: get_remaining() 与 get_config() 重复查询

---

## 架构关键约束（详见 AGENTS.md + ARCHITECTURE.md）

- watchdog_state 只能通过 services/watchdog.py 修改
- 所有心跳必须经过 reset_watchdog()
- SQLite WAL 模式，heartbeat_log 永久保留
- 预警由 FastAPI 直推，不经过 AstrBot
- 防重发：last_state_change_ts，同状态不重复触发

---

## 技术栈

- FastAPI + SQLite (WAL) + 微信小程序 + AstrBot + MiMo-V2.5 + GCP

## Git 状态

```
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

工作目录有未提交变更（Phase 1 代码），待提交。

---

## 下次会话第一件事

阅读此文件 → 检查 git status → 继续 Phase 1 待开发任务。
