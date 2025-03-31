import asyncio
import base64
import json
from typing import Generic, Optional, TypeVar
import os
import time


from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from app.logger import logger
from app.config import config, WORKSPACE_ROOT


from app.config import config
from app.llm import LLM
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch
from app.tool.image_understanding import ImageUnderstanding


_BROWSER_DESCRIPTION = """
Interact with a web browser to perform various actions. This tool provides browser automation capabilities:

Navigation:
- 'go_to_url': Go to a specific URL in the current tab
- 'web_search': Search the query in the current tab, the query should be a search query like humans search in web, concrete and not vague or super long. More the single most important items.
"""

Context = TypeVar("Context")


class BrowserUseTool(BaseTool, Generic[Context]):
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "go_to_url",
                    "web_search",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'go_to_url' action",
            },
            "query": {
                "type": "string",
                "description": "Search query for 'web_search' action",
            },
        },
        "required": ["action"],
        "dependencies": {
            "go_to_url": ["url"],
            "web_search": ["query"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)
    web_search_tool: WebSearch = Field(default_factory=WebSearch, exclude=True)

    # Context for generic functionality
    tool_context: Optional[Context] = Field(default=None, exclude=True)

    llm: Optional[LLM] = Field(default_factory=LLM)


    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            browser_config_kwargs = {"headless": False, "disable_security": True}

            if config.browser_config:
                from browser_use.browser.browser import ProxySettings

                # handle proxy settings.
                if config.browser_config.proxy and config.browser_config.proxy.server:
                    browser_config_kwargs["proxy"] = ProxySettings(
                        server=config.browser_config.proxy.server,
                        username=config.browser_config.proxy.username,
                        password=config.browser_config.proxy.password,
                    )

                browser_attrs = [
                    "headless",
                    "disable_security",
                    "extra_chromium_args",
                    "chrome_instance_path",
                    "wss_url",
                    "cdp_url",
                ]

                for attr in browser_attrs:
                    value = getattr(config.browser_config, attr, None)
                    if value is not None:
                        if not isinstance(value, list) or value:
                            browser_config_kwargs[attr] = value

            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        if self.context is None:
            context_config = BrowserContextConfig()

            # if there is context config in the config, use it.
            if (
                config.browser_config
                and hasattr(config.browser_config, "new_context_config")
                and config.browser_config.new_context_config
            ):
                context_config = config.browser_config.new_context_config

            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context

    async def execute(
        self,
        *args,
        **kwargs
    ) -> ToolResult:
        """
        Execute a specified browser action.

        The method can be called in several ways:
        - With named parameters: execute(action="go_to_url", url="https://example.com")
        - With a JSON string parameter: execute(tool_input='{"action": "go_to_url", "url": "https://example.com"}')
        - With a dictionary: execute({'action': 'go_to_url', 'url': 'https://example.com'})

        Returns:
            ToolResult with the action's output or error
        """
        action = None
        url = None
        query = None

        # Case 1: Parameters passed directly as kwargs
        if 'action' in kwargs:
            action = kwargs.get('action')
            url = kwargs.get('url')
            query = kwargs.get('query')

        # Case 2: First arg is a dict with parameters
        elif args and isinstance(args[0], dict):
            params = args[0]
            action = params.get('action')
            url = params.get('url')
            query = params.get('query')

        # Case 3: tool_input is a string (JSON)
        elif 'tool_input' in kwargs and isinstance(kwargs['tool_input'], str):
            try:
                params = json.loads(kwargs['tool_input'])
                action = params.get('action')
                url = params.get('url')
                query = params.get('query')
            except json.JSONDecodeError:
                return ToolResult(error="Invalid JSON in tool_input for browser_use tool")

        # Case 4: Any parameter is a string that looks like JSON
        elif not action:
            for k, v in kwargs.items():
                if isinstance(v, str) and v.strip().startswith('{') and v.strip().endswith('}'):
                    try:
                        params = json.loads(v)
                        if isinstance(params, dict) and 'action' in params:
                            action = params.get('action')
                            url = params.get('url')
                            query = params.get('query')
                            break
                    except json.JSONDecodeError:
                        continue

        # Log the received parameters for debugging
        logger.info(f"Browser tool received: args={args}, kwargs={kwargs}, parsed: action={action}, url={url}, query={query}")

        if not action:
            return ToolResult(error="No action specified for browser_use tool. Make sure to provide the 'action' parameter.")

        async with self.lock:
            try:
                context = await self._ensure_browser_initialized()

                # 将BrowserScreenshot的导入和实例化移到这里
                from app.tool.browser_screenshot import BrowserScreenshot
                screenshot_tool = BrowserScreenshot()
                image_tool = ImageUnderstanding()

                # Navigation actions
                if action == "go_to_url":
                    if not url:
                        return ToolResult(
                            error="URL is required for 'go_to_url' action"
                        )
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
                        url=url
                    )

                    if screenshot_result.error:
                        logger.error(f"截图失败: {screenshot_result.error}")
                        return

                    # 直接使用screenshot_result中的screenshot_path
                    saved_path = screenshot_result.screenshot_path
                    if not saved_path:
                        # 如果BrowserScreenshot工具未返回path，使用预设路径
                        saved_path = os.path.join(WORKSPACE_ROOT, screenshot_path)
                        logger.info(f"未获取到screenshot_path，使用预设路径: {saved_path}")
                    else:
                        logger.info(f"从screenshot_result获取保存路径: {saved_path}")

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
                        return ToolResult(
                            error=f"图像分析失败: {understanding_result.error}",
                            screenshot_path=saved_path
                        )

                    analysis = understanding_result.output
                    logger.info("图像分析完成")

                    # 步骤4：将结果整合到代理对话中
                    logger.info(f"分析结果: {analysis}")
                    return ToolResult(
                        output=f"Navigated to {url}\n analysis: {analysis}",
                        screenshot_path=saved_path,
                        base64_image=screenshot_result.base64_image if hasattr(screenshot_result, 'base64_image') else None
                    )

                elif action == "web_search":
                    if not query:
                        return ToolResult(
                            error="Query is required for 'web_search' action"
                        )
                    search_results = await self.web_search_tool.execute(query)
                    logger.info(f"搜索结果: {search_results}")

                    if search_results:
                        return ToolResult(
                            output=f"Searched for '{query}'\nAll results:"
                            + "\n".join([str(r) for r in search_results])
                        )
                    else:
                        return ToolResult(
                            error=f"No search results found for '{query}'"
                        )

                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                logger.error(f"Browser action error: {str(e)}", exc_info=True)
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def get_current_state(
        self, context: Optional[BrowserContext] = None
    ) -> ToolResult:
        """
        Get the current browser state as a ToolResult.
        If context is not provided, uses self.context.
        """
        try:
            # Use provided context or fall back to self.context
            ctx = context or self.context
            if not ctx:
                return ToolResult(error="Browser context not initialized")

            state = await ctx.get_state()

            # Create a viewport_info dictionary if it doesn't exist
            viewport_height = 0
            if hasattr(state, "viewport_info") and state.viewport_info:
                viewport_height = state.viewport_info.height
            elif hasattr(ctx, "config") and hasattr(ctx.config, "browser_window_size"):
                viewport_height = ctx.config.browser_window_size.get("height", 0)

            # Take a screenshot for the state
            page = await ctx.get_current_page()

            await page.bring_to_front()
            await page.wait_for_load_state()

            screenshot = await page.screenshot(
                full_page=True, animations="disabled", type="jpeg", quality=100
            )

            screenshot = base64.b64encode(screenshot).decode("utf-8")

            # Build the state info with all required fields
            state_info = {
                "url": state.url,
                "title": state.title,
                "tabs": [tab.model_dump() for tab in state.tabs],
            }

            return ToolResult(
                output=json.dumps(state_info, indent=4, ensure_ascii=False),
                base64_image=screenshot,
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self):
        """
        Clean up browser resources asynchronously.
        Safe to call multiple times.
        """
        async with self.lock:
            # 关闭上下文
            if self.context is not None:
                try:
                    logger.info("Closing browser context")
                    await self.context.close()
                except Exception as e:
                    logger.error(f"Error closing browser context: {str(e)}", exc_info=True)
                finally:
                    self.context = None
                    self.dom_service = None

            # 关闭浏览器
            if self.browser is not None:
                try:
                    logger.info("Closing browser")
                    await self.browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {str(e)}", exc_info=True)
                finally:
                    self.browser = None

    def shutdown(self):
        """
        Synchronous method to shut down browser resources.
        This should be called explicitly when the application is shutting down.
        Safe to call multiple times.
        """
        # 如果没有需要清理的资源，直接返回
        if self.browser is None and self.context is None:
            return

        try:
            # 尝试获取当前运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果事件循环正在运行，创建任务
                if loop.is_running():
                    logger.info("Scheduling browser cleanup in running event loop")
                    # 创建任务但不等待其完成，这样不会阻塞调用者
                    loop.create_task(self.cleanup())
                    return
                else:
                    # 如果循环存在但未运行，使用它清理资源
                    logger.info("Using existing event loop for browser cleanup")
                    loop.run_until_complete(self.cleanup())
            except RuntimeError:
                # 没有事件循环存在，创建一个新的
                logger.info("Creating new event loop for browser cleanup")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.cleanup())
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)  # 移除事件循环引用，避免内存泄漏
        except Exception as e:
            logger.error(f"Error during browser shutdown: {str(e)}", exc_info=True)

    def __del__(self):
        """
        Object destructor - we attempt to schedule cleanup if browser or context still exists.
        Applications should call shutdown() explicitly instead of relying on garbage collection.
        """
        if self.browser is not None or self.context is not None:
            logger.warning(
                "BrowserUseTool is being garbage collected without explicit shutdown. "
                "Resources may leak. Call shutdown() or use an async context manager."
            )

            # Try to schedule cleanup if in a running event loop
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    # Schedule cleanup as a future task to avoid runtime errors
                    loop.create_task(self.cleanup())
                    logger.info("Scheduled browser cleanup in the current event loop")
            except RuntimeError:
                # No running event loop, try one last synchronous attempt
                try:
                    self.shutdown()
                except Exception as e:
                    logger.error(f"Failed to clean up browser resources during garbage collection: {str(e)}")

    @classmethod
    def create_with_context(cls, context: Context) -> "BrowserUseTool[Context]":
        """Factory method to create a BrowserUseTool with a specific context."""
        tool = cls()
        tool.tool_context = context
        return tool

    async def __aenter__(self) -> "BrowserUseTool":
        """
        Enable async context manager support.
        Example:
            async with BrowserUseTool() as browser_tool:
                await browser_tool.execute(action="go_to_url", url="https://example.com")
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting the async context manager."""
        await self.cleanup()
        return False  # Don't suppress exceptions
