# Echo — PROJECT.md

> 防失联看门狗 + 极简赛博旅伴

## 项目定位

Echo 是一套面向无人区单人自驾场景的防失联系统。核心职责是：**当用户停止一切交互后，自动触发告警，将最后已知坐标发送给紧急联系人。**

附带 AI 伴侣功能，作为自驾途中的情绪陪伴与双重心跳来源。

## 核心原则

```
AI 允许失败。告警不允许失败。
```

## 目标场景

- **路线**：青甘大环线（青海 - 甘肃无人区）
- **时间**：2026 年 6 月中旬实地压测
- **环境**：信号极弱、网络抖动频繁、部分路段完全无信号
- **用户**：单人驾驶

## MVP 优先级

| 级别 | 模块 | 说明 |
|------|------|------|
| **P0** | Watchdog / Heartbeat / Alert | 保命链路，不可妥协，不可降级 |
| **P1** | 小程序定位 / 联系人管理 | 数据来源与告警目标 |
| **P2** | AstrBot / MiMo-V2.5 | AI 伴侣，与 P0 绑定（情感心跳），可简化但不可单独砍掉 |

## 技术栈

| 层 | 选型 |
|----|------|
| Backend | FastAPI + SQLite (WAL) |
| Frontend | 微信小程序 |
| AI | AstrBot + MiMo-V2.5 |
| Server | GCP |
| 通知推送 | FastAPI 直调（Server酱 / SMS / 微信订阅消息） |

## 关键约束

1. 所有心跳必须经过 `reset_watchdog()` 统一入口
2. `watchdog_state` 只能通过 `services/watchdog.py` 修改
3. 预警消息由 FastAPI 直推，不经过 AstrBot
4. 紧急联系人必须在首次开启守护前完成配置并验证
5. SQLite 使用 WAL 模式，`heartbeat_log` 永久保留

## 目录结构

```
Echo/
├── backend/
│   ├── main.py              # FastAPI 入口 + lifespan
│   ├── routers/             # 路由层
│   │   ├── heartbeat.py
│   │   ├── status.py
│   │   ├── contacts.py
│   │   ├── config.py
│   │   └── sos.py
│   ├── services/            # 业务逻辑层
│   │   ├── watchdog.py      # reset_watchdog() 唯一入口
│   │   ├── alert.py         # 告警发送 + 重试队列
│   │   └── notification.py  # 预警直推（Server酱/SMS）
│   ├── models/              # 数据模型
│   │   └── database.py      # SQLite 初始化 + WAL
│   ├── daemon/              # 看门狗守护进程
│   │   └── watchdog_daemon.py
│   └── config.py            # 全局配置
├── miniprogram/             # 微信小程序
├── docs/
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   └── ARCHITECTURE.md
├── AGENTS.md
└── .gitignore
```
