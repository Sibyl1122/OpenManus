# OpenManus 持久层与作业引擎使用手册

## 目录

- [1. 概述](#1-概述)
- [2. 数据库结构](#2-数据库结构)
- [3. 作业引擎功能](#3-作业引擎功能)
- [4. 快速开始](#4-快速开始)
- [5. API 使用指南](#5-api-使用指南)
- [6. 常见问题解答](#6-常见问题解答)

## 1. 概述

OpenManus 持久层使用 SQLite 作为轻量级数据库，用于存储作业、任务和工具使用记录。作业引擎提供了一套完整的 API，用于创建、监控和管理自动化任务的执行流程。

系统主要组件：
- **数据库层**：使用 SQLAlchemy ORM 框架管理 SQLite 数据库
- **作业引擎**：管理作业生命周期，包括创建、运行、监控和终止
- **任务执行器**：执行具体任务，记录工具使用情况和结果
- **作业工具**：提供给 AI 代理使用的工具接口

## 2. 数据库结构

### 2.1 主要表

系统包含三个主要表：

#### 作业表 (jobs)
- `id`：自增主键
- `job_id`：唯一作业标识符
- `description`：作业描述
- `status`：作业状态（pending, running, completed, failed, cancelled）
- `start_time`：开始时间
- `end_time`：结束时间
- `created_at`：创建时间

#### 任务表 (tasks)
- `id`：自增主键
- `content`：任务内容
- `status`：任务状态（pending, running, completed, failed, cancelled）
- `start_time`：开始时间
- `end_time`：结束时间
- `created_at`：创建时间
- `job_id`：关联的作业 ID

#### 工具使用表 (tool_uses)
- `id`：自增主键
- `tool_name`：工具名称
- `args`：工具参数（JSON 格式）
- `result`：工具执行结果
- `created_at`：创建时间
- `task_id`：关联的任务 ID

### 2.2 状态流转

作业和任务状态遵循以下流转：

```
pending → running → completed/failed
          └──────→ cancelled
```

## 3. 作业引擎功能

作业引擎提供以下核心功能：

- **作业管理**：创建、查询、列出和取消作业
- **任务管理**：添加、执行和监控任务
- **工具使用记录**：记录工具调用和结果
- **异步执行**：支持后台异步执行作业
- **状态追踪**：实时监控作业执行状态

## 4. 快速开始

### 4.1 启动作业引擎

```bash
# 普通模式启动
python run_job_engine.py

# 调试模式启动
python run_job_engine.py --debug
```

### 4.2 通过作业工具使用

在 OpenManus 框架中，可以直接通过 `job` 工具使用作业引擎功能：

```python
# 创建作业
result = await job_tool.execute(action="create_job", description="测试作业")
job_id = result["job_id"]

# 添加任务
await job_tool.execute(action="add_task", job_id=job_id, content="执行某项操作")

# 运行作业
await job_tool.execute(action="run_job", job_id=job_id)

# 获取作业状态
job_status = await job_tool.execute(action="get_job", job_id=job_id)
```

### 4.3 直接使用 API

也可以直接使用作业引擎 API：

```python
from app.db.job_engine import job_engine
from app.db.job_runner import job_runner

# 创建作业
job_id = job_engine.create_job("测试作业")

# 添加任务
task_id = job_engine.add_task(job_id, "执行某项操作")

# 运行作业
await job_runner.start_job(job_id)
```

## 5. API 使用指南

### 5.1 作业工具 API

作业工具支持以下操作：

| 操作 | 参数 | 描述 |
|------|------|------|
| `create_job` | `description` (可选) | 创建新作业 |
| `add_task` | `job_id`, `content` | 向作业添加任务 |
| `get_job` | `job_id` | 获取作业详情 |
| `list_jobs` | `status` (可选) | 列出所有作业 |
| `run_job` | `job_id` | 运行作业 |
| `cancel_job` | `job_id` | 取消作业 |
| `get_job_stats` | `job_id` | 获取作业执行统计信息 |

### 5.2 作业引擎 API

作业引擎提供以下 API：

```python
# 创建作业
job_id = job_engine.create_job(description)

# 获取作业
job = job_engine.get_job(job_id)

# 列出作业
jobs = job_engine.list_jobs(status)

# 添加任务
task_id = job_engine.add_task(job_id, content)

# 记录工具使用
tool_use_id = job_engine.record_tool_use(task_id, tool_name, args, result)

# 更新工具结果
job_engine.update_tool_result(tool_use_id, result)

# 取消作业
success = job_engine.cancel_job(job_id)

# 获取作业统计
stats = job_engine.get_job_stats(job_id)
```

### 5.3 作业运行器 API

作业运行器提供以下 API：

```python
# 启动作业
success = await job_runner.start_job(job_id)

# 取消作业
success = await job_runner.cancel_job(job_id)

# 关闭服务
await job_runner.shutdown()
```

## 6. 常见问题解答

### 6.1 数据存储在哪里？

默认情况下，数据库文件存储在项目根目录的 `data/openmanus.db`。这是一个 SQLite 数据库文件。

### 6.2 如何备份数据？

由于使用 SQLite 数据库，备份非常简单，只需复制 `data/openmanus.db` 文件即可：

```bash
cp data/openmanus.db data/openmanus.db.backup
```

### 6.3 作业执行失败怎么办？

查看失败的作业和任务：

```python
# 列出所有失败的作业
failed_jobs = job_engine.list_jobs(JobStatus.FAILED)

# 查看具体失败作业的详情
job_details = job_engine.get_job("job_id")
```

失败的作业会包含具体的任务执行状态和工具使用记录，有助于诊断问题。

### 6.4 如何自定义任务处理逻辑？

目前系统使用了一个简单的演示任务处理器。要实现真正的任务处理，需要修改 `app/db/job_runner.py` 中的 `_process_task` 方法，实现自定义的任务解析和执行逻辑。

### 6.5 可以同时运行多个作业吗？

是的，作业引擎支持同时运行多个作业，每个作业在单独的异步任务中执行。

### 6.6 作业是否会自动重试？

默认情况下，作业不会自动重试。如果需要重试机制，可以修改 `app/db/job_runner.py` 中的 `_run_job` 方法，添加重试逻辑。
