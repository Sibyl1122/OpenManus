#!/usr/bin/env python
# coding: utf-8
"""
OpenManus 作业引擎使用示例

此脚本演示如何：
1. 创建作业
2. 添加任务
3. 运行作业
4. 监控作业状态
"""

import asyncio
import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 导入必要模块
from app.db import init_db
from app.db.job_engine import job_engine
from app.db.job_runner import job_runner
from app.db.models import JobStatus


async def demo_job_engine():
    """作业引擎演示"""
    print("=== OpenManus 作业引擎演示 ===")

    # 初始化数据库
    print("初始化数据库...")
    init_db()

    # 创建作业
    print("\n1. 创建新作业")
    job_id = job_engine.create_job("示例演示作业")
    print(f"  - 创建的作业 ID: {job_id}")

    # 添加任务
    print("\n2. 添加任务到作业")
    task_ids = []
    for i in range(3):
        task_content = f"示例任务 #{i+1}"
        task_id = job_engine.add_task(job_id, task_content)
        task_ids.append(task_id)
        print(f"  - 添加任务: {task_content} (ID: {task_id})")

    # 获取作业详情
    print("\n3. 获取作业详情")
    job_details = job_engine.get_job(job_id)
    print(f"  - 作业状态: {job_details['status']}")
    print(f"  - 任务数量: {len(job_details['tasks'])}")

    # 启动作业
    print("\n4. 启动作业")
    success = await job_runner.start_job(job_id)
    if success:
        print(f"  - 作业 {job_id} 已开始运行")
    else:
        print(f"  - 作业 {job_id} 启动失败")
        return

    # 监控作业状态
    print("\n5. 监控作业状态")
    for _ in range(10):
        job_details = job_engine.get_job(job_id)
        print(f"  - 当前状态: {job_details['status']}")

        # 如果作业已经完成或失败，跳出循环
        if job_details['status'] in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
            break

        # 等待一秒
        await asyncio.sleep(1)

    # 获取最终作业详情
    print("\n6. 最终作业详情")
    job_details = job_engine.get_job(job_id)
    print(json.dumps(job_details, indent=2, ensure_ascii=False))

    # 列出所有作业
    print("\n7. 列出所有作业")
    all_jobs = job_engine.list_jobs()
    print(f"  - 总作业数: {len(all_jobs)}")
    for job in all_jobs:
        print(f"  - 作业 ID: {job['job_id']}, 状态: {job['status']}")

    print("\n演示完成！")


if __name__ == "__main__":
    try:
        asyncio.run(demo_job_engine())
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    finally:
        # 确保资源被清理
        asyncio.run(job_runner.shutdown())
