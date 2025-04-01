from pydantic import Field

from app.config import config
from app.prompt.browser import NEXT_STEP_PROMPT as BROWSER_NEXT_STEP_PROMPT
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.agent.toolcall import ToolCallAgent



class Manus(ToolCallAgent):
    """
    一个多功能的通用代理，使用规划功能解决各种任务。

    这个代理扩展了BrowserAgent，具有全面的工具和功能，
    包括Python执行、网页浏览、文件操作和信息检索，
    能够处理各种用户请求。
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # 向工具集合中添加通用工具（不包括浏览器工具，它将在初始化时添加）
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            BrowserUseTool(), PythonExecute(), StrReplaceEditor(), FileSaver(),Terminate()
        )
    )

    async def initialize(self):
        """初始化代理，包括设置浏览器工具"""
        # 现在可以安全地使用super()调用，因为我们在ReActAgent中添加了initialize方法
        await super().initialize()
        # 现在浏览器工具已经设置好了，不需要再添加

    async def think(self) -> bool:
        """
        处理当前状态并决定采取适当的下一步行动。

        此方法通过根据浏览器工具是否正在使用来动态调整提示，从而增强标准思考过程。方法流程：

        1. 存储原始的next_step_prompt以便稍后恢复
        2. 检查最近的消息以检测浏览器工具是否处于活动状态
        3. 如果浏览器正在使用中，临时切换到浏览器专用提示，为浏览器相关操作提供更好的上下文
        4. 调用父类的think方法执行实际的思考过程
        5. 思考完成后恢复原始提示

        这种上下文感知能力使代理在浏览器交互发生时能够提供更相关的指令，提高其决策质量。

        返回：
            bool: 如果需要进一步行动则为True，否则为False
        """
        # 存储原始提示以便稍后恢复
        original_prompt = self.next_step_prompt

        # 仅检查最近的消息（最后3条）以确定浏览器是否正在使用
        # 这通过不扫描整个对话历史来优化性能
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []

        # # 检查任何最近的消息内容中是否包含browser_use
        # # 这表明浏览器工具当前处于活动状态
        # browser_in_use = any(
        #     "browser_use" in msg.content.lower()
        #     for msg in recent_messages
        #     if hasattr(msg, "content") and isinstance(msg.content, str)
        # )

        # if browser_in_use:
        #     # 如果正在使用浏览器，临时切换到浏览器专用提示
        #     # 这为浏览器操作提供了专门的上下文
        #     self.next_step_prompt = BROWSER_NEXT_STEP_PROMPT

        # 调用父类的think方法执行实际的思考过程
        # 这利用了BrowserAgent的think逻辑，同时使用我们的上下文感知提示
        result = await super().think()

        # 恢复原始提示以保持未来调用的一致性
        self.next_step_prompt = original_prompt

        # 返回父类think方法的结果（表明是否需要行动）
        return result
