import os
from typing import Generic, Optional, TypeVar

from pydantic import Field

from app.config import WORKSPACE_ROOT
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.browser_screenshot import BrowserScreenshot
from app.tool.image_understanding import ImageUnderstanding

Context = TypeVar("Context")


class WebVision(BaseTool, Generic[Context]):
    name: str = "web_vision"
    description: str = """
分析网页视觉内容工具。此工具结合了网页截图和图像理解功能，可以获取当前浏览的网页截图并进行分析。
功能包括:
- 对当前浏览的网页进行截图
- 保存截图到指定位置
- 使用多模态模型分析截图内容
- 理解网页上的视觉元素、文本和结构
- 在对话中包含分析结果和可选的截图
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "save_path": {
                "type": "string",
                "description": "截图保存路径，可以是相对于工作区的路径或绝对路径。如果不指定，将自动生成文件名",
            },
            "full_page": {
                "type": "boolean",
                "description": "是否进行全页面截图（包括需要滚动才能看到的部分）。默认为true",
            },
            "goal": {
                "type": "string",
                "description": "分析截图的具体目标，如'描述网页内容'、'提取文本'、'识别界面元素'等",
            },
            "model_name": {
                "type": "string",
                "description": "要使用的多模态模型名称，默认使用配置中的模型",
            },
            "include_image_in_response": {
                "type": "boolean",
                "description": "是否在响应中包含截图。默认为true",
            },
        },
        "required": ["goal"],
    }

    screenshot_tool: BrowserScreenshot = Field(default_factory=BrowserScreenshot)
    understanding_tool: ImageUnderstanding = Field(default_factory=ImageUnderstanding)

    async def execute(
        self,
        goal: str,
        save_path: Optional[str] = None,
        full_page: bool = True,
        model_name: Optional[str] = None,
        include_image_in_response: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        对当前网页进行截图并分析内容。

        Args:
            goal: 分析截图的具体目标
            save_path: 截图保存路径，如果不指定则自动生成
            full_page: 是否截取完整页面
            model_name: 要使用的多模态模型名称
            include_image_in_response: 是否在响应中包含截图

        Returns:
            包含分析结果和可选的Base64编码截图的ToolResult
        """
        try:
            # 第一步：获取网页截图
            logger.info("正在获取网页截图...")
            screenshot_result = await self.screenshot_tool.execute(
                save_path=save_path,
                full_page=full_page
            )

            # 检查截图是否成功
            if screenshot_result.error:
                return ToolResult(error=f"截图失败: {screenshot_result.error}")

            # 提取保存路径信息
            saved_path = None
            content_parts = screenshot_result.content.split()
            for i, part in enumerate(content_parts):
                if part == "保存到" and i < len(content_parts) - 1:
                    saved_path = content_parts[i + 1]
                    break

            if not saved_path:
                return ToolResult(error="无法确定截图保存路径")

            # 第二步：分析截图内容
            logger.info(f"正在分析截图内容，目标: {goal}")
            understanding_result = await self.understanding_tool.execute(
                goal=goal,
                image_path=saved_path,
                model_name=model_name
            )

            # 检查分析是否成功
            if understanding_result.error:
                return ToolResult(error=f"图像分析失败: {understanding_result.error}")

            # 获取分析结果
            analysis = understanding_result.content

            # 构建响应
            response_content = f"网页截图已保存到 {saved_path}\n\n分析结果：\n{analysis}"

            # 返回结果
            if include_image_in_response:
                return ToolResult(
                    content=response_content,
                    base64_image=screenshot_result.base64_image
                )
            else:
                return ToolResult(content=response_content)

        except Exception as e:
            logger.error(f"网页视觉分析过程中出错: {str(e)}")
            return ToolResult(error=f"网页视觉分析失败: {str(e)}")

    @classmethod
    def create_with_context(cls, context: Context) -> "WebVision[Context]":
        """使用上下文创建工具实例，便于共享浏览器会话"""
        instance = cls()
        instance.screenshot_tool = BrowserScreenshot.create_with_context(context)
        return instance
