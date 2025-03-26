from pydantic import Field

from app.agent.simple import SimpleAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection, SystemInfoTool, OSAwareFileSaver, SystemInfoSaver
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute


class CustomAgent(SimpleAgent):
    """一个自定义的Agent，用于处理天气查询等任务"""
    
    name: str = "custom"
    description: str = "一个专门用于查询天气信息的Agent"
    
    # 配置系统提示词
    system_prompt: str = """你是一个专门用于查询天气信息的助手。
当用户请求天气信息时，你应该使用GoogleSearch工具来搜索相关信息。
请确保返回的信息准确、及时，并包含温度、天气状况等关键信息。"""
    
    # 配置可用工具
    available_tools: ToolCollection = ToolCollection(
        GoogleSearch(),
        BrowserUseTool(),
        SystemInfoTool()
    )

    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 1

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(), GoogleSearch(), BrowserUseTool(), 
            SystemInfoTool(), OSAwareFileSaver()
        )
    )