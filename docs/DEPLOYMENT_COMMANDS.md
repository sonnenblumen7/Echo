# DEPLOYMENT_COMMANDS.md

> Echo 云部署完整命令（从空 Ubuntu 到服务启动）

## 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.12 + pip + venv
sudo apt install -y python3 python3-pip python3-venv git

# 确认版本
python3 --version    # 需要 3.12+
git --version
```

## 2. 克隆项目

```bash
# 克隆到用户目录
cd ~
git clone <你的仓库地址>
cd Echo
```

## 3. 配置环境变量

```bash
# 从模板创建 .env
cp .env.example .env

# 编辑 .env，填入真实 PushDeer Key
nano .env
# 内容改为：
# PUSHDEER_KEY=你的真实Key
# 保存退出 (Ctrl+O, Enter, Ctrl+X)
```

## 4. 创建虚拟环境 + 安装依赖

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 确认安装成功
pip list | grep fastapi
```

## 5. 启动服务

```bash
# 前台启动（测试用，Ctrl+C 可停止）
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 6. 验证（新终端执行）

```bash
# 健康检查
curl http://localhost:8000/health

# 状态查询
curl http://localhost:8000/status

# 添加测试联系人
curl -X POST http://localhost:8000/contacts \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","name":"测试"}'

# 发送测试心跳
curl -X POST http://localhost:8000/heartbeat \
  -H "Content-Type: application/json" \
  -d '[{"device_id":"test","latitude":36.6,"longitude":101.7,"client_ts":1780000000,"type":"physical"}]'

# 触发测试 SOS
curl -X POST http://localhost:8000/sos/ \
  -H "Content-Type: application/json" \
  -d '{"latitude":36.6,"longitude":101.7,"client_ts":1780000001}'
```

## 7. 小程序切换（本地电脑操作）

修改 `miniprogram/config.js`：

```javascript
module.exports = {
  BASE_URL: "http://<你的公网IP>:8000"
};
```

微信开发者工具重新编译，真机测试。

## 8. 后台运行（可选）

```bash
# 使用 nohup 后台运行（SSH 断开后继续运行）
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > echo.log 2>&1 &

# 查看日志
tail -f echo.log

# 停止服务
pkill -f uvicorn
```

## 注意事项

- 公网 IP 需要在云服务器安全组/防火墙中开放 8000 端口
- `.env` 文件不要提交到 Git（已在 .gitignore 中）
- SQLite 数据库文件 `echo.db` 自动生成在 backend/ 目录下
- uvicorn 前台运行时关闭终端会停止服务，建议用 nohup 或 systemd 托管
