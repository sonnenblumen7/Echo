# PHASE1_REVIEW.md

> Phase 1 代码审查报告（2026-06-05）
> 审查范围：backend/ + docs/ + AGENTS.md
> 审查类型：只读，不修改代码

---

## 1. 当前架构图

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py (161 行)                      │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐ │
│  │ /health  │ │ /status  │ │ /heartbeat│ │ /config        │ │
│  └──────────┘ └──────────┘ │ (批量+去重)│ │ (阈值读写)     │ │
│                            └─────┬─────┘ └───────┬────────┘ │
│  ┌──────────┐ ┌──────────┐      │               │          │
│  │ /contacts│ │ GET/DEL  │      │               │          │
│  │ POST     │ │ contacts │      │               │          │
│  └────┬─────┘ └──────────┘      │               │          │
│       │                         ▼               ▼          │
│       │              ┌─────────────────────────────────┐    │
│       │              │         Service 层               │    │
│       │              │  watchdog.py   config.py         │    │
│       │              │  contacts.py   alert.py          │    │
│       │              │  notification.py                 │    │
│       │              └────────────┬────────────────────┘    │
│       │                           │                         │
│       │                           ▼                         │
│       │              ┌─────────────────────────────────┐    │
│       └─────────────→│  models/database.py             │    │
│                      │  SQLite (WAL) ← 唯一持久化层    │    │
│                      └─────────────────────────────────┘    │
│                                          ▲                  │
│                                          │                  │
│                      ┌───────────────────┴──────────────┐   │
│                      │  daemon/watchdog_daemon.py        │   │
│                      │  30s 轮询 → 状态迁移 → 通知触发   │   │
│                      │  每轮 process_alert_queue()       │   │
│                      └──────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 已完成能力

| 能力 | 文件 | 验证状态 |
|------|------|----------|
| SQLite 初始化（WAL + 5 表 + 2 索引 + 单例） | models/database.py | ✅ 8 项测试 |
| watchdog service（reset/get_state/get_remaining/get_config/transition/get_last_location） | services/watchdog.py | ✅ |
| config service（get_config/update_config） | services/config.py | ✅ 10 项测试 |
| contacts service（add/get/delete + 手机号查重） | services/contacts.py | ✅ 10 项测试 |
| alert service（trigger_alert/process_alert_queue） | services/alert.py | ✅ 8 项测试 |
| notification 占位（send_sms_alert + MOCK_SMS_SUCCESS） | services/notification.py | ✅ |
| POST /heartbeat（批量 + INSERT OR IGNORE 去重 + reset_watchdog） | main.py | ✅ |
| GET /status（state + remaining_seconds + last_heartbeat_ts） | main.py | ✅ |
| POST /config（Pydantic 校验 + 阈值持久化） | main.py | ✅ |
| POST/GET/DELETE /contacts（CRUD + 手机号正则 + 409 防重） | main.py | ✅ |
| watchdog_daemon（30s 轮询 + 状态迁移 + 防重发 + 通知触发） | daemon/watchdog_daemon.py | ✅ 7 项测试 |
| 配置热更新（改阈值后 daemon 下一轮生效） | 跨模块 | ✅ |

---

## 3. AGENTS.md 合规性

| 条款 | 状态 | 说明 |
|------|------|------|
| §5 状态机不可修改 | ✅ | normal → warning → alert，无遗漏迁移 |
| §6 心跳必须经过 reset_watchdog() | ✅ | POST /heartbeat line 119 调用 |
| §7 watchdog_state 只通过 service 层修改 | ✅ | 仅 watchdog.py 的 reset_watchdog() 和 transition_state() 写入 |
| §8 告警链路不可降级 | ⚠️ | 重试队列已实现（5 次），SMS 为 mock，备用通道未接入 |
| §9 预警由 FastAPI 直推 | ✅ | daemon 调 send_direct_warning()，不经过 AstrBot |
| §10 SQLite WAL | ✅ | get_connection() 强制 PRAGMA journal_mode=WAL |
| §11 防御性编程 | ⚠️ | send_sms_alert() 为 mock 无 try-except，接真实 API 时需补 |
| §12 日志用 logging | ✅ | 全部使用标准 logging |

---

## 4. 架构风险

### R1. heartbeat 写入与 watchdog 重置的事务断裂（已知，从 W2 继承）

