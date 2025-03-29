#!/usr/bin/env python3
"""
网页视觉理解示例脚本。
该脚本演示了如何使用OpenManus的网页视觉理解功能，
包括浏览网页、截图和图像内容分析。
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.base import Agent, Message, Role
from app.config import config
from app.logger import logger
from app.tool.browser_screenshot import BrowserScreenshot
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.image_understanding import ImageUnderstanding
from app.tool.web_vision import WebVision


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
    agent = Agent()
    browser_tool = BrowserUseTool()
    screenshot_tool = BrowserScreenshot()
    image_tool = ImageUnderstanding()
    web_vision_tool = WebVision()

    try:
        # 步骤1：打开网页
        url = "https://github.com/siliconflow/OpenManus"
        logger.info(f"正在打开网页: {url}")
        result = await browser_tool.execute(action="go_to_url", url=url)
        if result.error:
            logger.error(f"打开网页失败: {result.error}")
            return

        # 等待页面加载完成
        await asyncio.sleep(3)

        # 步骤2：获取网页截图
        logger.info("正在截取网页截图...")
        screenshot_result = await screenshot_tool.execute()
        if screenshot_result.error:
            logger.error(f"截图失败: {screenshot_result.error}")
            return

        # 提取保存的截图路径
        saved_path = None
        content_parts = screenshot_result.content.split()
        for i, part in enumerate(content_parts):
            if part == "保存到" and i < len(content_parts) - 1:
                saved_path = content_parts[i + 1]
                break

        if not saved_path:
            logger.error("无法确定截图保存路径")
            return

        logger.info(f"截图已保存到: {saved_path}")

        # 步骤3：分析截图内容
        goal = "详细描述网页的内容、布局和主要功能，并提取可见的重要文本信息"
        logger.info(f"正在分析截图，目标: {goal}")

        understanding_result = await image_tool.execute(
            goal=goal,
            image_path=saved_path
        )

        if understanding_result.error:
            logger.error(f"图像分析失败: {understanding_result.error}")
            return

        analysis = understanding_result.content
        logger.info("图像分析完成")

        # 步骤4：将结果整合到代理对话中
        logger.info("将分析结果整合到对话中...")

        # 模拟用户问题
        await agent.add_message(Role.USER, "请分析当前网页并告诉我它的主要内容是什么？")

        # 添加带图像的助手响应
        await agent.add_message(
            Role.ASSISTANT,
            f"我已经对您正在浏览的网页进行了分析，以下是结果：\n\n{analysis}",
            base64_image=screenshot_result.base64_image
        )

        # 打印对话历史
        logger.info("对话历史:")
        for msg in agent.message_history:
            logger.info(f"{msg.role}: {msg.content[:100]}..." if len(msg.content) > 100 else f"{msg.role}: {msg.content}")

        # 步骤5：演示一体化工具
        logger.info("\n演示一体化Web视觉工具...")
        web_vision_result = await web_vision_tool.execute(
            goal="识别页面上的主要功能区域，并总结页面的整体用途"
        )

        if web_vision_result.error:
            logger.error(f"Web视觉分析失败: {web_vision_result.error}")
            return

        logger.info("Web视觉分析完成")

        # 将结果添加到对话中
        await agent.add_message(Role.USER, "请分析这个页面的主要功能区域是什么？")
        await agent.add_message(
            Role.ASSISTANT,
            web_vision_result.content,
            base64_image=web_vision_result.base64_image
        )

        logger.info("示例完成！")

    except Exception as e:
        logger.error(f"示例运行过程中出错: {str(e)}")
    finally:
        # 清理浏览器资源
        await browser_tool.cleanup()


if __name__ == "__main__":
    asyncio.run(web_vision_demo())
