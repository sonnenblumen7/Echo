# AGENTS.md

> 所有参与 Echo 项目的 AI Agent（Claude、Codex、Gemini、GPT 等）必须遵守以下约束。

---

## 第一原则

```
AI 允许失败。告警不允许失败。
```

任何涉及告警链路的代码，以鲁棒性为第一优先级。其余模块可以简陋，告警不行。

---

## 行为约束

### 1. 禁止擅自增加复杂功能

- 不要引入用户未要求的功能
- 不要添加"顺便做一下"的优化
- 不要扩展需求范围（scope creep）
- 如果发现值得做的改进，**先提出来，等确认后再做**

### 2. 禁止提前优化

- 不要引入缓存层（除非有明确的性能瓶颈）
- 不要引入消息队列（Redis / RabbitMQ 等）
- 不要引入微服务拆分
- 不要优化数据库查询（除非有实际慢查询）
- SQLite + 单进程足够支撑本项目的所有场景

### 3. 禁止引入额外基础设施

- 不引入 Redis、Memcached、RabbitMQ、Kafka
- 不引入 Docker、Kubernetes（除非用户明确要求）
- 不引入 ORM（SQLAlchemy 等），直接用 sqlite3
- 不引入 Alembic 等迁移工具，手动建表
- 不引入 Prometheus、Grafana 等监控

当前基础设施：**FastAPI + SQLite + 微信小程序 + GCP**。没有更多了。

### 4. MVP 优先

- 实现最简单的能工作的方案
- 代码不需要优雅，但必须正确
- 如果两个方案都能工作，选更简单的那个
- 如果不确定，选更简单的那个

---

## 架构约束

### 5. 看门狗状态机不可修改

状态机已定稿（v4），除非用户明确要求变更：

```
normal → warning → alert
```

- `warning_threshold` 默认 2700 秒
- `alert_threshold` 默认 3600 秒
- 所有阈值 operator_configurable
- 无 `countdown` 字段，剩余时间实时计算
- 防重发：`last_state_change_ts`，同状态不重复触发

### 6. 所有心跳必须经过 reset_watchdog()

```python
# services/watchdog.py
def reset_watchdog(heartbeat_type: str, latitude=None, longitude=None,
                   device_id="default"):
    ...
```

- `POST /heartbeat` → `reset_watchdog("physical", lat, lng)`
- `POST /internal/heartbeat` → `reset_watchdog("emotional")`
- 未来任何新渠道 → `reset_watchdog(...)`
- **禁止**直接调用 `UPDATE watchdog_state SET ...`

### 7. watchdog_state 只能通过 service 层修改

```
routers/*.py    ──→  services/watchdog.py  ──→  watchdog_state 表
daemon/*.py     ──→  services/watchdog.py  ──→  watchdog_state 表
任何代码        ──→  services/watchdog.py  ──→  watchdog_state 表
```

禁止任何代码直接 `import sqlite3` 去修改 `watchdog_state`。唯一的合法路径是 `services/watchdog.py` 中的函数。

### 8. 告警链路不可降级

告警发送必须包含：

- SMS 主通道（5 秒超时，指数退避，最多 3 次）
- 失败写入 SQLite `alert_queue`（后台每 30 秒重试，最多 5 次）
- 全失败 → 备用通道（邮件/Webhook）
- 进程重启后自动从 `alert_queue` 捞起未发送告警

**禁止**：单次调用失败就放弃、跳过重试队列、去掉备用通道。

### 9. 预警消息由 FastAPI 直推

- 预警（warning 阶段）由 FastAPI 直接调用通知 API
- **禁止**将预警消息路由到 AstrBot 发送
- AstrBot 个人微信 Hook 不可靠，不可用于保命链路

### 10. SQLite 必须使用 WAL 模式

```python
conn.execute("PRAGMA journal_mode=WAL;")
```

在所有数据库连接初始化时强制执行。不使用 WAL 模式会导致并发写入锁表。

---

## 代码风格

### 11. 防御性编程

所有外部调用必须有 `try-except` + 超时：

```python
try:
    result = await asyncio.wait_for(external_call(), timeout=5.0)
except asyncio.TimeoutError:
    log.warning("外部调用超时")
    fallback_action()
except Exception as e:
    log.error(f"外部调用异常: {e}")
    fallback_action()
```

适用范围：SMS 发送、邮件发送、AstrBot 调用、微信 API 调用。

### 12. 日志

- 使用 Python 标准 `logging` 模块
- 告警相关操作必须记录 INFO 级别
- 异常必须记录 ERROR 级别
- 不引入 structlog 等第三方日志库

---

## 协作规范

### 13. 修改前先确认

以下操作必须先提出，等用户确认后再执行：

- 修改数据库表结构
- 修改状态机逻辑
- 修改告警链路
- 引入新的依赖包
- 修改接口签名

### 14. 文档同步

如果代码变更涉及架构调整，必须同步更新：

- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`

### 15. 优先级红线

当时间冲突或需要做取舍时：

```
P0（Watchdog / Heartbeat / Alert）> P1（小程序 / 联系人）> P2（AstrBot / AI）
```

无条件砍低优先级功能，保住高优先级。
