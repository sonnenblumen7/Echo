# DEPLOYMENT_CHECKLIST.md

> Echo 云部署清单（Day 3 使用）

## 服务器准备

- [ ] 购买云服务器（Ubuntu 24.04，最低 1C1G）
- [ ] 获取公网 IP
- [ ] SSH 登录确认
- [ ] 安装 Python 3.12+（`python3 --version` 确认）
- [ ] 安装 Git（`git --version` 确认）
- [ ] 防火墙/安全组开放 8000 端口（TCP 入站）

## 项目部署

- [ ] `git clone <repo_url>` 克隆项目
- [ ] `cd Echo/backend` 进入后端目录
- [ ] `python3 -m venv .venv` 创建虚拟环境
- [ ] `source .venv/bin/activate` 激活虚拟环境
- [ ] `pip install -r requirements.txt` 安装依赖
- [ ] `cd .. && cp .env.example .env` 创建环境变量文件
- [ ] 编辑 `.env`，填入 `PUSHDEER_KEY=你的真实Key`
- [ ] `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000` 启动服务

## 后端验证

- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `curl http://localhost:8000/status` → `{"state":"normal",...}`
- [ ] 浏览器访问 `http://<公网IP>:8000/docs` → Swagger UI 可用
- [ ] POST /contacts 添加测试联系人
- [ ] POST /heartbeat 发送测试心跳
- [ ] POST /sos/ 触发测试 SOS → PushDeer 收到通知

## 小程序切换

- [ ] 修改 `miniprogram/config.js` 中 `BASE_URL` 为 `http://<公网IP>:8000`
- [ ] 重新编译小程序
- [ ] 真机测试：开启守护 → 心跳正常
- [ ] 真机测试：SOS → 后端收到 + PushDeer 通知
- [ ] 真机测试：设置页 → 联系人 CRUD 正常

## 部署后确认

- [ ] 断网测试：离线缓存 → 恢复后批量补发
- [ ] PushDeer 双通道验证：SOS + Watchdog 均收到通知
- [ ] uvicorn 日志正常输出心跳坐标
