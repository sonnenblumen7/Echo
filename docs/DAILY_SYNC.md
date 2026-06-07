# DAILY_SYNC.md

> Claude 每日上下文同步文件。新会话启动时阅读此文件可快速恢复项目状态。

---

## 项目：Echo

防失联看门狗 + 极简赛博旅伴。青甘大环线无人区单人自驾，2026 年 6 月中旬压测。

**第一原则**：AI 允许失败。告警不允许失败。

---

## 当前进度：Phase 2 进行中

### Phase 1 已完成（43/43 测试通过）

后端全部就绪：SQLite + watchdog service + daemon + /heartbeat + /status + /config + /contacts + /sos + alert queue + routers 拆分。

### Phase 2 已完成

| 功能 | 状态 |
|------|------|
| wx.getLocation → POST /heartbeat（真机通过） | ✅ |
| 60 秒自动心跳 + 倒计时显示 | ✅ |
| 离线缓存 + 批量补发（12 条积压验证通过） | ✅ |
| UI 重设计（圆角卡片、渐变按钮、状态栏） | ✅ |
| SOS 长按 3 秒进度条 + 15 秒冷却 | ✅ |
| 手动确认心跳按钮 | ✅ |
| 后端 heartbeat 日志输出坐标 | ✅ |

### Phase 2 待开发

1. 设置页——紧急联系人 CRUD（对接 /contacts 接口）
2. 首次开启守护前强制填写联系人
3. 底部 Tab 导航（首页 + 设置）
4. 接入真实 SMS API（替换 mock）
5. Day 6 强制提审

### 已知问题

- 开发者工具偶尔缓存旧代码，需手动清缓存重新编译
- 真机测试需手机与电脑同局域网（后续部署 GCP 或用 ngrok）
- checkPrivacy 警告是微信框架噪音，不影响功能

---

## 技术栈

FastAPI + SQLite (WAL) + 微信小程序 + AstrBot + MiMo-V2.5 + GCP

## Git 状态

```
2ea3126 feat: mini program UI, SOS progress bar, manual heartbeat, backend logging
0da2205 fix: miniprogram entry files and location permission format
50f1670 feat: phase2 day1 mini program heartbeat prototype
09a7dbb feat: Phase 1 complete — config, contacts, alert queue, SOS, routers split
12d99a7 feat: Phase 1 core — SQLite, watchdog service, heartbeat API, daemon, docs
f64b2c3 docs: add PROJECT, ROADMAP, ARCHITECTURE, and AGENTS constraints
82234c8 init: FastAPI health check endpoint
```

工作区干净。

---

## 下次会话第一件事

阅读此文件 → git status → 继续 Phase 2 设置页开发。
