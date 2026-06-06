# DEVLOG.md

> Echo 开发日志

---

## 2026-06-04（Day 0 — 架构定稿 + Phase 1 启动）

### 架构评审

- 完成三轮架构评审（Claude 排查 → 用户确认 → Gemini 审查）
- 关键决策：放弃小程序后台定位，改用前台定位 + 自然打卡
- 关键决策：预警由 FastAPI 直推，不经过 AstrBot
- 关键决策：删除 watchdog_state.countdown，last_heartbeat_ts 为唯一事实源
- 状态机定稿 v4：normal → warning → alert，防重发靠 last_state_change_ts

### 文档生成

- docs/PROJECT.md — 项目定位与技术栈
- docs/ROADMAP.md — 10 天 Sprint 排期
- docs/ARCHITECTURE.md — 最终架构设计
- AGENTS.md — 15 条 AI Agent 行为约束

### Phase 1 代码实现

**新增文件：**
- `backend/config.py` — 数据库路径、默认阈值常量
- `backend/models/__init__.py` — 空文件，包标识
- `backend/models/database.py` — SQLite 初始化（WAL + foreign_keys + 5 表 + 2 索引）
- `backend/services/__init__.py` — 空文件，包标识
- `backend/services/watchdog.py` — reset_watchdog() / get_watchdog_state() / get_remaining() / get_config() / transition_state()
- `backend/daemon/__init__.py` — 空文件，包标识
- `backend/daemon/watchdog_daemon.py` — 30 秒轮询 + 状态迁移 + 防重发
- `backend/main.py` — FastAPI 入口 + lifespan + POST /heartbeat + GET /status

**修改文件：**
- `.gitignore` — 新增 *.db / *.db-wal / *.db-shm
- `AGENTS.md` — §6 签名同步实际代码

### 代码审查

- 执行只读架构审查，发现 1 Critical + 4 Warning + 3 Info
- C1 已修复：reset_watchdog() 异常向上传播，main.py 捕获后返回 error
- W1 已修复：AGENTS.md §6 签名同步
- W2/W3/W4 记录为技术债，Phase 1 后期统一处理

### Git 提交记录

```
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

### 验证结果

- ✅ import 不触发 init_db
- ✅ WAL 模式、foreign_keys、5 表、2 索引
- ✅ watchdog_state 单例初始化
- ✅ POST 单条/批量心跳 + INSERT OR IGNORE 去重
- ✅ watchdog_state 自动更新 + get_remaining() 实时计算
- ✅ daemon 状态迁移：normal → warning → alert
- ✅ 防重发：同状态 last_state_change_ts 不变
- ✅ 心跳回退：alert → normal
- ✅ C1 修复验证：reset_watchdog 失败 → 客户端收到 error

### 下一步

- POST /config（看门狗阈值配置读写）
- POST /contacts（紧急联系人 CRUD）
- services/alert.py + services/notification.py
- POST /sos

---

## 2026-06-05（Day 1 — Phase 1 完成）

### 代码实现

**新增文件：**
- `backend/services/config.py` — get_config() / update_config()
- `backend/services/contacts.py` — add_contact() / get_contacts() / delete_contact()
- `backend/services/alert.py` — trigger_alert(source) / process_alert_queue()
- `backend/services/notification.py` — send_sms_alert(MOCK_SMS_SUCCESS) / send_direct_warning() / send_test_sms()
- `backend/routers/__init__.py` — 空文件
- `backend/routers/heartbeat.py` — POST /heartbeat
- `backend/routers/status.py` — GET /status
- `backend/routers/config.py` — POST /config
- `backend/routers/contacts.py` — POST/GET/DELETE /contacts
- `backend/routers/sos.py` — POST /sos（紧急阻断）

**修改文件：**
- `backend/main.py` — 从 161 行瘦身到 39 行，拆分为 routers/
- `backend/services/watchdog.py` — 新增 get_last_location()，移除 get_config()（迁移到 config.py）
- `backend/daemon/watchdog_daemon.py` — 接入 trigger_alert + process_alert_queue，_on_alert 传 source="WATCHDOG_TIMEOUT"

### Phase 1 Review

- 执行完整架构审查（docs/PHASE1_REVIEW.md）
- AGENTS.md 15 条约束：12 条完全合规，3 条有理由偏差
- 技术债：P1×4, P2×4, P3×3
- 结论：批准进入 Phase 2

### 关键决策

- POST /sos 必须调用 transition_state("alert")，防止状态脑裂
- trigger_alert 新增 source 参数（SOS_BUTTON / WATCHDOG_TIMEOUT），区分消息模板
- main.py 拆分为 routers/（Phase 2 前 P1 技术债已清）

### Git 提交记录

```
12d99a7 feat: Phase 1 core — SQLite, watchdog service, heartbeat API, daemon, docs
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

### 最终测试结果

Phase 1 全回归测试：43 passed, 0 failed

覆盖：基础设施(6) + 心跳(5) + 配置(5) + 联系人(7) + 状态机(5) + 告警链路(6) + SOS(6) + 恢复(3)

### 下一步

- Phase 2：小程序采集端（Day 4-6）
- P1 技术债剩余：SMS 接入、备用通知通道、send_direct_warning 占位替换
