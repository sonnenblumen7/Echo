# Echo

防失联看门狗 + 极简赛博旅伴

## 快速启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install fastapi uvicorn requests
```

## 环境变量

复制 `.env.example` 为 `.env`，填入真实配置：

```bash
cp .env.example .env
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `PUSHDEER_KEY` | 否 | PushDeer 推送 Key，用于保底通知通道。未配置时该通道静默跳过 |

### PushDeer（保底通知通道）

PushDeer 是 Echo 的第三层告警通道（SMS → alert_queue → PushDeer）。

1. 注册 [PushDeer](https://www.pushdeer.com)
2. 获取 Key
3. 写入 `.env` 文件

未配置 PushDeer 不影响核心功能，SMS 和 alert_queue 正常工作。

## 启动后端

```bash
cd backend
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 小程序开发

用微信开发者工具导入 `miniprogram/` 目录。

## 架构文档

- [docs/PROJECT.md](docs/PROJECT.md) — 项目定位
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 架构设计
- [docs/ROADMAP.md](docs/ROADMAP.md) — Sprint 排期
- [AGENTS.md](AGENTS.md) — AI Agent 行为约束
