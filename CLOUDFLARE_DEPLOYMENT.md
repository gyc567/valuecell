# ValueCell Cloudflare 部署完全指南 🚀

## 目录
1. [项目架构概览](#项目架构概览)
2. [准备工作](#准备工作)
3. [后端部署方案](#后端部署方案)
4. [前端部署到 Cloudflare Pages](#前端部署到-cloudflare-pages)
5. [配置环境变量](#配置环境变量)
6. [域名和路由配置](#域名和路由配置)
7. [测试和验证](#测试和验证)
8. [常见问题解决](#常见问题解决)

## 项目架构概览

ValueCell 是一个前后端分离的金融 AI 应用：
- **前端**：React 19 + TypeScript + Vite (可部署到 Cloudflare Pages)
- **后端**：Python 3.12 + FastAPI + 多个 AI 智能体 (需要另外的服务器)
- **数据库**：SQLite (轻量级，无需额外数据库服务)

### ⚠️ 重要说明
由于 Cloudflare Workers 对 Python 支持有限，且本项目后端依赖大量 Python 库和 AI 模型，建议采用**混合部署方案**：
- **前端** → Cloudflare Pages
- **后端** → VPS 或云服务器（如 AWS EC2、Google Cloud、Azure）

## 准备工作

### 1. 注册 Cloudflare 账号
1. 访问 [https://www.cloudflare.com](https://www.cloudflare.com)
2. 点击 "Sign Up" 注册账号
3. 验证邮箱
4. 登录到 Cloudflare Dashboard

### 2. 准备 API 密钥
在部署前，你需要准备以下 API 密钥：

```bash
# 必需的 API 密钥
OPENROUTER_API_KEY=     # 从 https://openrouter.ai/ 获取
SEC_EMAIL=              # SEC 数据访问需要的邮箱

# 可选的 API 密钥（增强功能）
OPENAI_API_KEY=         # OpenAI API
FINNHUB_API_KEY=        # 金融新闻数据
GOOGLE_API_KEY=         # Google AI 模型
```

### 3. 安装必要工具
在本地开发环境安装：

```bash
# Node.js 和 npm (用于构建前端)
# 访问 https://nodejs.org 下载安装

# Git (用于版本控制)
# 访问 https://git-scm.com 下载安装

# Cloudflare Wrangler CLI (可选，用于命令行部署)
npm install -g wrangler
```

## 后端部署方案

### 选项 1：使用 VPS 部署后端（推荐）

#### 步骤 1：选择 VPS 提供商
推荐的 VPS 提供商：
- **DigitalOcean**：$6/月起，简单易用
- **Vultr**：$6/月起，全球节点多
- **Linode**：$5/月起，性能稳定
- **AWS EC2**：免费套餐一年

#### 步骤 2：创建和配置服务器

```bash
# 1. 创建 Ubuntu 22.04 LTS 服务器（最低配置：2GB RAM, 2 CPU）

# 2. SSH 登录到服务器
ssh root@your-server-ip

# 3. 更新系统
apt update && apt upgrade -y

# 4. 安装 Python 3.12
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install python3.12 python3.12-venv python3.12-dev -y

# 5. 安装 uv (Python 包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 6. 安装 Git
apt install git -y

# 7. 克隆项目
git clone https://github.com/ValueCell-ai/valuecell.git
cd valuecell

# 8. 配置环境变量
cp .env.example .env
nano .env  # 编辑并填入你的 API 密钥

# 9. 安装依赖并初始化数据库
cd python
uv sync
uv run valuecell/server/db/init_db.py

# 10. 安装 PM2 (进程管理器)
apt install nodejs npm -y
npm install -g pm2
```

#### 步骤 3：创建启动脚本

创建文件 `/root/valuecell/start-backend.sh`：

```bash
#!/bin/bash
cd /root/valuecell/python
source /root/.local/bin/env
uv run -m valuecell.server.main
```

#### 步骤 4：使用 PM2 管理后端进程

```bash
# 添加执行权限
chmod +x /root/valuecell/start-backend.sh

# 使用 PM2 启动后端
pm2 start /root/valuecell/start-backend.sh --name valuecell-backend

# 保存 PM2 配置
pm2 save
pm2 startup systemd
```

#### 步骤 5：配置 Nginx 反向代理

```bash
# 安装 Nginx
apt install nginx -y

# 创建配置文件
nano /etc/nginx/sites-available/valuecell
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;  # 替换为你的域名

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用配置
ln -s /etc/nginx/sites-available/valuecell /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### 步骤 6：配置防火墙

```bash
# 安装 UFW
apt install ufw -y

# 配置规则
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### 选项 2：使用 Docker 部署（适合熟悉 Docker 的用户）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - SEC_EMAIL=${SEC_EMAIL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FINNHUB_API_KEY=${FINNHUB_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

部署步骤：

```bash
# 在服务器上
docker-compose up -d
```

## 前端部署到 Cloudflare Pages

### 步骤 1：准备前端代码

在本地开发环境：

```bash
# 1. 克隆项目（如果还没有）
git clone https://github.com/ValueCell-ai/valuecell.git
cd valuecell

# 2. 进入前端目录
cd frontend

# 3. 安装依赖
npm install  # 或使用 bun install

# 4. 修改 API 端点配置
```

创建 `frontend/.env.production`：

```bash
# 指向你的后端服务器
VITE_API_BASE_URL=https://api.yourdomain.com
```

修改 `frontend/src/api/config.ts`（如果需要）：

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.yourdomain.com';
```

### 步骤 2：构建前端

```bash
# 在 frontend 目录下
npm run build  # 或 bun run build

# 构建完成后，输出在 build/client 目录
```

### 步骤 3：部署到 Cloudflare Pages

#### 方法 A：通过 Cloudflare Dashboard（推荐新手）

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 点击左侧 "Pages"
3. 点击 "Create a project" → "Connect to Git"
4. 授权 GitHub 账号
5. 选择你 fork 的 valuecell 仓库
6. 配置构建设置：
   ```
   Framework preset: None
   Build command: cd frontend && npm install && npm run build
   Build output directory: frontend/build/client
   Root directory: /
   ```
7. 添加环境变量：
   ```
   VITE_API_BASE_URL = https://api.yourdomain.com
   ```
8. 点击 "Save and Deploy"

#### 方法 B：使用 Wrangler CLI

```bash
# 1. 登录 Cloudflare
wrangler login

# 2. 在 frontend 目录创建 wrangler.toml
cat > wrangler.toml << EOF
name = "valuecell-frontend"
compatibility_date = "2024-01-01"

[site]
bucket = "./build/client"
EOF

# 3. 部署
wrangler pages publish build/client --project-name=valuecell-frontend
```

#### 方法 C：直接上传（最简单）

1. 在 Cloudflare Dashboard 进入 Pages
2. 点击 "Create a project" → "Direct Upload"
3. 拖拽 `frontend/build/client` 文件夹到上传区域
4. 设置项目名称
5. 点击 "Deploy site"

### 步骤 4：配置自定义域名

1. 在 Cloudflare Pages 项目设置中
2. 点击 "Custom domains"
3. 添加你的域名（如 `app.yourdomain.com`）
4. 按照提示配置 DNS 记录

## 配置环境变量

### 后端环境变量（.env）

```bash
# 应用设置
APP_NAME=ValueCell
APP_VERSION=0.1.0
APP_ENVIRONMENT=production
API_DEBUG=false

# API 设置
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8000

# 语言和时区
LANG=zh-CN
TIMEZONE=Asia/Shanghai

# AI 模型配置
OPENROUTER_API_KEY=sk-or-v1-xxxxx
PLANNER_MODEL_ID=google/gemini-2.5-flash
SEC_PARSER_MODEL_ID=openai/gpt-4o-mini
SEC_ANALYSIS_MODEL_ID=deepseek/deepseek-chat-v3-0324
RESEARCH_AGENT_MODEL_ID=google/gemini-2.5-flash

# SEC 数据
SEC_EMAIL=your-email@example.com

# 可选服务
OPENAI_API_KEY=sk-xxxxx
FINNHUB_API_KEY=xxxxx
XUEQIU_TOKEN=xxxxx  # 雪球网 token，用于中国市场数据
```

### 前端环境变量

在 Cloudflare Pages 设置中添加：

```bash
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

## 域名和路由配置

### 1. 配置 DNS 记录

在 Cloudflare DNS 设置中添加：

```
类型    名称    内容                     代理状态
A       api     你的服务器IP              已代理
CNAME   app     你的pages项目.pages.dev   已代理
```

### 2. 配置 SSL/TLS

1. 在 Cloudflare Dashboard → SSL/TLS
2. 选择 "Full (strict)" 模式
3. 在服务器上安装 Certbot：

```bash
# 在服务器上
apt install certbot python3-certbot-nginx -y
certbot --nginx -d api.yourdomain.com
```

### 3. 配置 CORS

确保后端允许前端域名访问，在 `.env` 中：

```bash
CORS_ORIGINS=["https://app.yourdomain.com", "http://localhost:1420"]
```

## 测试和验证

### 1. 测试后端 API

```bash
# 测试根路径
curl https://api.yourdomain.com

# 应返回：
# {"success":true,"data":{"name":"ValueCell","version":"0.1.0","environment":"production"},"msg":"Welcome to ValueCell API"}
```

### 2. 测试前端访问

1. 访问 `https://app.yourdomain.com`
2. 检查浏览器控制台是否有错误
3. 尝试与 AI 智能体对话

### 3. 监控日志

```bash
# 在服务器上查看后端日志
pm2 logs valuecell-backend

# 查看 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## 常见问题解决

### 问题 1：CORS 错误

**症状**：浏览器控制台显示 "CORS policy" 错误

**解决方案**：
1. 检查后端 CORS 配置
2. 确保前端域名在允许列表中
3. 重启后端服务

### 问题 2：WebSocket 连接失败

**症状**：实时聊天功能不工作

**解决方案**：

在 Nginx 配置中添加 WebSocket 支持：

```nginx
location /ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 问题 3：API 请求超时

**症状**：AI 响应时间过长导致超时

**解决方案**：

增加 Nginx 超时时间：

```nginx
proxy_connect_timeout 600;
proxy_send_timeout 600;
proxy_read_timeout 600;
send_timeout 600;
```

### 问题 4：内存不足

**症状**：后端服务频繁崩溃

**解决方案**：
1. 升级服务器配置（建议至少 4GB RAM）
2. 配置 swap 空间：

```bash
# 创建 4GB swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 问题 5：前端构建失败

**症状**：Cloudflare Pages 构建报错

**解决方案**：
1. 检查 Node.js 版本兼容性
2. 在 Cloudflare Pages 设置中指定 Node 版本：
   ```
   NODE_VERSION=20
   ```
3. 清理缓存重新部署

## 性能优化建议

### 1. 启用 Cloudflare 缓存

在 Cloudflare Dashboard → Caching → Configuration：
- 设置缓存级别为 "Standard"
- 启用 "Always Online"
- 配置页面规则缓存静态资源

### 2. 优化后端性能

```python
# 在后端配置中启用响应压缩
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 3. 数据库优化

定期清理和优化 SQLite 数据库：

```bash
# 创建定时任务
crontab -e

# 添加每周优化任务
0 3 * * 0 cd /root/valuecell/python && uv run -c "import sqlite3; conn = sqlite3.connect('data/valuecell.db'); conn.execute('VACUUM'); conn.close()"
```

## 监控和维护

### 1. 设置健康检查

创建 `/root/valuecell/health-check.sh`：

```bash
#!/bin/bash
if ! curl -f http://localhost:8000/ > /dev/null 2>&1; then
    pm2 restart valuecell-backend
fi
```

添加到 crontab：
```bash
*/5 * * * * /root/valuecell/health-check.sh
```

### 2. 日志轮转

配置 logrotate：

```bash
cat > /etc/logrotate.d/valuecell << EOF
/root/valuecell/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 640 root root
}
EOF
```

### 3. 备份策略

```bash
# 每日备份脚本
cat > /root/backup-valuecell.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# 备份数据库
cp /root/valuecell/python/data/valuecell.db $BACKUP_DIR/valuecell-$DATE.db

# 备份配置
cp /root/valuecell/.env $BACKUP_DIR/env-$DATE

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "env-*" -mtime +7 -delete
EOF

chmod +x /root/backup-valuecell.sh

# 添加到 crontab
echo "0 2 * * * /root/backup-valuecell.sh" | crontab -
```

## 安全建议

### 1. 限制 API 访问

使用 Cloudflare Rate Limiting 防止滥用：
- Dashboard → Security → Rate limiting
- 创建规则限制每个 IP 的请求频率

### 2. 启用 Web Application Firewall (WAF)

- Dashboard → Security → WAF
- 启用 Cloudflare 管理规则集

### 3. 定期更新

```bash
# 更新系统包
apt update && apt upgrade -y

# 更新 Python 依赖
cd /root/valuecell/python
uv sync --upgrade

# 更新前端依赖
cd /root/valuecell/frontend
npm update
```

## 成本估算

### 基础部署成本（每月）
- **Cloudflare Pages**：免费（前端托管）
- **VPS 服务器**：$6-20（后端运行）
- **域名**：$1-2（如果需要购买）
- **总计**：约 $7-22/月

### 可选服务成本
- **OpenRouter API**：按使用量计费，约 $10-50/月
- **OpenAI API**：按使用量计费
- **Finnhub**：免费套餐可用

## 总结

恭喜！按照以上步骤，你应该已经成功将 ValueCell 部署到生产环境：

✅ 后端运行在 VPS 上，通过 PM2 管理  
✅ 前端部署在 Cloudflare Pages  
✅ 使用 Cloudflare 的 CDN 和安全功能  
✅ 配置了 SSL 证书和自定义域名  

### 下一步
1. 🔍 监控应用性能和错误
2. 📊 分析用户使用情况
3. 🚀 根据需求扩展功能
4. 💬 加入社区获取支持

### 获取帮助
- GitHub Issues: https://github.com/ValueCell-ai/valuecell/issues
- Discord 社区: https://discord.com/invite/84Kex3GGAh
- 官方文档: 查看项目 README

祝你使用愉快！🎉