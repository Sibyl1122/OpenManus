#!/usr/bin/env python3
"""
网页视觉理解示例脚本。
该脚本演示了如何使用OpenManus的网页视觉理解功能，
包括浏览网页、截图和图像内容分析。
"""

import asyncio
import os
import sys
import base64
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.base import Agent, Message, Role
from app.config import config, WORKSPACE_ROOT
from app.logger import logger
from app.tool.browser_screenshot import BrowserScreenshot
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.image_understanding import ImageUnderstanding
from app.tool.web_vision import WebVision

# 设置OpenAI模型配置
if not hasattr(config, 'llm') or not config.llm:
    config.llm = {}


async def web_vision_demo():
    """
    演示网页视觉理解功能的完整流程。
    包括：
    1. 打开网页
    2. 截取网页截图
    3. 分析截图内容
    4. 将理解结果整合到对话中
    """
    logger.info("开始网页视觉理解示例...")

    # 初始化代理及工具
    agent = Agent(name="WebVisionAgent")
    browser_tool = BrowserUseTool()
    screenshot_tool = BrowserScreenshot()
    image_tool = ImageUnderstanding()
    web_vision_tool = WebVision()

    try:
        # 步骤1：打开网页
        url = "https://www.weather.com.cn/weather/101020100.shtml"
        logger.info(f"正在打开网页: {url}")
        result = await browser_tool.execute(action="go_to_url", url=url)
        if result.error:
            logger.error(f"打开网页失败: {result.error}")
            return

        # 等待页面加载完成
        await asyncio.sleep(3)

        # 步骤2：使用浏览器截图工具获取浏览器窗口截图
        logger.info("正在使用浏览器截图工具截取浏览器窗口...")

        # 创建screenshots目录
        screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        # 生成带时间戳的文件名
        timestamp = int(time.time())
        screenshot_path = os.path.join("screenshots", f"weather_screenshot_{timestamp}.png")

        # 使用BrowserScreenshot工具获取浏览器截图
        screenshot_result = await screenshot_tool.execute(
            save_path=screenshot_path,
            full_page=True,
            use_selenium=True,  # 使用Selenium方式进行截图
            url=url  # 传递正确的URL
        )

        if screenshot_result.error:
            logger.error(f"截图失败: {screenshot_result.error}")
            return

        # 提取保存的截图路径
        saved_path = None
        content_parts = screenshot_result.output.split()
        logger.info(f"截图结果: {screenshot_result.output}")

        # 尝试从输出中提取路径
        for i, part in enumerate(content_parts):
            if part == "保存到" and i < len(content_parts) - 1:
                saved_path = content_parts[i + 1]
                break

        # 如果没有找到路径，使用我们之前设置的路径
        if not saved_path:
            logger.info("无法从输出中提取路径，使用预设路径")
            saved_path = os.path.join(WORKSPACE_ROOT, screenshot_path)

        logger.info(f"截图已保存到: {saved_path}")

        # 步骤3：分析截图内容
        goal = "详细描述网页的内容、布局和主要功能，并提取可见的重要文本信息"
        logger.info(f"正在分析截图，目标: {goal}")

        # 使用配置文件中的模型进行图像分析
        understanding_result = await image_tool.execute(
            goal=goal,
            image_path=saved_path
            # 不再显式指定模型名称，使用配置中的模型
        )

        if understanding_result.error:
            logger.error(f"图像分析失败: {understanding_result.error}")
            return

        analysis = understanding_result.output
        logger.info("图像分析完成")

        # 步骤4：将结果整合到代理对话中
        logger.info(f"分析结果: {analysis}")

        logger.info("示例完成！")

    except Exception as e:
        logger.error(f"示例运行过程中出错: {str(e)}")
    finally:
        # 清理浏览器资源
        await browser_tool.cleanup()


if __name__ == "__main__":
    asyncio.run(web_vision_demo())
