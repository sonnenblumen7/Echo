# PROJECT_STRUCTURE.md

> Echo 项目当前目录结构（2026-06-04 更新）

```
Echo/
├── .gitignore                          # Git 忽略规则
├── AGENTS.md                           # AI Agent 行为约束（15 条）
│
├── backend/
│   ├── config.py                       # 全局配置（DB 路径、默认阈值）
│   ├── main.py                         # FastAPI 入口 + lifespan + 路由
│   ├── echo.db                         # SQLite 数据库（运行时生成，已 gitignore）
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py                 # SQLite 初始化（WAL、5 表、2 索引）
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── watchdog.py                 # 看门狗 service 层（唯一合法写入 watchdog_state）
│   │
│   ├── daemon/
│   │   ├── __init__.py
│   │   └── watchdog_daemon.py          # 看门狗守护进程（30s 轮询）
│   │
│   ├── routers/                        # [待建] 路由模块拆分
│   │
│   └── .venv/                          # Python 虚拟环境（已 gitignore）
│
├── docs/
│   ├── PROJECT.md                      # 项目定位与技术栈
│   ├── ROADMAP.md                      # 10 天 Sprint 排期
│   ├── ARCHITECTURE.md                 # 最终架构设计
│   ├── DEVLOG.md                       # 开发日志
│   ├── DAILY_SYNC.md                   # Claude 每日上下文同步
│   └── PROJECT_STRUCTURE.md            # 本文件
│
└── .vs/                                # VS Code 工作区（已 gitignore）
```

---

## 模块职责边界

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│  路由层      │────→│  service 层       │────→│  SQLite         │
│  main.py     │     │  watchdog.py     │     │  echo.db        │
│  (routers/)  │     │  alert.py [待建]  │     │  (WAL 模式)     │
└─────────────┘     │  notification.py │     └────────────────┘
                    │  [待建]           │
                    └──────────────────┘
                           ↑
                    ┌──────────────────┐
                    │  daemon 层        │
                    │  watchdog_daemon  │
                    └──────────────────┘
```

### 调用规则

- 路由层 → service 层 → SQLite（单向依赖）
- daemon 层 → service 层 → SQLite（单向依赖）
- 禁止路由层直接修改 watchdog_state
- 禁止 daemon 层直接修改 watchdog_state
- watchdog_state 的唯一合法写入路径：services/watchdog.py

### 文件状态

| 文件 | 行数 | 职责 |
|------|------|------|
| config.py | 9 | 数据库路径 + 默认阈值常量 |
| models/database.py | 107 | 连接工厂 + 建表 + 建索引 + 初始化 |
| services/watchdog.py | 86 | watchdog_state 读写 + 配置读取 + 状态迁移 |
| daemon/watchdog_daemon.py | 43 | 30 秒轮询 + 状态迁移判断 |
| main.py | 95 | FastAPI 入口 + lifespan + /health + /status + /heartbeat |
