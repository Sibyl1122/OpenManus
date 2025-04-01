import json
from typing import Any, Optional

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.browser import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message, ToolChoice
from app.tool import BrowserUseTool, Terminate, ToolCollection


class BrowserAgent(ToolCallAgent):
    """
    A browser agent that uses the browser_use library to control a browser.

    This agent can navigate web pages, interact with elements, fill forms,
    extract content, and perform other browser-based actions to accomplish tasks.
    """

    name: str = "browser"
    description: str = "A browser agent that can control a browser to accomplish tasks"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # 可用工具配置（不直接创建BrowserUseTool实例）
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    # 使用Auto工具选择，允许同时使用工具和自由格式的响应
    tool_choices: ToolChoice = ToolChoice.AUTO
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    _current_base64_image: Optional[str] = None
    _browser_tool: Optional[BrowserUseTool] = None
    _browser_context_manager: Optional[BrowserUseTool] = None

    async def initialize(self):
        """初始化代理，设置浏览器工具"""
        # 使用异步上下文管理器创建浏览器工具
        if self._browser_context_manager is None:
            try:
                # 记录初始化浏览器工具的操作
                logger.info(f"{self.name} agent initializing browser tool...")
                self._browser_context_manager = BrowserUseTool()
                self._browser_tool = await self._browser_context_manager.__aenter__()
                # 将浏览器工具添加到可用工具集合
                self.available_tools.add_tool(self._browser_tool)
                logger.info(f"{self.name} browser tool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize browser tool: {str(e)}")
                raise

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """处理特殊工具的执行结果，特别是终止操作"""
        if not self._is_special_tool(name):
            return
        else:
            # 调用父类方法处理特殊工具
            await super()._handle_special_tool(name, result, **kwargs)

    async def get_browser_state(self) -> Optional[dict]:
        """Get the current browser state for context in next steps."""
        # 确保浏览器工具已初始化
        if self._browser_tool is None:
            await self.initialize()

        try:
            # 从工具获取浏览器状态
            result = await self._browser_tool.get_current_state()

            if result.error:
                logger.debug(f"Browser state error: {result.error}")
                return None

            # 如果有截图则保存
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image

            # 解析状态信息
            return json.loads(result.output)

        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def cleanup(self):
        """清理代理资源，包括浏览器资源"""
        try:
            # 清理浏览器上下文管理器
            if self._browser_context_manager is not None:
                logger.info(f"{self.name} cleaning up browser resources")
                await self._browser_context_manager.__aexit__(None, None, None)
                self._browser_context_manager = None
                self._browser_tool = None
                logger.info(f"{self.name} browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up browser resources: {str(e)}")

        # 调用父类清理方法
        await super().cleanup()

    async def think(self) -> bool:
        """Process current state and decide next actions using tools, with browser state info added"""
        # 确保浏览器工具已初始化
        if self._browser_tool is None:
            await self.initialize()

        # Add browser state to the context
        browser_state = await self.get_browser_state()

        # Initialize placeholder values
        url_info = ""
        tabs_info = ""
        content_above_info = ""
        content_below_info = ""
        results_info = ""

        if browser_state and not browser_state.get("error"):
            # URL and title info
            url_info = f"\n   URL: {browser_state.get('url', 'N/A')}\n   Title: {browser_state.get('title', 'N/A')}"

            # Tab information
            if "tabs" in browser_state:
                tabs = browser_state.get("tabs", [])
                if tabs:
                    tabs_info = f"\n   {len(tabs)} tab(s) available"

            # Content above/below viewport
            pixels_above = browser_state.get("pixels_above", 0)
            pixels_below = browser_state.get("pixels_below", 0)

            if pixels_above > 0:
                content_above_info = f" ({pixels_above} pixels)"

            if pixels_below > 0:
                content_below_info = f" ({pixels_below} pixels)"


        # Replace placeholders with actual browser state info
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            url_placeholder=url_info,
            tabs_placeholder=tabs_info,
            content_above_placeholder=content_above_info,
            content_below_placeholder=content_below_info,
            results_placeholder=results_info,
        )

        # Call parent implementation
        result = await super().think()
        # Reset the next_step_prompt to its original state
        self.next_step_prompt = NEXT_STEP_PROMPT

        return result
