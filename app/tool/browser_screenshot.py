import asyncio
import base64
import os
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import Field

from app.config import WORKSPACE_ROOT
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.browser_use_tool import BrowserUseTool

Context = TypeVar("Context")


class BrowserScreenshot(BaseTool, Generic[Context]):
    name: str = "browser_screenshot"
    description: str = """
对当前浏览的网页进行截图并保存。
此工具将对浏览器当前页面进行完整截图，并可以选择性地将截图保存到指定位置。
功能包括:
- 获取当前页面的完整截图
- 将截图保存为图像文件
- 返回截图的Base64编码以便后续处理
- 自动生成带有时间戳的文件名
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "save_path": {
                "type": "string",
                "description": "截图保存路径，可以是相对于工作区的路径或绝对路径。如果不指定，将使用自动生成的文件名保存到工作区的'screenshots'目录",
            },
            "full_page": {
                "type": "boolean",
                "description": "是否进行全页面截图（包括需要滚动才能看到的部分）。默认为true",
            },
        },
    }

    browser_tool: BrowserUseTool = Field(default_factory=BrowserUseTool)

    async def execute(
        self,
        save_path: Optional[str] = None,
        full_page: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        对当前浏览的网页进行截图并保存。

        Args:
            save_path: 截图保存的路径，如果不指定则自动生成文件名
            full_page: 是否截取完整的页面

        Returns:
            包含截图保存路径和Base64编码的ToolResult
        """
        try:
            # 确保浏览器已初始化
            logger.info("正在获取浏览器当前状态...")

            # 确保浏览器工具已准备好使用
            if not self.browser_tool.browser or not self.browser_tool.context:
                logger.info("初始化浏览器...")
                await self.browser_tool._ensure_browser_initialized()

            # 获取当前页面
            page = await self.browser_tool.context.get_current_page()
            if not page:
                return ToolResult(error="无法获取浏览器当前页面")

            # 获取当前URL作为参考
            url = await page.get_current_url()
            logger.info(f"正在对页面进行截图: {url}")

            # 执行截图
            screenshot_bytes = await page.screenshot(full_page=full_page)
            base64_screenshot = base64.b64encode(screenshot_bytes).decode("utf-8")

            # 确定保存路径
            if not save_path:
                # 创建screenshots目录
                screenshots_dir = os.path.join(WORKSPACE_ROOT, "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)

                # 基于URL和时间戳生成文件名
                domain = url.split("//")[-1].split("/")[0].replace(".", "_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{domain}_{timestamp}.png"
                save_path = os.path.join("screenshots", filename)

            # 解析保存路径
            if os.path.isabs(save_path):
                full_save_path = save_path
            else:
                full_save_path = os.path.join(WORKSPACE_ROOT, save_path)

            # 确保目录存在
            os.makedirs(os.path.dirname(full_save_path), exist_ok=True)

            # 保存截图
            with open(full_save_path, "wb") as f:
                f.write(screenshot_bytes)

            logger.info(f"截图已保存至: {full_save_path}")

            # 返回结果
            return ToolResult(
                content=f"成功获取网页截图并保存到 {full_save_path}",
                base64_image=base64_screenshot
            )

        except Exception as e:
            logger.error(f"截图过程中出错: {str(e)}")
            return ToolResult(error=f"截图失败: {str(e)}")

    @classmethod
    def create_with_context(cls, context: Context) -> "BrowserScreenshot[Context]":
        """使用上下文创建工具实例，便于共享浏览器会话"""
        instance = cls()
        instance.browser_tool = BrowserUseTool.create_with_context(context)
        return instance
