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
- 本地日志目录：`.local-run/logs`

复制 `.env.example` 为 `.env` 可按需调整（不要提交真实 `.env`）。

## 推荐启动（像单机游戏一样一键启动）

在项目根目录 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_game.ps1
```

`start_game.ps1` 会自动：

1. 检查 Python、Node、npm 是否可用
2. 检查 `backend` / `frontend` 目录是否存在
3. 检查后端依赖（缺失时自动执行 `pip install -e .`）
4. 检查前端 `node_modules`（缺失时自动执行 `npm install`）
5. 调用 `local_start.ps1` 启动后端和前端
6. 等待后端 health 通过（最多 60 秒）
7. 等待前端页面可访问（最多 60 秒）
8. 自动打开浏览器到 http://127.0.0.1:1234

启动失败时会提示日志位置：

- `.local-run/logs/launcher.log`
- `.local-run/logs/backend.log`
- `.local-run/logs/frontend.log`

## 停止游戏

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_stop.ps1
```

会优先停止 `.local-run` 中记录的本项目进程，并确认 4321 / 1234 端口不再被本项目占用。

## 查看状态

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_status.ps1
```

显示后端/前端运行状态、health、SQLite 存档大小、最近备份、日志目录等。

## 仅打开浏览器

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_open.ps1
```

若后端 health 不可用，会提示先运行 `start_game.ps1`。

## 仅启动服务（不等待、不打开浏览器）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_start.ps1
```

适用于已熟悉手动排查的场景。若端口已被本项目占用，会提示已运行而不重复启动。

## 备份本地存档

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_backup_data.ps1
```

会将 `backend/data/local_save.sqlite3` 复制到 `backend/backups/local_save_YYYYMMDD_HHMMSS.sqlite3`。

## 重置本地存档

```powershell
powershell -ExecutionPolicy Bypass -File scripts\local_reset_data.ps1
```

执行前会要求输入 `YES` 确认。原数据库会被移动到 `backend/backups/`，不会直接删除。启动器**不会**删除 SQLite 存档。

## 切换存档模式

通过环境变量 `SAVE_REPOSITORY_TYPE` 切换：

| 值 | 说明 |
|----|------|
| `sqlite` | **默认**。本地文件持久化，适合单机游玩 |
| `memory` | 内存模式，重启后数据丢失，适合快速测试 |
| `postgres` | 可选高级方案，需要 PostgreSQL 服务 |

PostgreSQL 和 `docker-compose.yml` 仍保留为可选方案，**不是当前默认路径**。服务器部署不是当前目标。

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
| `.local-run/` | 进程 PID、运行状态 |
| `.local-run/logs/` | `launcher.log`、`backend.log`、`frontend.log` |

以上目录均已在 `.gitignore` 中忽略，不会提交到 Git。
