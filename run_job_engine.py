#!/usr/bin/env python
# coding: utf-8
"""
OpenManus 作业引擎启动脚本
"""

import asyncio
import argparse
import logging
import os
import sys
import signal

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("job_engine")

# 导入必要模块
from app.db import init_db
from app.db.job_engine import job_engine
from app.db.job_runner import job_runner


async def run_job_service():
    """运行作业服务"""
    # 确保数据目录存在
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

    # 初始化数据库表
    init_db()

    logger.info("作业引擎已启动，按 Ctrl+C 停止...")

    # 设置信号处理
    def signal_handler():
        logger.info("正在关闭作业引擎...")
        asyncio.create_task(job_runner.shutdown())

    # 添加信号处理器
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(sig, signal_handler)

    try:
        # 保持服务运行
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("作业引擎服务被取消")
    finally:
        # 确保资源被清理
        await job_runner.shutdown()
        logger.info("作业引擎已关闭")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="OpenManus 作业引擎")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式输出详细日志"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("调试模式已启用")

    # 运行作业服务
    try:
        asyncio.run(run_job_service())
    except KeyboardInterrupt:
        logger.info("接收到退出信号，正在关闭...")
    except Exception as e:
        logger.exception(f"作业引擎运行异常: {str(e)}")
        sys.exit(1)