**位置**：[main.py:98-124](backend/main.py#L98-L124)

heartbeat_log 写入（conn1）→ commit → close → reset_watchdog()（conn2）。

如果 reset_watchdog() 失败，心跳数据已落盘但看门狗未重置。客户端收到 error，但下次心跳会补偿。

**实际风险**：低。单进程 SQLite，reset_watchdog 仅一条 UPDATE，失败概率极低。

### R2. alert_queue 首次发送失败即入队，无单次超时重试

**位置**：[alert.py:23-29](backend/services/alert.py#L23-L29)

trigger_alert() 对每个联系人只调一次 send_sms_alert()。如果 SMS API 瞬时超时，直接入队等待 30 秒后重试。

AGENTS.md §8 要求"5 秒超时，指数退避，最多 3 次"。当前 mock 无此逻辑，接真实 API 时需补。

### R3. 进程多实例风险

无文件锁或端口占用检查。如果误启动两个 FastAPI 实例，两个 daemon 会同时轮询，可能导致重复告警。

**实际风险**：MVP 单机部署，手动启动，概率极低。

### R4. process_alert_queue 读取与更新不在同一事务

**位置**：[alert.py:37-70](backend/services/alert.py#L37-L70)

先 SELECT 全部 pending → 遍历 → 逐条 UPDATE。如果进程在遍历中途崩溃，部分 alert 的 retry_count 已更新，部分未更新。

**实际风险**：低。最多丢失一次重试机会，下一轮会重新处理。

---

## 5. 技术债

### P1（Phase 2 前必须解决）

| 编号 | 描述 | 影响 |
|------|------|------|
| P1-1 | main.py 161 行，Phase 2 新增 SOS + internal_heartbeat 后将超 200 行 | 可维护性 |
| P1-2 | send_sms_alert() 是 mock，部署前必须接入真实 SMS API | 阻塞上线 |
| P1-3 | 无备用通知通道（邮件/Webhook），AGENTS.md §8 要求 | 合规性 |
| P1-4 | send_direct_warning() 是占位，warning 阶段无实际触达能力 | 功能缺失 |

### P2（建议解决）

| 编号 | 描述 | 影响 |
|------|------|------|
| P2-1 | heartbeat 写入与 watchdog 重置不在同一事务 | 数据一致性（风险低） |
| P2-2 | process_alert_queue 读写不在同一事务 | 数据一致性（风险低） |
| P2-3 | alert.py 的 retry_count 语义：首次成功显示 retry_count=1 | 语义不精确 |
| P2-4 | main.py 中 get_contacts 被迫 alias 为 svc_get_contacts | 命名不清晰 |

### P3（以后优化）

| 编号 | 描述 | 影响 |
|------|------|------|
| P3-1 | daemon 每轮调 get_config() 查 DB，配置变更频率极低 | 性能（可忽略） |
| P3-2 | get_remaining() 内部调 get_config()，再查一次 DB | 性能（可忽略） |
| P3-3 | 进程无文件锁，多实例可能重复告警 | 可靠性（MVP 单机无影响） |

---

## 6. main.py 健康度

| 指标 | 值 | 评估 |
|------|------|------|
| 总行数 | 161 | ⚠️ 临界，Phase 2 前需拆分 |
| Pydantic 模型 | 3 个（HeartbeatItem, ConfigRequest, ContactRequest） | 可接受 |
| 路由数量 | 7 个（health, status, heartbeat, config, contacts×3） | 可接受 |
| import 行数 | 10 | 正常 |
| 路由别名 | 1（get_contacts → svc_get_contacts） | ⚠️ 命名冲突 |

**结论**：当前可用，Phase 2 新增 /sos + /internal/heartbeat + Pydantic 模型后将达到 ~220 行，建议拆分为 routers/。

---

## 7. 数据一致性

| 检查项 | 状态 | 说明 |
|------|------|------|
| heartbeat_log 与 watchdog_state 事务 | ⚠️ | 跨连接，非原子（P2-1） |
| daemon 重启恢复 | ✅ | 从 SQLite 读取真实状态，30s 内自动恢复 |
| watchdog_state 单例存活 | ✅ | INSERT OR IGNORE，重启后状态保留 |
| alert_queue 持久化 | ✅ | 进程重启后 pending 记录被捞起继续重试 |
| 配置热更新 | ✅ | 改 DB → daemon 下一轮生效 |
| 心跳去重 | ✅ | UNIQUE(device_id, client_ts) + INSERT OR IGNORE |

---

## 8. 状态机审查

### 迁移路径完整性

| 迁移 | 触发条件 | 实现位置 | 状态 |
|------|----------|----------|------|
| normal → warning | elapsed ≥ warning_threshold | daemon _check_once | ✅ |
| warning → alert | elapsed ≥ alert_threshold | daemon _check_once | ✅ |
| normal → alert | elapsed ≥ alert_threshold（跳过 warning） | daemon _check_once | ✅ 正确行为 |
| warning → normal | 收到心跳 | reset_watchdog() | ✅ |
| alert → normal | 收到心跳 | reset_watchdog() | ✅ |
| warning → warning | daemon 再次检查 | _check_once 跳过 | ✅ 防重发 |
| alert → alert | daemon 再次检查 | _check_once 跳过 | ✅ 防重发 |
| normal → normal | 心跳持续 | reset_watchdog() | ✅ |

### 遗漏检查

- 无遗漏迁移路径
- 无重复触发风险（last_state_change_ts 机制生效）
- 无死锁风险（所有状态均可通过心跳回退到 normal）

---

## 9. 是否批准进入下一阶段

**结论：批准进入 Phase 2。**

理由：
- Phase 1 核心闭环已打通：心跳 → 看门狗 → 预警/告警 → 短信队列 → 重试
- 无 Critical 级别阻塞项
- P1 技术债可在 Phase 2 开发过程中同步处理（主要是 main.py 拆分）
- P1-2/P1-3/P1-4 依赖真实 SMS API 接入，与 Phase 2 小程序开发并行不冲突

### Phase 2 启动前建议

1. 先拆 main.py 为 routers/（1 小时，避免 Phase 2 代码堆积）
2. 将 P1-2/P1-3/P1-4 加入 Phase 2 排期（SMS 接入 + 备用通道）
3. AGENTS.md §8 的"5 秒超时 + 指数退避"在接真实 SMS API 时一并实现
