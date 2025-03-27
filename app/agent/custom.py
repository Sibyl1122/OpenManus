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
    description: str = "自定义Agent"
    
    # 配置系统提示词
    system_prompt: str = SYSTEM_PROMPT

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