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

---

## 2026-06-06（Phase 2 Day 1 — 小程序骨架 + 真机心跳）

### 小程序初始化

**新建文件：**
- `miniprogram/app.json` — 页面注册 + requiredPrivateInfos: ["getLocation"] + permission.scope.userLocation
- `miniprogram/app.js` — App 入口，onLaunch 打日志
- `miniprogram/app.wxss` — 全局样式（空）
- `miniprogram/project.config.json` — 微信开发者工具项目配置（含 appid: wx54d417ad7c0f6f6e）
- `miniprogram/pages/index/index.wxml` — 页面结构
- `miniprogram/pages/index/index.js` — 页面逻辑
- `miniprogram/pages/index/index.json` — 页面配置
- `miniprogram/pages/index/index.wxss` — 页面样式

**踩坑记录：**
1. app.json 的 permission 格式错误：最初写成 `{"desc": "..."}`，正确格式是 `{"scope.userLocation": {"desc": "..."}}`，导致真机定位静默失败
2. 微信开发者工具需要「清缓存 → 全部清除 → 编译」才能加载新代码，直接点编译可能跑旧缓存
3. checkPrivacy / recoverTuoguanOptimizeAd 是微信框架内部噪音，不影响功能
4. bindlongtap 在微信中约 350ms 就触发，不是 3 秒——SOS 进度条改用 touchstart + setTimeout 3 秒手动计时

### 真机心跳验证

- 真机扫码后点击「开启守护」→ 弹出定位授权 → 获取成功（纬度 22.59589）
- POST /heartbeat → 后端返回 `{status: "ok", received: 1}`
- 后端终端打印：`heartbeat: 1 条, lat=22.59589, lng=113.97412`

### 60 秒自动心跳

- setInterval 60 秒 → wx.getLocation → push 到队列 → POST /heartbeat
- 每 60 秒控制台输出：`tick: 位置获取成功，队列 1 条` → `flushQueue 成功: 1 条已送达`
- 倒计时 60→0 每秒递减，归零后下一个 tick 重置

### 离线缓存 + 批量补发

**测试方法**：停掉后端服务（模拟信号盲区），等心跳积压，再重启后端。

**测试结果**：
- 断网期间：每 60 秒 `flushQueue 失败: 网络异常，心跳保留在本地队列 (N 条)`
- 队列正确累积：1→2→3→...→12 条
- 恢复网络后：`flushQueue 成功: 12 条已送达` → `队列已清空`
- 恢复正常单条发送

**Gemini 的飞行模式测试方案不可行**：开飞行模式时小程序被系统挂起，setInterval 停止运行。停后端服务是更好的模拟方式。

### UI 重设计

**页面结构**：
- 状态卡片：守护状态（绿/灰）、最后心跳时间、下次心跳倒计时
- 开启/结束守护按钮（渐变色，toggle 切换）
- 手动确认心跳按钮（绿色描边，守护中显示，点击立即发心跳+重置倒计时）
- SOS 红色圆润按钮（长按 3 秒进度条动画）

**样式**：圆角卡片(24rpx)、渐变按钮、阴影、禁用页面滚动，适配微信审核要求

### SOS 进度条实现

**初版问题**：使用 bindlongtap，但微信的 longtap 约 350ms 就触发，和 3 秒动画不同步。

**修正方案**：去掉 bindlongtap，改为纯手动计时：
- bindtouchstart → sosPressing=true（CSS 动画开始）+ setTimeout 3 秒
- 3 秒到 → _fireSos() 触发
- bindtouchend/bindtouchcancel → clearTimeout + sosPressing=false（动画归零）

**防抖**：15 秒冷却期，_sosCooldown 时间戳判断，重复触发直接忽略。

### 手动确认心跳

- 用户进信号盲区前主动按一下，多争取 60 秒窗口
- 点击 → 调用 tick() → 立即获取 GPS + 发心跳 + 倒计时重置为 60
- 只在「守护中」状态显示

### 后端日志补全

- routers/heartbeat.py 新增成功日志：`heartbeat: N 条, lat=X, lng=Y, device=Z`
- 之前只有 SOS 有坐标日志，普通心跳没有，导致终端看不到数据

### Git 提交记录

```
f36c6a2 docs: update DAILY_SYNC with Phase 2 progress
2ea3126 feat: mini program UI, SOS progress bar, manual heartbeat, backend logging
0da2205 fix: miniprogram entry files and location permission format
50f1670 feat: phase2 day1 mini program heartbeat prototype
09a7dbb feat: Phase 1 complete — config, contacts, alert queue, SOS, routers split
12d99a7 feat: Phase 1 core — SQLite, watchdog service, heartbeat API, daemon, docs
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

### 已知问题

- 真机测试需手机与电脑同局域网（192.168.1.21:8000），后续需部署 GCP 或用 ngrok
- 开发者工具缓存旧代码问题：清缓存 → 全部清除 → 编译
- uvicorn 终端偶尔不显示请求日志（可能是 --reload 导致的短暂断连）

### 下一步

1. 设置页——紧急联系人 CRUD（对接 /contacts 接口）
2. 首次开启守护前强制填写联系人
3. 底部 Tab 导航（首页 + 设置）
4. 接入真实 SMS API（替换 mock）
5. Day 6 强制提审
