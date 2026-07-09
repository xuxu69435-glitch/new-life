# 模拟人生 · 单机本地运行说明

本项目是一款**单机本地网页游戏**：前端、后端、存档都在你的电脑上运行，不需要公网服务器，也不需要 PostgreSQL（除非你想用可选的高级配置）。

## 默认地址

| 服务 | 地址 |
|------|------|
| 前端页面 | http://127.0.0.1:1234 |
| 后端接口 | http://127.0.0.1:4321 |
| 后端 health | http://127.0.0.1:4321/health |

## 默认配置

- 运行环境：`ENVIRONMENT=local`
- 存档方式：`SAVE_REPOSITORY_TYPE=sqlite`
- 本地数据库文件：`backend/data/local_save.sqlite3`
- 前端 API 地址：`http://127.0.0.1:4321`

复制 `.env.example` 为 `.env` 可按需调整（不要提交真实 `.env`）。

## 一键启动（Windows 推荐）

在项目根目录 PowerShell 中运行：

```powershell
.\scripts\local_start.ps1
```

启动后会输出：

- 前端页面：http://127.0.0.1:1234
- 后端接口：http://127.0.0.1:4321
- 后端 health：http://127.0.0.1:4321/health

## 一键停止

```powershell
.\scripts\local_stop.ps1
```

会停止占用 **4321**（后端）和 **1234**（前端）端口的本机进程。

## 手动启动

### 后端

```powershell
cd backend
$env:ENVIRONMENT="local"
$env:SAVE_REPOSITORY_TYPE="sqlite"
$env:SQLITE_DATABASE_PATH="data/local_save.sqlite3"
$env:BACKEND_HOST="127.0.0.1"
$env:BACKEND_PORT="4321"
python -m uvicorn app.main:app --host 127.0.0.1 --port 4321
```

### 前端

```powershell
cd frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:4321"
npm install
npm run dev
```

## 备份本地存档

```powershell
.\scripts\local_backup_data.ps1
```

会将 `backend/data/local_save.sqlite3` 复制到 `backend/backups/local_save_YYYYMMDD_HHMMSS.sqlite3`。

## 重置本地存档

```powershell
.\scripts\local_reset_data.ps1
```

执行前会要求输入 `YES` 确认。原数据库会被移动到 `backend/backups/`，不会直接删除。

## 切换存档模式

通过环境变量 `SAVE_REPOSITORY_TYPE` 切换：

| 值 | 说明 |
|----|------|
| `sqlite` | **默认**。本地文件持久化，适合单机游玩 |
| `memory` | 内存模式，重启后数据丢失，适合快速测试 |
| `postgres` | 可选高级方案，需要 PostgreSQL 服务 |

PostgreSQL 和 `docker-compose.yml` 仍保留为可选部署方案，**不是当前默认路径**。

## 运行测试

### 后端

```powershell
cd backend
python -m pytest tests/ -v
```

PostgreSQL 集成测试默认跳过，需设置 `RUN_POSTGRES_TESTS=1` 才会运行。

### 前端构建

```powershell
cd frontend
npm install
npm run build
```

## 本地数据目录

| 路径 | 用途 |
|------|------|
| `backend/data/` | SQLite 存档（默认 `local_save.sqlite3`） |
| `backend/backups/` | 手动备份与重置前的归档 |
| `.local-run/` | 本地启动脚本记录的进程 PID |

以上目录均已在 `.gitignore` 中忽略，不会提交到 Git。
